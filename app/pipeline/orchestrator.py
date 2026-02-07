"""Pipeline Orchestrator - Coordinates all enhancement stages."""

from app.models.schemas import (
    PipelineResult,
    SceneClassification,
    FakeSignal,
    RealismConstraints,
    Strategy,
    ExecutionPlan,
    RealismScore,
    ModelRouting,
    EnhancementResult,
    ExpertEnhancementResult,
    IterationResult,
    ExpertAgentResult,
    DimensionSignals,
    AIConfidenceLevel,
)
from app.pipeline.scene_classifier import SceneClassifier
from app.pipeline.fake_detector import FakeSignalDetector
from app.pipeline.rag_module import RAGModule
from app.pipeline.strategy_gen import StrategyGenerator
from app.pipeline.execution_plan import ExecutionPlanner
from app.pipeline.realism_scorer import RealismScorer
from app.pipeline.prompt_generator import PromptGenerator
from app.agents.enhancement_orchestrator import (
    EnhancementOrchestrator as ExpertOrchestrator,
    EnhancementOrchestratorResult,
)
from app.services.image_model import get_image_model_client

MAX_ITERATIONS = 3
STOP_LEVELS = [AIConfidenceLevel.VERY_LOW, AIConfidenceLevel.LOW, AIConfidenceLevel.MEDIUM]
CONTINUE_LEVELS = [AIConfidenceLevel.HIGH, AIConfidenceLevel.VERY_HIGH]


