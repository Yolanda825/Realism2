"""Color Enhancement Agent - Specializes in fixing color-related AI artifacts."""

from app.agents.base import BaseEnhancementAgent, EnhancementContext, AgentResult, AgentType
from app.services.llm_client import get_llm_client


class ColorEnhancementAgent(BaseEnhancementAgent):
    """
    Agent specialized in fixing color-related AI artifacts.
    
    Handles:
    - Over-saturation
    - HDR look
    - Unnatural color gradients
    - Color temperature issues
    - Color banding
    """
    
    agent_type = AgentType.COLOR
    
    # Keywords that indicate color-related issues
    COLOR_KEYWORDS = [
        "color", "颜色", "saturat", "饱和", "hdr", "vibrant", "鲜艳",
        "tone", "色调", "gradient", "渐变", "temperature", "色温",
        "warm", "暖", "cool", "冷", "tint", "偏色",
        "contrast", "对比", "fade", "褪色", "vivid", "艳丽"
    ]
    
    def __init__(self):
        self.llm_client = get_llm_client()
    
    async def can_handle(self, context: EnhancementContext) -> bool:
        """Check if there are color-related issues to fix."""
        relevant_signals = self._find_relevant_signals(context, self.COLOR_KEYWORDS)
        return len(relevant_signals) > 0
    
    async def enhance(self, context: EnhancementContext) -> AgentResult:
        """Execute color enhancement based on the provided prompt."""
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
                
                description = f"色彩优化 ({intensity_desc}强度) - 目标区域: {', '.join(prompt.target_areas) if prompt.target_areas else '全局'}"
            else:
                changes_made = ["降低过度饱和", "统一色温"]
                description = "色彩优化 - 使用默认设置"
            
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
                description="色彩优化失败",
                error_message=str(e),
                prompt_used=self._get_prompt_dict(context),
            )
