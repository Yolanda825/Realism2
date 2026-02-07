"""Prompt Generator - Creates img2img prompts based on analysis results."""

from app.models.schemas import (
    SceneClassification,
    FakeSignal,
    Strategy,
    ExecutionPlan,
    ModelRouting,
    Severity,
    Priority,
)


# Scene-specific prompt templates
SCENE_PROMPTS = {
    "portrait": {
        "base": "realistic photograph of a person, natural skin texture with visible pores, subtle skin imperfections, natural hair strands, realistic eye reflections, professional photography",
        "negative": "smooth plastic skin, airbrushed, oversaturated, HDR, cartoon, anime, illustration, painting, artificial, perfect symmetry, uncanny valley",
    },
    "landscape": {
        "base": "realistic landscape photograph, natural lighting, atmospheric perspective, subtle color variations, film grain, professional nature photography",
        "negative": "oversaturated, HDR, cartoon, painting, artificial colors, perfect symmetry, digital art, illustration",
    },
    "interior": {
        "base": "realistic interior photograph, natural ambient lighting, subtle shadows, realistic material textures, professional architectural photography",
        "negative": "perfect lighting, CGI, 3D render, artificial, cartoon, illustration, oversaturated",
    },
    "product": {
        "base": "realistic product photograph, natural studio lighting, subtle reflections, realistic material properties, professional commercial photography",
        "negative": "CGI, 3D render, floating object, artificial lighting, cartoon, illustration",
    },
    "street": {
        "base": "realistic street photograph, natural urban lighting, weathered surfaces, atmospheric elements, documentary photography style",
        "negative": "perfect clean surfaces, artificial, CGI, illustration, cartoon, oversaturated",
    },
    "default": {
        "base": "realistic photograph, natural lighting, subtle imperfections, film grain, professional photography",
        "negative": "artificial, CGI, cartoon, illustration, oversaturated, HDR, perfect symmetry",
    },
}


