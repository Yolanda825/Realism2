"""Stage 4: Strategy Generator - Generates enhancement strategies based on analysis."""

import json
from app.models.schemas import (
    SceneClassification,
    FakeSignal,
    RealismConstraints,
    Strategy,
    Operation,
    ModuleType,
    Strength,
    Locality,
    Priority,
)
from app.services.llm_client import get_llm_client

SYSTEM_PROMPT = """You are a realism enhancement director. Your job is to create strategies for improving the perceived realism of images.

CRITICAL RULES:
1. PRESERVE identity, composition, and intent of the original image.
2. REDUCE "AI-like perfection" by introducing real-world imperfections.
3. AVOID cinematic, stylized, or aesthetic exaggeration.
4. PREFER subtle, local, and physically plausible changes.
5. NEVER mention specific model names or generate prompts.
6. Think like a "realism director", not an artist.
7. Focus on WHAT should change, HOW STRONGLY, and WHAT MUST NOT CHANGE.

You must return ONLY valid JSON, no other text."""

STRATEGY_PROMPT = """Based on the following analysis, create a realism enhancement strategy.

SCENE CLASSIFICATION:
{scene_classification}

DETECTED FAKE SIGNALS:
{fake_signals}

REALISM CONSTRAINTS:
Scene Rules: {scene_rules}
Avoid Patterns: {avoid_patterns}

---

Create a strategy with the following structure:

1. GOAL: A brief statement of the overall enhancement goal

2. PRIORITY: Rate overall priority based on severity of issues
   - "very_low": Image is already quite realistic
   - "low": Minor enhancements needed
   - "medium": Moderate enhancements needed

3. OPERATIONS: List of specific enhancement operations
   Each operation must specify:
   - module: "lighting", "texture", or "noise"
   - action: What to do (be specific but don't mention model names)
   - strength: "very_low", "low", or "medium"
   - locality: "global" or "local"

4. CONSTRAINTS: Things that MUST NOT change
   - Preserve identity and composition
   - Maintain overall color scheme
   - Keep the image's intent intact

Example operations:
- Lighting: "Add subtle shadow falloff variation", "Introduce minor highlight inconsistency"
- Texture: "Add micro-texture to smooth surfaces", "Introduce slight skin pore detail"
- Noise: "Add subtle sensor noise pattern", "Introduce film grain in shadows"

Return your strategy as JSON in this exact format:
{{
  "goal": "<overall enhancement goal>",
  "priority": "very_low" | "low" | "medium",
  "operations": [
    {{
      "module": "lighting" | "texture" | "noise",
      "action": "<specific action description>",
      "strength": "very_low" | "low" | "medium",
      "locality": "global" | "local"
    }}
  ],
  "constraints": ["<constraint1>", "<constraint2>", ...]
}}

Return ONLY the JSON object, no explanations or markdown."""


class StrategyGenerator:
    """Generates enhancement strategies based on analysis results."""

    def __init__(self):
        """Initialize the strategy generator."""
        self.llm_client = get_llm_client()

    async def generate(
        self,
        scene_classification: SceneClassification,
        fake_signals: list[FakeSignal],
        realism_constraints: RealismConstraints,
    ) -> Strategy:
        """
        Generate an enhancement strategy based on analysis.

        Args:
            scene_classification: Scene classification results
            fake_signals: Detected fake signals
            realism_constraints: Retrieved realism constraints

        Returns:
            Strategy with goal, priority, operations, and constraints
        """
        # Format the prompt with analysis data
        prompt = STRATEGY_PROMPT.format(
            scene_classification=json.dumps(scene_classification.model_dump(), indent=2),
            fake_signals=json.dumps([s.model_dump() for s in fake_signals], indent=2),
            scene_rules=json.dumps(realism_constraints.scene_rules, indent=2),
            avoid_patterns=json.dumps(realism_constraints.avoid_patterns, indent=2),
        )

        # Get LLM response
        response = await self.llm_client.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=2048,
        )

        # Parse the JSON response
        result = await self.llm_client.parse_json_response(response)

        # Parse priority
        priority_str = result.get("priority", "low").lower()
        try:
            priority = Priority(priority_str)
        except ValueError:
            priority = Priority.LOW

        # Parse operations
        operations = []
        for op in result.get("operations", []):
            try:
                module = ModuleType(op.get("module", "noise").lower())
                strength = Strength(op.get("strength", "low").lower())
                locality = Locality(op.get("locality", "global").lower())

                operations.append(Operation(
                    module=module,
                    action=op.get("action", ""),
                    strength=strength,
                    locality=locality,
                ))
            except (ValueError, KeyError):
                continue

        return Strategy(
            goal=result.get("goal", "Enhance perceived realism"),
            priority=priority,
            operations=operations,
            constraints=result.get("constraints", []),
        )
