"""Enhancement Orchestrator - Manages the iterative enhancement process."""

from dataclasses import dataclass, field
from typing import Optional
from app.agents.base import EnhancementContext, AgentResult, AgentType
from app.agents.router import RouterAgent, RoutingDecision
from app.pipeline.fake_detector import FakeSignalDetector, ExpressionAnalysis
from app.pipeline.scene_classifier import SceneClassifier
from app.models.schemas import FakeSignal


# Configuration
MAX_ITERATIONS = 3
AI_LIKELIHOOD_THRESHOLD = 0.4  # Target: below this is considered "realistic enough"
IMPROVEMENT_THRESHOLD = 0.05   # Minimum improvement to continue iterating


@dataclass
class IterationResult:
    """Result of a single iteration."""
    iteration: int
    ai_likelihood_before: float
    ai_likelihood_after: float
    agents_invoked: list[AgentType]
    agent_results: list[AgentResult]
    fake_signals_before: list
    fake_signals_after: list
    routing_decision: RoutingDecision
    
    def to_dict(self) -> dict:
        # Extract agent prompts from routing decision
        agent_prompts = []
        for agent_type in self.agents_invoked:
            prompt = self.routing_decision.get_prompt(agent_type)
            if prompt:
                agent_prompts.append(prompt.to_dict())
        
        return {
            "iteration": self.iteration,
            "ai_likelihood_before": self.ai_likelihood_before,
            "ai_likelihood_after": self.ai_likelihood_after,
            "agents_invoked": [a.value for a in self.agents_invoked],
            "agent_results": [r.to_dict() for r in self.agent_results],
            "fake_signals_before_count": len(self.fake_signals_before),
            "fake_signals_after_count": len(self.fake_signals_after),
            "routing_reasoning": self.routing_decision.reasoning,
            "agent_prompts": agent_prompts,
        }


@dataclass
class EnhancementOrchestratorResult:
    """Final result from the enhancement orchestrator."""
    success: bool
    original_image_base64: str
    enhanced_image_base64: str
    total_iterations: int
    initial_ai_likelihood: float
    final_ai_likelihood: float
    iterations: list[IterationResult] = field(default_factory=list)
    final_fake_signals: list = field(default_factory=list)
    summary: str = ""
    stopped_reason: str = ""  # "threshold_reached", "max_iterations", "no_improvement", "error"
    # Expression analysis info
    expression_type: str = "neutral"
    expression_mode: str = "preserve"
    expression_issues: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "total_iterations": self.total_iterations,
            "initial_ai_likelihood": self.initial_ai_likelihood,
            "final_ai_likelihood": self.final_ai_likelihood,
            "iterations": [i.to_dict() for i in self.iterations],
            "final_fake_signals_count": len(self.final_fake_signals),
            "summary": self.summary,
            "stopped_reason": self.stopped_reason,
            "expression_type": self.expression_type,
            "expression_mode": self.expression_mode,
            "expression_issues": self.expression_issues,
        }


