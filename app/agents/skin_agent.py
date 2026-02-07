"""Skin Enhancement Agent - Specializes in fixing skin-related AI artifacts."""

from app.agents.base import BaseEnhancementAgent, EnhancementContext, AgentResult, AgentType
from app.services.llm_client import get_llm_client


class SkinEnhancementAgent(BaseEnhancementAgent):
    """
    Agent specialized in fixing skin-related AI artifacts.
    
    Handles:
    - Over-smooth skin (plastic look)
    - Missing pores and skin texture
    - Unnatural skin uniformity
    - Waxy or artificial skin appearance
    """
    
    agent_type = AgentType.SKIN
    
    # Keywords that indicate skin-related issues
    SKIN_KEYWORDS = [
        "skin", "皮肤", "smooth", "光滑", "plastic", "塑料",
        "pore", "毛孔", "waxy", "蜡", "texture", "纹理",
        "face", "脸", "airbrushed", "磨皮"
    ]
    
    def __init__(self):
        self.llm_client = get_llm_client()
    
    async def can_handle(self, context: EnhancementContext) -> bool:
        """Check if there are skin-related issues to fix."""
        # Only applicable for portraits or images with people
        if context.scene_type.lower() not in ["portrait", "street", "other"]:
            return False
        
        relevant_signals = self._find_relevant_signals(context, self.SKIN_KEYWORDS)
        return len(relevant_signals) > 0
    
    async def enhance(self, context: EnhancementContext) -> AgentResult:
        """Execute skin enhancement based on the provided prompt."""
        try:
            # Get the prompt from router
            prompt = context.agent_prompt
            prompt_dict = self._get_prompt_dict(context)
            
            if prompt:
                # Use the specific instructions from the router
                changes_made = prompt.specific_instructions.copy()
                
                # Build description based on prompt
                intensity_desc = {
                    "light": "轻微",
                    "medium": "中等",
                    "strong": "较强"
                }.get(prompt.intensity, "中等")
                
                description = f"皮肤优化 ({intensity_desc}强度) - 目标区域: {', '.join(prompt.target_areas) if prompt.target_areas else '全局'}"
                
                # In a real implementation, this would call an image processing API
                # using prompt.positive_prompt and prompt.negative_prompt
                
            else:
                # Fallback if no prompt provided
                changes_made = ["添加皮肤纹理细节", "增加自然毛孔"]
                description = "皮肤优化 - 使用默认设置"
            
            return AgentResult(
                success=True,
                agent_type=self.agent_type,
                enhanced_image_base64=context.image_base64,  # Would be modified in real impl
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
                description="皮肤优化失败",
                error_message=str(e),
                prompt_used=self._get_prompt_dict(context),
            )
