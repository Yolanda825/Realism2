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

    async def process(
        self,
        image_base64: str,
        enhance_image: bool = True,
        use_expert_system: bool = True,
    ) -> PipelineResult:
        """
        Process an image through the complete pipeline.

        Args:
            image_base64: Base64-encoded image data
            enhance_image: Whether to perform actual image enhancement
            use_expert_system: Whether to use the expert agent system

        Returns:
            PipelineResult containing all stage outputs and enhanced image
        """
        # Stage 1: Scene Classification
        scene_classification = await self.scene_classifier.classify(image_base64)

        # Stage 2: Fake Signal Detection
        fake_signals = await self.fake_detector.detect(image_base64)

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

        # Stage 7: Expert Enhancement (if enabled)
        expert_enhancement = None
        model_routing = None
        enhancement_result = None

        if enhance_image:
            if use_expert_system:
                # Use the new expert agent system
                expert_result = await self.expert_orchestrator.enhance(
                    image_base64=image_base64,
                    scene_type=scene_classification.primary_scene,
                    initial_ai_likelihood=scene_classification.ai_likelihood,
                    initial_fake_signals=fake_signals,
                )
                
                # Convert to schema format
                expert_enhancement = self._convert_expert_result(expert_result)
                
                # Also populate legacy fields for backward compatibility
                enhancement_result = EnhancementResult(
                    success=expert_result.success,
                    enhanced_image_base64=expert_result.enhanced_image_base64,
                    error_message=None if expert_result.success else "Enhancement failed",
                )
            else:
                # Use legacy prompt-based enhancement
                model_routing = self.prompt_generator.generate_routing(
                    scene_classification=scene_classification,
                    fake_signals=fake_signals,
                    strategy=strategy,
                    execution_plan=execution_plan,
                )

        # Assemble final result
        return PipelineResult(
            scene_classification=scene_classification,
            fake_signals=fake_signals,
            realism_constraints=realism_constraints,
            strategy=strategy,
            execution_plan=execution_plan,
            realism_score=realism_score,
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
