"""Texture Enhancement Agent - Specializes in fixing texture-related AI artifacts."""

from app.agents.base import BaseEnhancementAgent, EnhancementContext, AgentResult, AgentType
from app.services.llm_client import get_llm_client


class TextureEnhancementAgent(BaseEnhancementAgent):
    """
    Agent specialized in fixing texture-related AI artifacts.
    
    Handles:
    - Over-uniform textures
    - Missing micro-details
    - Unnatural material surfaces
    - Repetitive patterns
    - Too clean surfaces
    """
    
    agent_type = AgentType.TEXTURE
    
    # Keywords that indicate texture-related issues
    TEXTURE_KEYWORDS = [
        "texture", "纹理", "uniform", "均匀", "pattern", "图案",
        "detail", "细节", "surface", "表面", "material", "材质",
        "clean", "干净", "smooth", "平滑", "repetit", "重复",
        "micro", "微观", "grain", "颗粒"
    ]
    
    def __init__(self):
        self.llm_client = get_llm_client()
    
    async def can_handle(self, context: EnhancementContext) -> bool:
        """Check if there are texture-related issues to fix."""
        relevant_signals = self._find_relevant_signals(context, self.TEXTURE_KEYWORDS)
        return len(relevant_signals) > 0
    
    async def enhance(self, context: EnhancementContext) -> AgentResult:
        """Execute texture enhancement based on the provided prompt."""
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
                
                description = f"纹理优化 ({intensity_desc}强度) - 目标区域: {', '.join(prompt.target_areas) if prompt.target_areas else '全局'}"
            else:
                changes_made = ["增加表面细节", "添加自然磨损感"]
                description = "纹理优化 - 使用默认设置"
            
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
                description="纹理优化失败",
                error_message=str(e),
                prompt_used=self._get_prompt_dict(context),
            )
