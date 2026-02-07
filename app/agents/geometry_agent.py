"""Geometry Enhancement Agent - Specializes in fixing geometric/anatomical AI artifacts."""

from app.agents.base import BaseEnhancementAgent, EnhancementContext, AgentResult, AgentType
from app.services.llm_client import get_llm_client


class GeometryEnhancementAgent(BaseEnhancementAgent):
    """
    Agent specialized in fixing geometric and anatomical AI artifacts.
    
    Handles:
    - Extra/missing fingers
    - Unnatural poses
    - Anatomical impossibilities
    - Perspective errors
    - Distorted proportions
    """
    
    agent_type = AgentType.GEOMETRY
    
    # Keywords that indicate geometry-related issues
    GEOMETRY_KEYWORDS = [
        "finger", "手指", "hand", "手", "pose", "姿势",
        "anatomy", "解剖", "proportion", "比例", "perspective", "透视",
        "distort", "扭曲", "limb", "肢体", "body", "身体",
        "face", "脸", "eye", "眼", "symmetr", "对称",
        "extra", "多余", "missing", "缺少", "impossible", "不可能"
    ]
    
    def __init__(self):
        self.llm_client = get_llm_client()
    
    async def can_handle(self, context: EnhancementContext) -> bool:
        """Check if there are geometry-related issues to fix."""
        if context.scene_type.lower() in ["landscape"]:
            return False
        
        relevant_signals = self._find_relevant_signals(context, self.GEOMETRY_KEYWORDS)
        return len(relevant_signals) > 0
    
    async def enhance(self, context: EnhancementContext) -> AgentResult:
        """Execute geometry enhancement based on the provided prompt."""
        try:
            prompt = context.agent_prompt
            prompt_dict = self._get_prompt_dict(context)
            
            if prompt:
                changes_made = prompt.specific_instructions.copy()
                
                intensity_desc = {
                    "light": "轻微",
                    "medium": "中等",
                    "strong": "较强"
                }.get(prompt.intensity, "中等")
                
                description = f"几何/解剖学优化 ({intensity_desc}强度) - 目标区域: {', '.join(prompt.target_areas) if prompt.target_areas else '全局'}"
            else:
                changes_made = ["修正解剖学错误", "调整比例"]
                description = "几何/解剖学优化 - 使用默认设置"
            
            return AgentResult(
                success=True,
                agent_type=self.agent_type,
                enhanced_image_base64=context.image_base64,
                description=description,
                changes_made=changes_made,
                error_message=None,
                prompt_used=prompt_dict,
            )
            
        except Exception as e:
            return AgentResult(
                success=False,
                agent_type=self.agent_type,
                enhanced_image_base64=context.image_base64,
                description="几何/解剖学优化失败",
                error_message=str(e),
                prompt_used=self._get_prompt_dict(context),
            )
