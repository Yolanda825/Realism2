"""Stage 6: Realism Scorer - Estimates realism improvement after enhancement."""

from app.models.schemas import (
    SceneClassification,
    FakeSignal,
    Strategy,
    ExecutionPlan,
    RealismScore,
    Severity,
    Priority,
)


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
        Estimate realism scores.

        This is a heuristic-based scorer that estimates improvement
        based on the analysis and planned enhancements.

        Args:
            scene_classification: Scene classification results
            fake_signals: Detected fake signals
            strategy: The enhancement strategy
            execution_plan: The execution plan

        Returns:
            RealismScore with before/after estimates and confidence
        """
        # Calculate "before" score based on AI likelihood and fake signals
        before_score = self._calculate_before_score(
            scene_classification.ai_likelihood,
            fake_signals
        )

        # Calculate expected improvement based on strategy and plan
        improvement = self._calculate_improvement(
            fake_signals,
            strategy,
            execution_plan
        )

        # Calculate "after" score
        after_score = min(1.0, before_score + improvement)

        # Calculate confidence based on analysis quality
        confidence = self._calculate_confidence(
            scene_classification,
            fake_signals,
            strategy
        )

        # Generate notes
        notes = self._generate_notes(
            before_score,
            after_score,
            fake_signals,
            strategy
        )

        return RealismScore(
            before=round(before_score, 3),
            after=round(after_score, 3),
            confidence=round(confidence, 3),
            notes=notes,
        )

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
