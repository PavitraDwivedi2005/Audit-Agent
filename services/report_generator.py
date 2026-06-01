# services/report_generator.py
# OpenRouter strategic reasoning layer integration.
# Handles isolated generation across 4 free LLMs with strict timeout and error bounds.

import os
import time
import json
from openai import OpenAI
from dotenv import load_dotenv

from services.prompts import get_benchmark_report_prompt

load_dotenv()

# Define the exact free model identifiers on OpenRouter
BENCHMARK_MODELS = {
    "Qwen 3 Next 80B": "qwen/qwen3-next-80b-a3b-instruct:free",
    "GPT-OSS 120B": "openai/gpt-oss-120b:free",
    "Llama 3.3 70B": "meta-llama/llama-3.3-70b-instruct:free",
    "Hermes 3 Llama 3.1 405B": "nousresearch/hermes-3-llama-3.1-405b:free",
}

class ReportGeneratorService:
    """
    Service that orchestrates prompt formatting and executes text audit generation
    across multiple free OpenRouter models with strict error boundaries.
    """

    def __init__(self):
        # API key is securely loaded from environment variables
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not defined in environment or .env file.")
        
        # Configure OpenAI client to point to OpenRouter endpoint
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )

    def generate_report(self, model_key: str, metrics_json: dict, creator_name: str | None = None) -> dict:
        """
        Executes audit generation for a single specified model.
        Returns a dict containing generation results and telemetry.
        """
        model_id = BENCHMARK_MODELS.get(model_key)
        if not model_id:
            return {
                "report_text": None,
                "raw_response": f"Unknown model key: {model_key}",
                "latency": 0.0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "error": f"Model key '{model_key}' is not mapped to any OpenRouter model id."
            }

        prompt = get_benchmark_report_prompt(metrics_json, creator_name)
        
        # Setup telemetry variables
        start_time = time.time()
        latency = 0.0
        
        try:
            # Enforce 45-second timeout on the HTTP request to prevent hangs
            response = self.client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=2500,        # safe ceiling to avoid "doctoral thesis on hashtags"
                temperature=0.7,        # optimal strategic reasoning variance
                extra_headers={
                    "HTTP-Referer": "https://arohanum.com",
                    "X-Title": "Arohanum Elevate Benchmark Agent",
                },
                timeout=45.0,
            )
            
            latency = time.time() - start_time
            
            # Extract content and token metadata
            report_text = response.choices[0].message.content
            raw_model_response = response.model_dump_json()
            
            prompt_tokens = 0
            completion_tokens = 0
            if response.usage:
                prompt_tokens = getattr(response.usage, "prompt_tokens", 0)
                completion_tokens = getattr(response.usage, "completion_tokens", 0)
                
            return {
                "report_text": report_text,
                "raw_response": raw_model_response,
                "latency": round(latency, 2),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "error": None
            }
            
        except Exception as e:
            latency = time.time() - start_time
            return {
                "report_text": None,
                "raw_response": f"Exception raised during OpenRouter generation:\n{str(e)}",
                "latency": round(latency, 2),
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "error": f"Failed to generate using {model_key}: {str(e)}"
            }
