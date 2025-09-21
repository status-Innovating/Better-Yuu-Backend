# # app/domains/ai_engine/services.py
"""
Modern AI integration using the high-level Vertex AI SDK.
- Analyzes dream text using a Vertex AI generative model (e.g., Gemini).
- Returns a structured dict matching the DreamAnalysis schema.
"""

import os
import json
import logging
from typing import Dict, Any
from datetime import datetime, timezone

import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    if settings.GOOGLE_PROJECT and settings.GOOGLE_REGION:
        vertexai.init(project=settings.GOOGLE_PROJECT, location=settings.GOOGLE_REGION)
        logger.info(f"Vertex AI SDK initialized for project '{settings.GOOGLE_PROJECT}' in region '{settings.GOOGLE_REGION}'")
    else:
        logger.warning("Vertex AI SDK not initialized because GOOGLE_PROJECT or GOOGLE_REGION is missing.")
except Exception as e:
    logger.error(f"Failed to initialize Vertex AI SDK: {e}", exc_info=True)

# --- Core AI Service ---

async def analyze_text_with_vertex(text: str) -> Dict[str, Any]:
    """
    Calls a Vertex AI generative model using the modern SDK.
    """
    # UPDATED: Check for settings at the time of the function call
    if not all([settings.GOOGLE_PROJECT, settings.GOOGLE_REGION, settings.VERTEX_AI_MODEL]):
        raise ValueError("Google Cloud settings (PROJECT, REGION, MODEL) are not configured in your .env file.")

    if not text or not text.strip():
        logger.warning("analyze_text_with_vertex called with empty text.")
        return {"status": "complete", "summary": "No text provided.", "raw_response": ""}

    prompt = f"""
You are an empathetic mental health analysis assistant. Analyze the user's dream text below.
Produce a JSON object only (no other text, no markdown fences) that follows this exact schema:

{{
  "summary": "string",
  "emotions": {{ "<emotion>": number (0 to 1) }},
  "sentiment_score": number (-1.0 to 1.0),
  "themes": ["string"],
  "symbols": [{{ "symbol": "string", "confidence": number, "explanation": "string" }}],
  "risk_flags": {{
     "self_harm": "none|low|medium|high",
     "suicide": "none|low|medium|high",
     "violence": boolean,
     "abuse_mention": boolean
  }}
}}

Dream text:
---
{text}
---

Return only the valid JSON object.
"""

    try:
        # Load the generative model using the model name from settings
        model = GenerativeModel(settings.VERTEX_AI_MODEL)

        generation_config = GenerationConfig(temperature=0.1, max_output_tokens=2048)

        response = await model.generate_content_async([prompt], generation_config=generation_config)

        model_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(model_text)

        parsed_json["status"] = "complete"
        parsed_json["model"] = settings.VERTEX_AI_MODEL
        parsed_json["generated_at"] = datetime.now(timezone.utc).isoformat()
        parsed_json["raw_response"] = model_text
        return parsed_json

    except Exception as e:
        logger.error(f"Error during Vertex AI call: {e}", exc_info=True)
        raise