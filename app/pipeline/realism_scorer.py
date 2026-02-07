"""Stage 6: Realism Scorer - Estimates realism improvement after enhancement."""

from app.models.schemas import (
    SceneClassification,
    FakeSignal,
    Strategy,
    ExecutionPlan,
    RealismScore,
    Severity,
    Priority,
    AIConfidenceLevel,
)


AI_LEVEL_DESCRIPTIONS = {
    AIConfidenceLevel.VERY_LOW: "几乎无AI痕迹，图像非常真实",
    AIConfidenceLevel.LOW: "轻微AI痕迹，图像较为真实",
    AIConfidenceLevel.MEDIUM: "中等AI痕迹，图像有一定AI特征",
    AIConfidenceLevel.HIGH: "明显AI痕迹，图像AI特征较明显",
    AIConfidenceLevel.VERY_HIGH: "严重AI痕迹，图像明显为AI生成",
}


class RealismScorer:
    """Estimates realism scores before and after enhancement."""

    def __init__(self):
        """Initialize the realism scorer."""
        pass

    async def score(
        self,
        scene_classification: SceneClassification,
        fake_signals: list[FakeSignal],
        strategy: Strategy,
        execution_plan: ExecutionPlan,
    ) -> RealismScore:
        """
        Estimate realism scores with AI confidence level.

        Args:
            scene_classification: Scene classification results
            fake_signals: Detected fake signals
            strategy: The enhancement strategy
            execution_plan: The execution plan

        Returns:
            RealismScore with before/after estimates, AI level, and confidence
        """
        before_score = self._calculate_before_score(
            scene_classification.ai_likelihood,
            fake_signals
        )

        improvement = self._calculate_improvement(
            fake_signals,
            strategy,
            execution_plan
        )

        after_score = min(1.0, before_score + improvement)

        confidence = self._calculate_confidence(
            scene_classification,
            fake_signals,
            strategy
        )

        ai_level = self._calculate_ai_level(after_score)
        level_description = AI_LEVEL_DESCRIPTIONS.get(ai_level, "")

        notes = self._generate_notes(
            before_score,
            after_score,
            fake_signals,
            strategy
        )

        return RealismScore(
            before=round(before_score, 3),
            after=round(after_score, 3),
            ai_score_level=ai_level,
            ai_score_level_description=level_description,
            confidence=round(confidence, 3),
            notes=notes,
        )

    def should_continue_iteration(self, ai_level: AIConfidenceLevel) -> bool:
        """
        Determine if another iteration should be performed.

        Args:
            ai_level: The current AI confidence level

        Returns:
            True if should continue (level is high or very_high), False otherwise
        """
        return ai_level in [AIConfidenceLevel.HIGH, AIConfidenceLevel.VERY_HIGH]

    def _calculate_ai_level(self, realism_score: float) -> AIConfidenceLevel:
        """
        Convert realism score to AI confidence level.

        Args:
            realism_score: Realism score (0-1, higher is more realistic)

        Returns:
            Corresponding AI confidence level
        """
        if realism_score >= 0.85:
            return AIConfidenceLevel.VERY_LOW
        elif realism_score >= 0.65:
            return AIConfidenceLevel.LOW
        elif realism_score >= 0.45:
            return AIConfidenceLevel.MEDIUM
        elif realism_score >= 0.25:
            return AIConfidenceLevel.HIGH
        else:
            return AIConfidenceLevel.VERY_HIGH

    def _calculate_before_score(
        self,
        ai_likelihood: float,
        fake_signals: list[FakeSignal],
    ) -> float:
        """Calculate the initial realism score."""
        # Start with inverse of AI likelihood
        base_score = 1.0 - ai_likelihood

        # Penalize for each fake signal based on severity
        severity_penalties = {
            Severity.LOW: 0.03,
            Severity.MEDIUM: 0.07,
            Severity.HIGH: 0.12,
        }

        total_penalty = sum(
            severity_penalties.get(signal.severity, 0.05)
            for signal in fake_signals
        )

        # Cap the penalty at 0.5 to avoid negative scores
        total_penalty = min(0.5, total_penalty)

        return max(0.0, base_score - total_penalty)

    def _calculate_improvement(
        self,
        fake_signals: list[FakeSignal],
        strategy: Strategy,
        execution_plan: ExecutionPlan,
    ) -> float:
        """Calculate expected improvement from enhancements."""
        if not strategy.operations:
            return 0.0

        # Base improvement from addressing fake signals
        signal_improvement = 0.0
        for signal in fake_signals:
            if signal.severity == Severity.HIGH:
                signal_improvement += 0.05
            elif signal.severity == Severity.MEDIUM:
                signal_improvement += 0.03
            else:
                signal_improvement += 0.01

        # Improvement from operations
        operation_improvement = 0.0
        total_instructions = (
            len(execution_plan.lighting_module) +
            len(execution_plan.texture_module) +
            len(execution_plan.noise_module)
        )

        # Each instruction contributes based on strategy priority
        priority_multipliers = {
            Priority.VERY_LOW: 0.005,
            Priority.LOW: 0.01,
            Priority.MEDIUM: 0.015,
        }

        multiplier = priority_multipliers.get(strategy.priority, 0.01)
        operation_improvement = total_instructions * multiplier

        # Total improvement capped at reasonable levels
        total_improvement = signal_improvement + operation_improvement
        return min(0.3, total_improvement)  # Max 30% improvement

    def _calculate_confidence(
        self,
        scene_classification: SceneClassification,
        fake_signals: list[FakeSignal],
        strategy: Strategy,
    ) -> float:
        """Calculate confidence in the score estimation."""
        confidence = 0.7  # Base confidence

        # Higher confidence if scene type is well-known
        known_scenes = ["portrait", "landscape", "interior", "product", "street"]
        if scene_classification.primary_scene.lower() in known_scenes:
            confidence += 0.1

        # Higher confidence with more fake signals (more data)
        if len(fake_signals) > 2:
            confidence += 0.05
        elif len(fake_signals) == 0:
            confidence -= 0.1  # Less confident if no signals detected

        # Higher confidence with more operations planned
        if len(strategy.operations) > 3:
            confidence += 0.05

        # Higher confidence if constraints are specified
        if len(strategy.constraints) > 2:
            confidence += 0.05

        return min(0.95, max(0.4, confidence))

    def _generate_notes(
        self,
        before_score: float,
        after_score: float,
        fake_signals: list[FakeSignal],
        strategy: Strategy,
    ) -> str:
        """Generate explanatory notes for the score."""
        notes = []

        # Comment on before score
        if before_score < 0.4:
            notes.append("Image shows significant AI-generated characteristics.")
        elif before_score < 0.6:
            notes.append("Image shows moderate AI-generated characteristics.")
        elif before_score < 0.8:
            notes.append("Image shows minor AI-generated characteristics.")
        else:
            notes.append("Image appears relatively realistic.")

        # Comment on improvement
        improvement = after_score - before_score
        if improvement > 0.15:
            notes.append("Significant improvement expected from enhancements.")
        elif improvement > 0.05:
            notes.append("Moderate improvement expected from enhancements.")
        elif improvement > 0:
            notes.append("Minor improvement expected from enhancements.")
        else:
            notes.append("No enhancement needed or possible.")

        # Highlight main issues
        high_severity_signals = [s for s in fake_signals if s.severity == Severity.HIGH]
        if high_severity_signals:
            notes.append(f"Primary issues: {len(high_severity_signals)} high-severity artifacts detected.")

        return " ".join(notes)
