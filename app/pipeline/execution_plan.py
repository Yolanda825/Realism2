"""Stage 5: Execution Planner - Translates strategy into module instructions."""

from app.models.schemas import (
    Strategy,
    ExecutionPlan,
    ModuleInstruction,
    ModuleType,
    Strength,
    Locality,
)


# Strength to parameter mapping
STRENGTH_PARAMS = {
    Strength.VERY_LOW: {"intensity": 0.1, "probability": 0.3},
    Strength.LOW: {"intensity": 0.25, "probability": 0.5},
    Strength.MEDIUM: {"intensity": 0.4, "probability": 0.7},
}


class ExecutionPlanner:
    """Translates enhancement strategies into execution-ready instructions."""

    def __init__(self):
        """Initialize the execution planner."""
        pass

    async def create_plan(self, strategy: Strategy) -> ExecutionPlan:
        """
        Create an execution plan from a strategy.

        Args:
            strategy: The enhancement strategy

        Returns:
            ExecutionPlan with module-specific instructions
        """
        lighting_instructions = []
        texture_instructions = []
        noise_instructions = []

        for operation in strategy.operations:
            instruction = self._create_instruction(operation)

            if operation.module == ModuleType.LIGHTING:
                lighting_instructions.append(instruction)
            elif operation.module == ModuleType.TEXTURE:
                texture_instructions.append(instruction)
            elif operation.module == ModuleType.NOISE:
                noise_instructions.append(instruction)

        return ExecutionPlan(
            lighting_module=lighting_instructions,
            texture_module=texture_instructions,
            noise_module=noise_instructions,
        )

    def _create_instruction(self, operation) -> ModuleInstruction:
        """
        Create a module instruction from an operation.

        Args:
            operation: The operation from the strategy

        Returns:
            ModuleInstruction with action and parameters
        """
        # Get base parameters from strength
        params = STRENGTH_PARAMS.get(operation.strength, STRENGTH_PARAMS[Strength.LOW]).copy()

        # Add module-specific parameters
        if operation.module == ModuleType.LIGHTING:
            params.update(self._get_lighting_params(operation))
        elif operation.module == ModuleType.TEXTURE:
            params.update(self._get_texture_params(operation))
        elif operation.module == ModuleType.NOISE:
            params.update(self._get_noise_params(operation))

        # Determine target region
        target_region = None if operation.locality == Locality.GLOBAL else "auto_detect"

        return ModuleInstruction(
            action=operation.action,
            parameters=params,
            target_region=target_region,
        )

    def _get_lighting_params(self, operation) -> dict:
        """Get lighting-specific parameters."""
        action_lower = operation.action.lower()

        params = {
            "type": "lighting_adjustment",
        }

        if "shadow" in action_lower:
            params["shadow_variation"] = True
            params["shadow_softness"] = 0.2 if operation.strength == Strength.VERY_LOW else 0.4
        if "highlight" in action_lower:
            params["highlight_variation"] = True
            params["highlight_bloom"] = 0.1 if operation.strength == Strength.VERY_LOW else 0.2
        if "falloff" in action_lower:
            params["falloff_randomization"] = True
        if "inconsisten" in action_lower:
            params["consistency_break"] = True

        return params

    def _get_texture_params(self, operation) -> dict:
        """Get texture-specific parameters."""
        action_lower = operation.action.lower()

        params = {
            "type": "texture_enhancement",
        }

        if "micro" in action_lower or "pore" in action_lower:
            params["add_micro_detail"] = True
            params["detail_scale"] = "fine"
        if "variation" in action_lower:
            params["add_variation"] = True
        if "imperfection" in action_lower:
            params["add_imperfections"] = True
            params["imperfection_type"] = "natural"
        if "skin" in action_lower:
            params["target_material"] = "skin"
        if "surface" in action_lower:
            params["target_material"] = "surface"

        return params

    def _get_noise_params(self, operation) -> dict:
        """Get noise-specific parameters."""
        action_lower = operation.action.lower()

        params = {
            "type": "noise_injection",
        }

        if "sensor" in action_lower:
            params["noise_type"] = "sensor"
            params["pattern"] = "gaussian"
        if "film" in action_lower or "grain" in action_lower:
            params["noise_type"] = "film_grain"
            params["pattern"] = "organic"
        if "shadow" in action_lower:
            params["target_tones"] = "shadows"
        if "highlight" in action_lower:
            params["target_tones"] = "highlights"
        if "chroma" in action_lower or "color" in action_lower:
            params["include_chroma"] = True

        # Default noise type if not specified
        if "noise_type" not in params:
            params["noise_type"] = "subtle"
            params["pattern"] = "natural"

        return params