class PromptGenerator:
    """Generates img2img prompts based on analysis results."""

    def __init__(self):
        """Initialize the prompt generator."""
        pass

    def generate_routing(
        self,
        scene_classification: SceneClassification,
        fake_signals: list[FakeSignal],
        strategy: Strategy,
        execution_plan: ExecutionPlan,
    ) -> ModelRouting:
        """
        Generate model routing information including prompt.

        Args:
            scene_classification: Scene classification results
            fake_signals: Detected fake signals
            strategy: Enhancement strategy
            execution_plan: Execution plan

        Returns:
            ModelRouting with model selection and prompt
        """
        # Get scene-specific templates
        scene_key = scene_classification.primary_scene.lower()
        templates = SCENE_PROMPTS.get(scene_key, SCENE_PROMPTS["default"])

        # Build enhancement prompt based on strategy
        prompt_parts = [templates["base"]]
        negative_parts = [templates["negative"]]

        # Add specific enhancements based on detected issues
        enhancement_keywords = self._get_enhancement_keywords(fake_signals, strategy)
        if enhancement_keywords:
            prompt_parts.append(enhancement_keywords)

        # Add anti-AI keywords based on fake signals
        anti_ai_keywords = self._get_anti_ai_keywords(fake_signals)
        if anti_ai_keywords:
            negative_parts.append(anti_ai_keywords)

        # Combine prompts
        prompt = ", ".join(prompt_parts)
        negative_prompt = ", ".join(negative_parts)

        # Determine model parameters based on priority
        params = self._get_model_parameters(strategy, scene_classification)

        # Generate reasoning
        reasoning = self._generate_reasoning(
            scene_classification, fake_signals, strategy
        )

        return ModelRouting(
            model_name="img2img-realism",
            model_type="img2img",
            prompt=prompt,
            negative_prompt=negative_prompt,
            parameters=params,
            reasoning=reasoning,
        )

    def _get_enhancement_keywords(
        self,
        fake_signals: list[FakeSignal],
        strategy: Strategy,
    ) -> str:
        """Get enhancement keywords based on detected issues."""
        keywords = []

        for signal in fake_signals:
            signal_lower = signal.signal.lower()

            if "smooth" in signal_lower or "texture" in signal_lower:
                keywords.append("detailed texture")
            if "symmetr" in signal_lower:
                keywords.append("natural asymmetry")
            if "lighting" in signal_lower or "shadow" in signal_lower:
                keywords.append("natural lighting falloff")
            if "edge" in signal_lower:
                keywords.append("natural edge transitions")
            if "noise" in signal_lower or "grain" in signal_lower:
                keywords.append("subtle film grain")

        # Add from strategy operations
        for op in strategy.operations:
            if op.module.value == "texture":
                keywords.append("micro detail")
            if op.module.value == "noise":
                keywords.append("sensor noise")
            if op.module.value == "lighting":
                keywords.append("realistic shadows")

        return ", ".join(list(set(keywords))) if keywords else ""

    def _get_anti_ai_keywords(self, fake_signals: list[FakeSignal]) -> str:
        """Get negative prompt keywords to counter AI artifacts."""
        keywords = []

        for signal in fake_signals:
            signal_lower = signal.signal.lower()

            if "smooth" in signal_lower:
                keywords.append("plastic skin")
                keywords.append("airbrushed")
            if "symmetr" in signal_lower:
                keywords.append("perfect symmetry")
            if "uniform" in signal_lower:
                keywords.append("uniform texture")
            if "clean" in signal_lower:
                keywords.append("too clean")
            if "perfect" in signal_lower:
                keywords.append("artificial perfection")

        return ", ".join(list(set(keywords))) if keywords else ""

    def _get_model_parameters(
        self,
        strategy: Strategy,
        scene_classification: SceneClassification,
        expression_mode: str = "preserve",
    ) -> dict:
        """
        Get model parameters based on strategy priority.
        
        Updated with more conservative denoising values to preserve identity
        and expression when needed.
        """
        # Base parameters - conservative to preserve original image
        params = {
            "steps": 20,
            "cfg_scale": 7.0,
            "sampler": "DPM++ 2M Karras",
            "seed": -1,
        }

        # New denoising strength mapping - more conservative
        # Lower = more preservation, Higher = more change
        priority_to_strength = {
            Priority.VERY_LOW: 0.10,  # Was 0.15
            Priority.LOW: 0.18,       # Was 0.25
            Priority.MEDIUM: 0.25,    # Was 0.35
        }
        base_strength = priority_to_strength.get(strategy.priority, 0.18)
        
        # Adjust based on scene type - portraits need more care
        if scene_classification.primary_scene.lower() == "portrait":
            # Reduce denoising for portraits to preserve facial features
            base_strength *= 0.8
        
        # Adjust based on expression mode
        if expression_mode == "correct":
            # Expression correction needs higher denoising
            base_strength = max(0.25, base_strength)  # At least 0.25 for expression correction
            base_strength = min(0.35, base_strength * 1.3)  # But not more than 0.35
        
        params["denoising_strength"] = base_strength

        # Adjust based on AI likelihood - but more conservatively
        if scene_classification.ai_likelihood > 0.7:
            # Moderate increase for highly AI-looking images
            params["denoising_strength"] = min(0.35, params["denoising_strength"] + 0.05)
            params["steps"] = 25
        
        # Round to 2 decimal places
        params["denoising_strength"] = round(params["denoising_strength"], 2)

        return params
    
    def get_denoising_for_agent(
        self,
        intensity: str,
        expression_mode: str = "preserve",
        scene_type: str = "portrait",
    ) -> float:
        """
        Get recommended denoising strength for an agent based on intensity and expression mode.
        
        Args:
            intensity: "light", "medium", or "strong"
            expression_mode: "preserve" or "correct"
            scene_type: Type of scene (portrait, landscape, etc.)
            
        Returns:
            Recommended denoising strength
        """
        # Base denoising by intensity
        intensity_to_denoising = {
            "light": 0.10,
            "medium": 0.18,
            "strong": 0.28,
        }
        base = intensity_to_denoising.get(intensity, 0.18)
        
        # Adjust for expression mode
        if expression_mode == "correct":
            # Expression correction needs higher denoising
            correction_adjustments = {
                "light": 0.20,   # Light correction
                "medium": 0.28,  # Standard correction
                "strong": 0.35,  # Strong correction
            }
            base = correction_adjustments.get(intensity, 0.28)
        
        # Adjust for portraits - slightly lower to preserve identity
        if scene_type.lower() == "portrait" and expression_mode == "preserve":
            base *= 0.85
        
        return round(min(0.40, base), 2)  # Cap at 0.40

    def _generate_reasoning(
        self,
        scene_classification: SceneClassification,
        fake_signals: list[FakeSignal],
        strategy: Strategy,
    ) -> str:
        """Generate human-readable reasoning for model selection."""
        parts = []

        # Scene type reasoning
        parts.append(
            f"图像类型: {scene_classification.primary_scene}"
        )

        # AI likelihood
        likelihood_desc = "低" if scene_classification.ai_likelihood < 0.4 else \
                         "中等" if scene_classification.ai_likelihood < 0.7 else "高"
        parts.append(f"AI生成可能性: {likelihood_desc} ({scene_classification.ai_likelihood:.0%})")

        # Main issues
        high_severity = [s for s in fake_signals if s.severity == Severity.HIGH]
        medium_severity = [s for s in fake_signals if s.severity == Severity.MEDIUM]

        if high_severity:
            parts.append(f"严重问题: {len(high_severity)}个")
        if medium_severity:
            parts.append(f"中等问题: {len(medium_severity)}个")

        # Enhancement approach
        parts.append(f"增强策略: {strategy.goal}")

        return " | ".join(parts)