class EnhancementOrchestrator:
    """
    Orchestrator for the iterative enhancement process.
    
    Flow:
    1. Detect AI signals in the image
    2. Route to appropriate expert agents
    3. Execute experts sequentially
    4. Re-detect AI likelihood
    5. If AI likelihood > threshold and iterations < max, go to step 2
    6. Return final result
    """
    
    def __init__(self):
        self.router = RouterAgent()
        self.fake_detector = FakeSignalDetector()
        self.scene_classifier = SceneClassifier()
    
    async def enhance(
        self,
        image_base64: str,
        scene_type: str,
        initial_ai_likelihood: float,
        initial_fake_signals: list[FakeSignal],
        expression_analysis: Optional[ExpressionAnalysis] = None,
    ) -> EnhancementOrchestratorResult:
        """
        Run the iterative enhancement process.
        
        Args:
            image_base64: Base64-encoded source image
            scene_type: Type of scene (portrait, landscape, etc.)
            initial_ai_likelihood: Initial AI likelihood from scene classifier
            initial_fake_signals: Initially detected fake signals
            expression_analysis: Optional pre-computed expression analysis
            
        Returns:
            EnhancementOrchestratorResult with all iteration details
        """
        iterations = []
        current_image = image_base64
        current_ai_likelihood = initial_ai_likelihood
        current_fake_signals = initial_fake_signals
        stopped_reason = ""
        
        # Detect expression if not provided (for portraits)
        if expression_analysis is None and scene_type.lower() in ["portrait", "street", "other"]:
            try:
                expression_analysis = await self.fake_detector.detect_expression(image_base64)
            except Exception:
                expression_analysis = ExpressionAnalysis()
        
        # Default expression values
        expression_type = "neutral"
        expression_mode = "preserve"
        expression_issues = []
        expression_natural = True
        
        if expression_analysis:
            expression_type = expression_analysis.expression_type
            expression_natural = expression_analysis.expression_natural
            expression_issues = expression_analysis.expression_issues
            expression_mode = "correct" if expression_analysis.correction_needed else "preserve"
        
        # Check if enhancement is even needed
        if current_ai_likelihood < AI_LIKELIHOOD_THRESHOLD:
            return EnhancementOrchestratorResult(
                success=True,
                original_image_base64=image_base64,
                enhanced_image_base64=image_base64,
                total_iterations=0,
                initial_ai_likelihood=initial_ai_likelihood,
                final_ai_likelihood=current_ai_likelihood,
                iterations=[],
                final_fake_signals=current_fake_signals,
                summary="图像AI痕迹较低，无需增强处理",
                stopped_reason="threshold_reached",
                expression_type=expression_type,
                expression_mode=expression_mode,
                expression_issues=expression_issues,
            )
        
        for iteration in range(MAX_ITERATIONS):
            # Create context for this iteration with expression info
            context = EnhancementContext(
                image_base64=current_image,
                scene_type=scene_type,
                ai_likelihood=current_ai_likelihood,
                fake_signals=current_fake_signals,
                iteration=iteration,
                previous_enhancements=[r.to_dict() for it in iterations for r in it.agent_results],
                expression_type=expression_type,
                expression_mode=expression_mode,
                expression_issues=expression_issues,
                expression_natural=expression_natural,
            )
            
            # Step 1: Route to experts
            routing_decision = await self.router.route(context)
            
            if not routing_decision.agents_to_invoke:
                stopped_reason = "no_agents_needed"
                break
            
            # Step 2: Execute experts sequentially
            agent_results = []
            ai_likelihood_before = current_ai_likelihood
            
            for agent_type in routing_decision.priority_order:
                agent = self.router.get_agent(agent_type)
                if agent:
                    # Update context with current image and agent-specific prompt
                    context.image_base64 = current_image
                    context.agent_prompt = routing_decision.get_prompt(agent_type)
                    
                    # Execute agent
                    result = await agent.enhance(context)
                    agent_results.append(result)
                    
                    # Update current image if successful
                    if result.success and result.enhanced_image_base64:
                        current_image = result.enhanced_image_base64
            
            # Step 3: Re-detect AI likelihood
            fake_signals_before = current_fake_signals
            
            try:
                # Re-classify to get new AI likelihood
                new_classification = await self.scene_classifier.classify(current_image)
                new_ai_likelihood = new_classification.ai_likelihood
                
                # Re-detect fake signals
                new_fake_signals = await self.fake_detector.detect(current_image)
            except Exception:
                # If re-detection fails, use previous values
                new_ai_likelihood = current_ai_likelihood
                new_fake_signals = current_fake_signals
            
            # Record iteration
            iteration_result = IterationResult(
                iteration=iteration + 1,
                ai_likelihood_before=ai_likelihood_before,
                ai_likelihood_after=new_ai_likelihood,
                agents_invoked=routing_decision.priority_order,
                agent_results=agent_results,
                fake_signals_before=fake_signals_before,
                fake_signals_after=new_fake_signals,
                routing_decision=routing_decision,
            )
            iterations.append(iteration_result)
            
            # Update state for next iteration
            previous_ai_likelihood = current_ai_likelihood
            current_ai_likelihood = new_ai_likelihood
            current_fake_signals = new_fake_signals
            
            # Step 4: Check if we should continue
            improvement = previous_ai_likelihood - current_ai_likelihood
            
            if current_ai_likelihood < AI_LIKELIHOOD_THRESHOLD:
                stopped_reason = "threshold_reached"
                break
            
            if improvement < IMPROVEMENT_THRESHOLD:
                stopped_reason = "no_improvement"
                break
        else:
            stopped_reason = "max_iterations"
        
        # Generate summary
        summary = self._generate_summary(
            iterations,
            initial_ai_likelihood,
            current_ai_likelihood,
            stopped_reason,
            expression_type,
            expression_mode,
        )
        
        return EnhancementOrchestratorResult(
            success=True,
            original_image_base64=image_base64,
            enhanced_image_base64=current_image,
            total_iterations=len(iterations),
            initial_ai_likelihood=initial_ai_likelihood,
            final_ai_likelihood=current_ai_likelihood,
            iterations=iterations,
            final_fake_signals=current_fake_signals,
            summary=summary,
            stopped_reason=stopped_reason,
            expression_type=expression_type,
            expression_mode=expression_mode,
            expression_issues=expression_issues,
        )
    
    def _generate_summary(
        self,
        iterations: list[IterationResult],
        initial_likelihood: float,
        final_likelihood: float,
        stopped_reason: str,
        expression_type: str = "neutral",
        expression_mode: str = "preserve",
    ) -> str:
        """Generate a human-readable summary of the enhancement process."""
        if not iterations:
            return "未执行增强处理"
        
        # Count all agents invoked
        all_agents = []
        for it in iterations:
            all_agents.extend(it.agents_invoked)
        
        agent_counts = {}
        for agent in all_agents:
            agent_counts[agent.value] = agent_counts.get(agent.value, 0) + 1
        
        agent_summary = ", ".join([
            f"{name}({count}次)" for name, count in agent_counts.items()
        ])
        
        improvement = initial_likelihood - final_likelihood
        improvement_pct = improvement * 100
        
        reason_text = {
            "threshold_reached": "达到目标阈值",
            "max_iterations": "达到最大迭代次数",
            "no_improvement": "优化效果不明显",
            "no_agents_needed": "无需专家处理",
        }.get(stopped_reason, stopped_reason)
        
        # Expression info
        expression_type_zh = {
            "big_laugh": "大笑",
            "crying": "大哭",
            "surprise": "惊讶",
            "anger": "愤怒",
            "neutral": "中性",
            "other": "其他",
        }.get(expression_type, expression_type)
        
        expression_mode_zh = "保留" if expression_mode == "preserve" else "修正"
        
        summary = (
            f"共执行{len(iterations)}轮优化，"
            f"调用专家: {agent_summary}。"
            f"AI痕迹从{initial_likelihood:.0%}降至{final_likelihood:.0%}，"
            f"改善{improvement_pct:.1f}个百分点。"
        )
        
        # Add expression info if not neutral
        if expression_type != "neutral":
            summary += f" 表情类型: {expression_type_zh}({expression_mode_zh})。"
        
        summary += f"停止原因: {reason_text}"
        
        return summary
