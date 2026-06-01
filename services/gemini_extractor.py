# services/gemini_extractor.py
# Multimodal Gemini service for extracting analytics from screenshots.
#
# Handles large uploads (30-50+ images) by batching into groups of
# BATCH_SIZE, extracting from each batch, then merging results.
#
# Incorporates 100% resilient fallback logic: if a batch fails (e.g. 400 bad image),
# the extractor automatically retries the images in that batch individually
# to maximize data recovery while skipping only the corrupted file.

import google.generativeai as genai
import json
import os
import re
from dotenv import load_dotenv

from services.prompts import get_extraction_prompt

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

BATCH_SIZE = 5  # Max images per Gemini request to stay within payload limits

# Magic bytes → MIME type lookup
_MAGIC_SIGNATURES = [
    (b'\x89PNG\r\n\x1a\n',     "image/png"),
    (b'\xff\xd8\xff',           "image/jpeg"),
    (b'RIFF',                   "image/webp"),
    (b'GIF87a',                 "image/gif"),
    (b'GIF89a',                 "image/gif"),
]


def _detect_mime(data: bytes, filename: str = "") -> str | None:
    """Detect MIME type from file magic bytes, falling back to filename extension."""
    for sig, mime in _MAGIC_SIGNATURES:
        if data[:len(sig)] == sig:
            if sig == b'RIFF' and data[8:12] != b'WEBP':
                continue
            return mime
    ext = os.path.splitext(filename)[1].lower()
    ext_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    return ext_map.get(ext)


def _merge_results(base: dict, new: dict) -> dict:
    """
    Merge two extraction result dicts. For each field:
    - If base has null and new has a value → take new's value
    - If both have values → keep base (first seen wins)
    - Lists get extended (e.g. top_hashtags)
    - additional_metrics dicts get merged
    """
    for key, new_val in new.items():
        if key.startswith("_"):
            continue  # skip metadata keys

        base_val = base.get(key)

        # Both are dicts → recurse
        if isinstance(base_val, dict) and isinstance(new_val, dict):
            base[key] = _merge_results(base_val, new_val)
        # Base is None/missing → take new
        elif base_val is None:
            base[key] = new_val
        # Both are lists → extend without duplicates
        elif isinstance(base_val, list) and isinstance(new_val, list):
            for item in new_val:
                if item not in base_val:
                    base_val.append(item)
        # Otherwise keep base (first-seen wins)

    return base


class GeminiExtractor:
    """
    Extracts analytics data from screenshots using Gemini's multimodal API.
    Automatically batches large uploads (30-50+ images) into smaller groups.
    If a batch fails, retries images individually for absolute fault tolerance.
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model = genai.GenerativeModel(model_name)

    def _strip_markdown_fences(self, text: str) -> str:
        text = text.strip()
        pattern = r'^```(?:json)?\s*\n?(.*?)\n?\s*```$'
        match = re.match(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text

    def _parse_response(self, raw_text: str) -> dict:
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            pass
        cleaned = self._strip_markdown_fences(raw_text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        return {
            "error": "Failed to parse JSON from Gemini response",
            "raw_response": raw_text
        }

    def _extract_batch(self, image_parts: list[dict], prompt: str) -> dict:
        """Send a single batch of image parts to Gemini and return parsed result."""
        content_parts = [prompt] + image_parts
        response = self.model.generate_content(
            content_parts,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        return self._parse_response(response.text)

    def _extract_individual_fallback(self, batch: list[dict], prompt: str, batch_num: int, errors_list: list) -> dict | None:
        """Retries all items in a failed batch individually to extract successful images."""
        batch_result = None
        for idx, img_part in enumerate(batch, 1):
            try:
                single_result = self._extract_batch([img_part], prompt)
                if "error" not in single_result:
                    if batch_result is None:
                        batch_result = single_result
                    else:
                        batch_result = _merge_results(batch_result, single_result)
                else:
                    errors_list.append(f"Batch {batch_num} - Image {idx} extraction failed: {single_result['error']}")
            except Exception as e:
                errors_list.append(f"Batch {batch_num} - Image {idx} call failed: {str(e)}")
        return batch_result

    def extract(
        self,
        images: list[bytes],
        creator_name: str | None = None,
        filenames: list[str] | None = None,
        progress_callback=None,
    ) -> dict:
        """
        Extract analytics data from screenshot images using Gemini.

        Args:
            images: List of image file bytes.
            creator_name: Optional creator username for context.
            filenames: Optional filenames for MIME fallback detection.
            progress_callback: Optional callable(batch_num, total_batches, status)
                               for UI progress updates.

        Returns:
            dict with extracted metrics, or {"error": ..., "raw_response": ...} on failure.
        """
        if not images:
            return {"error": "No images provided", "raw_response": ""}

        prompt = get_extraction_prompt(creator_name)
        filenames = filenames or [""] * len(images)

        # Build inline_data parts — skip unrecognized formats
        image_parts = []
        skipped = []
        for idx, (img_bytes, fname) in enumerate(zip(images, filenames)):
            mime = _detect_mime(img_bytes, fname)
            if not mime:
                skipped.append(fname or f"image_{idx}")
                continue
            image_parts.append({
                "inline_data": {
                    "mime_type": mime,
                    "data": img_bytes,
                }
            })

        if not image_parts:
            return {
                "error": f"No valid images found. Skipped: {', '.join(skipped)}",
                "raw_response": "",
            }

        # Split into batches
        batches = [image_parts[i:i + BATCH_SIZE] for i in range(0, len(image_parts), BATCH_SIZE)]
        total_batches = len(batches)

        merged_result = None
        batch_errors = []
        recovered_batches = 0

        for batch_num, batch in enumerate(batches, 1):
            if progress_callback:
                progress_callback(batch_num, total_batches, "extracting")

            try:
                result = self._extract_batch(batch, prompt)

                if "error" in result:
                    # Fallback recovery
                    batch_errors.append(f"Batch {batch_num}: {result['error']}. Retrying items individually...")
                    recovered = self._extract_individual_fallback(batch, prompt, batch_num, batch_errors)
                    if recovered:
                        recovered_batches += 1
                        if merged_result is None:
                            merged_result = recovered
                        else:
                            merged_result = _merge_results(merged_result, recovered)
                    continue

                if merged_result is None:
                    merged_result = result
                else:
                    merged_result = _merge_results(merged_result, result)

            except Exception as e:
                batch_errors.append(f"Batch {batch_num}/{total_batches} failed: {str(e)}. Retrying items individually...")
                recovered = self._extract_individual_fallback(batch, prompt, batch_num, batch_errors)
                if recovered:
                    recovered_batches += 1
                    if merged_result is None:
                        merged_result = recovered
                    else:
                        merged_result = _merge_results(merged_result, recovered)
                continue

        # If we got no successful results at all
        if merged_result is None:
            return {
                "error": f"All {total_batches} batch(es) failed: {'; '.join(batch_errors)}",
                "raw_response": "",
            }

        # Attach metadata
        if skipped:
            merged_result["_skipped_images"] = skipped
        if batch_errors:
            merged_result["_batch_errors"] = batch_errors
            
        # Count recovered batches as processed
        merged_result["_batches_processed"] = total_batches - len(batch_errors) + recovered_batches
        merged_result["_batches_total"] = total_batches

        return merged_result
