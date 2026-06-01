# services/strategist_service.py
# AI service for generating human-friendly growth strategy insights from extracted metrics.

import google.generativeai as genai
import os
from dotenv import load_dotenv

from services.prompts import get_audit_report_prompt

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


class StrategistService:
    """
    Service for generating high-quality growth audits and recommendations
    based on the extracted creator metrics, written from a content strategist POV.
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model = genai.GenerativeModel(model_name)

    def generate_growth_audit(self, metrics_json: dict, creator_name: str | None = None) -> str:
        """
        Generates a growth audit using the strategizing prompt.
        
        Args:
            metrics_json: The extracted metrics JSON dict.
            creator_name: Optional creator username for context.
            
        Returns:
            str: Plain text strategist report.
        """
        prompt = get_audit_report_prompt(metrics_json, creator_name)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,  # slightly higher temperature for creative strategy and pillars
                )
            )
            return response.text
        except Exception as e:
            raise RuntimeError(f"Failed to generate growth audit via Gemini: {str(e)}")
