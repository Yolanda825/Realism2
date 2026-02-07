"""Lighting Enhancement Agent - Specializes in fixing lighting-related AI artifacts."""

from app.agents.base import BaseEnhancementAgent, EnhancementContext, AgentResult, AgentType
from app.services.llm_client import get_llm_client


class LightingEnhancementAgent(BaseEnhancementAgent):
    """
    Agent specialized in fixing lighting-related AI artifacts.
    
    Handles:
    - Inconsistent shadow directions
    - Unnatural highlights
    - Missing light falloff
    - Physically impossible lighting
    - Incorrect ambient lighting
    """
    
    agent_type = AgentType.LIGHTING
    
    # Keywords that indicate lighting-related issues
    LIGHTING_KEYWORDS = [
        "light", "光", "shadow", "阴影", "highlight", "高光",
        "reflection", "反射", "dark", "暗", "bright", "亮",
        "illuminat", "照明", "falloff", "衰减", "ambient", "环境光"
    ]
    
    def __init__(self):
        self.llm_client = get_llm_client()
    
    async def can_handle(self, context: EnhancementContext) -> bool:
        """Check if there are lighting-related issues to fix."""
        relevant_signals = self._find_relevant_signals(context, self.LIGHTING_KEYWORDS)
        return len(relevant_signals) > 0
    
    async def enhance(self, context: EnhancementContext) -> AgentResult:
        """Execute lighting enhancement based on the provided prompt."""
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
                
                description = f"光线优化 ({intensity_desc}强度) - 目标区域: {', '.join(prompt.target_areas) if prompt.target_areas else '全局'}"
            else:
                changes_made = ["统一光源方向", "柔化阴影边缘"]
                description = "光线优化 - 使用默认设置"
            
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
                description="光线优化失败",
                error_message=str(e),
                prompt_used=self._get_prompt_dict(context),
            )