class PipelineOrchestrator:
    """
    Orchestrates the complete image realism enhancement pipeline.

    Pipeline stages:
    1. Scene Classifier - Analyze image and classify scene type
    2. Fake Signal Detector - Identify AI-generated artifacts
    3. RAG Module - Retrieve realism constraints for scene type
    4. Strategy Generator - Create enhancement strategy
    5. Execution Planner - Generate module-specific instructions
    6. Realism Scorer - Estimate realism improvement
    7. Expert Enhancement - Use expert agents to enhance the image (with iteration)
    """

    def __init__(self):
        """Initialize all pipeline components."""
        self.scene_classifier = SceneClassifier()
        self.fake_detector = FakeSignalDetector()
        self.rag_module = RAGModule()
        self.strategy_generator = StrategyGenerator()
        self.execution_planner = ExecutionPlanner()
        self.realism_scorer = RealismScorer()
        self.prompt_generator = PromptGenerator()
        self.expert_orchestrator = ExpertOrchestrator()
        self.image_model_client = get_image_model_client()

    async def process(
        self,
        image_base64: str,
        enhance_image: bool = True,
        use_expert_system: bool = False,
    ) -> PipelineResult:
        """
        Process an image through the complete pipeline.

        Args:
            image_base64: Base64-encoded image data
            enhance_image: Whether to perform actual image enhancement
            use_expert_system: Whether to use the expert agent system (default False for simplified flow)

        Returns:
            PipelineResult containing all stage outputs and enhanced image
        """
        # Stage 1: Scene Classification
        scene_classification = await self.scene_classifier.classify(image_base64)

        # Stage 2: Fake Signal Detection with dimension categorization
        fake_signals = await self.fake_detector.detect(image_base64)
        dimension_signals = self.fake_detector.categorize_by_dimension(fake_signals)

        # Stage 3: RAG - Retrieve Realism Constraints
        realism_constraints = await self.rag_module.retrieve_constraints(
            scene_classification.primary_scene
        )

        # Stage 4: Strategy Generation
        strategy = await self.strategy_generator.generate(
            scene_classification=scene_classification,
            fake_signals=fake_signals,
            realism_constraints=realism_constraints,
        )

        # Stage 5: Execution Planning
        execution_plan = await self.execution_planner.create_plan(strategy)

        # Stage 6: Realism Scoring (initial estimate)
        realism_score = await self.realism_scorer.score(
            scene_classification=scene_classification,
            fake_signals=fake_signals,
            strategy=strategy,
            execution_plan=execution_plan,
        )

        # Stage 7: Simplified Enhancement with iteration (default flow)
        expert_enhancement = None
        model_routing = None
        enhancement_result = None
        final_image = image_base64
        final_score = realism_score

        if enhance_image:
            if use_expert_system:
                # Use expert agent system
                expert_result = await self.expert_orchestrator.enhance(
                    image_base64=image_base64,
                    scene_type=scene_classification.primary_scene,
                    initial_ai_likelihood=scene_classification.ai_likelihood,
                    initial_fake_signals=fake_signals,
                )
                expert_enhancement = self._convert_expert_result(expert_result)
                enhancement_result = EnhancementResult(
                    success=expert_result.success,
                    enhanced_image_base64=expert_result.enhanced_image_base64,
                    error_message=None if expert_result.success else "Enhancement failed",
                )
                final_image = expert_result.enhanced_image_base64
            else:
                # Simplified flow: strategy -> image model -> iteration
                result = await self._simple_iterate(
                    image_base64=image_base64,
                    scene_classification=scene_classification,
                    fake_signals=fake_signals,
                    dimension_signals=dimension_signals,
                    realism_constraints=realism_constraints,
                )
                enhancement_result = EnhancementResult(
                    success=result["success"],
                    enhanced_image_base64=result["enhanced_image"],
                    error_message=result.get("error"),
                )
                final_image = result["enhanced_image"]
                final_score = result["final_score"]

        return PipelineResult(
            scene_classification=scene_classification,
            dimension_signals=dimension_signals,
            fake_signals=fake_signals,
            realism_constraints=realism_constraints,
            strategy=strategy,
            execution_plan=execution_plan,
            realism_score=final_score,
            expert_enhancement=expert_enhancement,
            model_routing=model_routing,
            enhancement_result=enhancement_result,
        )

    def _convert_expert_result(
        self,
        result: EnhancementOrchestratorResult,
    ) -> ExpertEnhancementResult:
        """Convert internal expert result to schema format."""
        iterations = []
        for it in result.iterations:
            agent_results = []
            for ar in it.agent_results:
                agent_results.append(ExpertAgentResult(
                    agent_type=ar.agent_type.value,
                    success=ar.success,
                    description=ar.description,
                    changes_made=ar.changes_made,
                    error_message=ar.error_message,
                ))
            
            iterations.append(IterationResult(
                iteration=it.iteration,
                ai_likelihood_before=it.ai_likelihood_before,
                ai_likelihood_after=it.ai_likelihood_after,
                agents_invoked=[a.value for a in it.agents_invoked],
                agent_results=agent_results,
                routing_reasoning=it.routing_decision.reasoning,
            ))
        
        return ExpertEnhancementResult(
            success=result.success,
            total_iterations=result.total_iterations,
            initial_ai_likelihood=result.initial_ai_likelihood,
            final_ai_likelihood=result.final_ai_likelihood,
            iterations=iterations,
            summary=result.summary,
            stopped_reason=result.stopped_reason,
            enhanced_image_base64=result.enhanced_image_base64,
        )

    async def _simple_iterate(
        self,
        image_base64: str,
        scene_classification: SceneClassification,
        fake_signals: list[FakeSignal],
        dimension_signals: DimensionSignals,
        realism_constraints: RealismConstraints,
    ) -> dict:
        """
        Simplified enhancement loop: strategy -> image model -> re-score -> iterate.

        Loop logic:
        - If AI level is medium or below: stop and output current image
        - If AI level is high or very_high: generate new image and re-score
        - Maximum 3 iterations

        Args:
            image_base64: Current image (base64)
            scene_classification: Scene classification result
            fake_signals: Detected fake signals
            dimension_signals: Signals categorized by dimension
            realism_constraints: Retrieved constraints

        Returns:
            dict with success, enhanced_image, final_score, iterations, stopped_reason
        """
        current_image = image_base64
        current_fake_signals = fake_signals
        current_dimension_signals = dimension_signals
        iterations_data = []

        for iteration in range(1, MAX_ITERATIONS + 1):
            # Generate strategy for current signals
            strategy = await self.strategy_generator.generate(
                scene_classification=scene_classification,
                fake_signals=current_fake_signals,
                realism_constraints=realism_constraints,
            )
            execution_plan = await self.execution_planner.create_plan(strategy)

            # Score before enhancement
            score_before = await self.realism_scorer.score(
                scene_classification=scene_classification,
                fake_signals=current_fake_signals,
                strategy=strategy,
                execution_plan=execution_plan,
            )

            # Do not stop solely based on initial AI level. We decide stopping based on improvement after enhancement.

            # Generate model routing from strategy
            model_routing = self.prompt_generator.generate_routing(
                scene_classification=scene_classification,
                fake_signals=current_fake_signals,
                strategy=strategy,
                execution_plan=execution_plan,
            )

            # Execute enhancement
            enhancement_result = await self.image_model_client.execute_enhancement(
                image_base64=current_image,
                model_routing=model_routing,
            )

            if not enhancement_result.success:
                return {
                    "success": False,
                    "enhanced_image": current_image,
                    "final_score": score_before,
                    "iterations": iteration - 1,
                    "stopped_reason": f"Image enhancement failed at iteration {iteration}: {enhancement_result.error_message}",
                    "iterations_data": iterations_data,
                    "error": enhancement_result.error_message,
                }

            enhanced_image = enhancement_result.enhanced_image_base64

            # Re-score the enhanced image
            new_fake_signals = await self.fake_detector.detect(enhanced_image)
            new_dimension_signals = self.fake_detector.categorize_by_dimension(new_fake_signals)
            new_execution_plan = await self.execution_planner.create_plan(strategy)
            score_after = await self.realism_scorer.score(
                scene_classification=scene_classification,
                fake_signals=new_fake_signals,
                strategy=strategy,
                execution_plan=new_execution_plan,
            )

            # Record iteration
            iterations_data.append({
                "iteration": iteration,
                "ai_score_level_before": score_before.ai_score_level.value,
                "ai_score_level_after": score_after.ai_score_level.value,
                "strategy_goal": strategy.goal,
                "model_routing_reasoning": model_routing.reasoning,
            })

            # Update for next iteration
            current_image = enhanced_image
            current_fake_signals = new_fake_signals
            current_dimension_signals = new_dimension_signals

            # Decide whether to continue or stop based on improvement
            improvement = score_after.after - score_before.before
            if improvement > 0:
                if score_after.ai_score_level in STOP_LEVELS:
                    return {
                        "success": True,
                        "enhanced_image": current_image,
                        "final_score": score_after,
                        "iterations": iteration,
                        "stopped_reason": f"AI level improved to {score_after.ai_score_level.value}, stopping iteration",
                        "iterations_data": iterations_data,
                    }
            else:
                # No improvement; allow another round if we haven't reached MAX_ITERATIONS yet
                if iteration >= MAX_ITERATIONS:
                    return {
                        "success": True,
                        "enhanced_image": current_image,
                        "final_score": score_after,
                        "iterations": iteration,
                        "stopped_reason": "no_improvement_max_reached",
                        "iterations_data": iterations_data,
                    }

        # Max iterations reached
        final_score = await self.realism_scorer.score(
            scene_classification=scene_classification,
            fake_signals=current_fake_signals,
            strategy=strategy,
            execution_plan=execution_plan,
        )
        return {
            "success": True,
            "enhanced_image": current_image,
            "final_score": final_score,
            "iterations": MAX_ITERATIONS,
            "stopped_reason": f"Reached maximum iterations ({MAX_ITERATIONS})",
            "iterations_data": iterations_data,
        }

    async def analyze_only(self, image_base64: str) -> PipelineResult:
        """
        Run analysis without image enhancement.

        Args:
            image_base64: Base64-encoded image data

        Returns:
            PipelineResult with analysis only (no enhanced image)
        """
        return await self.process(image_base64, enhance_image=False)


# Global orchestrator instance
_orchestrator = None


def get_orchestrator() -> PipelineOrchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PipelineOrchestrator()
    return _orchestrator
