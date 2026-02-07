"""Stage 1: Scene Classifier - Analyzes images to classify scene type and AI likelihood."""

import json
from app.models.schemas import SceneClassification
from app.services.llm_client import get_llm_client

SYSTEM_PROMPT = """You are an expert image analyst specializing in scene classification and AI-generated image detection.

IMPORTANT RULES:
1. Never describe or infer the identity of any person in the image.
2. Focus only on scene type, technical attributes, and AI-generation likelihood.
3. Do not mention names or identify specific individuals.
4. Be objective and technical in your analysis.

You must return ONLY valid JSON, no other text."""

CLASSIFICATION_PROMPT = """Analyze this image and provide a scene classification.

Classify the following:

1. PRIMARY SCENE TYPE - Choose the most appropriate:
   - portrait: Images primarily featuring a person or people
   - landscape: Natural outdoor scenes (mountains, beaches, forests, etc.)
   - interior: Indoor spaces (rooms, offices, restaurants, etc.)
   - product: Commercial product photography
   - street: Urban/street photography
   - architecture: Buildings and architectural subjects
   - food: Food photography
   - abstract: Abstract or artistic compositions
   - other: If none of the above fit

2. SECONDARY ATTRIBUTES - List relevant attributes such as:
   - Lighting conditions (natural, artificial, studio, golden hour, etc.)
   - Composition style (centered, rule of thirds, symmetrical, etc.)
   - Color palette (warm, cool, muted, vibrant, etc.)
   - Depth of field (shallow, deep)
   - Any other relevant technical characteristics

3. AI-GENERATION LIKELIHOOD (0.0 to 1.0) - Estimate the probability this is AI-generated based on:
   - Texture consistency and micro-details
   - Edge sharpness patterns
   - Lighting physics accuracy
   - Presence of common AI artifacts
   - Overall "synthetic" feel

Return your analysis as JSON in this exact format:
{
  "primary_scene": "<scene_type>",
  "secondary_attributes": ["<attribute1>", "<attribute2>", ...],
  "ai_likelihood": <float between 0.0 and 1.0>
}

Return ONLY the JSON object, no explanations or markdown."""


class SceneClassifier:
    """Classifies images by scene type and estimates AI-generation likelihood."""

    def __init__(self):
        """Initialize the scene classifier."""
        self.llm_client = get_llm_client()

    async def classify(self, image_base64: str) -> SceneClassification:
        """
        Classify the scene type and attributes of an image.

        Args:
            image_base64: Base64-encoded image data

        Returns:
            SceneClassification with scene type, attributes, and AI likelihood
        """
        response = await self.llm_client.chat_completion_with_image(
            prompt=CLASSIFICATION_PROMPT,
            image_base64=image_base64,
            system_prompt=SYSTEM_PROMPT,
            temperature=0,
            max_tokens=1024,
        )

        # Parse the JSON response
        result = await self.llm_client.parse_json_response(response)

        return SceneClassification(
            primary_scene=result.get("primary_scene", "other"),
            secondary_attributes=result.get("secondary_attributes", []),
            ai_likelihood=float(result.get("ai_likelihood", 0.5)),
        )
