"""Expression Enhancement Agent - Specializes in fixing facial expression muscle issues."""

from app.agents.base import BaseEnhancementAgent, EnhancementContext, AgentResult, AgentType
from app.services.llm_client import get_llm_client


# Expression correction templates with professional muscle guidance
EXPRESSION_CORRECTION_TEMPLATES = {
    "big_laugh": {
        "positive": (
            "Duchenne smile with genuine eye involvement, "
            "crow's feet wrinkles at eye corners from orbicularis oculi contraction, "
            "raised apple cheeks from zygomatic major muscle, "
            "deepened nasolabial folds extending outward, "
            "natural upper teeth exposure with realistic gum line, "
            "eye squint from orbicularis oculi engagement, "
            "slight chin dimpling from mentalis muscle"
        ),
        "negative": (
            "fake smile, eyes wide open while laughing, flat cheeks, "
            "missing crow's feet, perfectly symmetrical smile, "
            "unnatural teeth alignment, plastic expression, stiff smile"
        ),
        "preservation": (
            "maintain overall face shape and identity, preserve hair style, "
            "keep same clothing and background, maintain skin tone"
        ),
        "muscles": [
            "orbicularis_oculi",
            "zygomatic_major",
            "risorius",
            "levator_labii",
            "mentalis",
        ],
        "instructions_zh": [
            "添加眼角鱼尾纹（眼轮匝肌收缩效果）",
            "增强颧骨处苹果肌隆起",
            "加深鼻唇沟并调整走向",
            "修正牙齿暴露的自然度",
            "添加下巴轻微颏肌纹理",
        ],
    },
    "crying": {
        "positive": (
            "corrugator muscle engagement creating vertical frown lines between eyebrows, "
            "reddened eye rims and tear duct area, swollen lower eyelids, "
            "reddened nose tip from blood flow, contracted nasal ala, "
            "mouth corners pulled down by depressor anguli oris, "
            "everted lower lip with slight tremor, "
            "chin dimpling and orange-peel texture from mentalis contraction, "
            "realistic tear tracks on skin with proper light reflection"
        ),
        "negative": (
            "fake crying, dry eyes with artificial tears, normal colored nose, "
            "smooth chin without texture, perfectly shaped tears, "
            "symmetrical crying face, plastic sadness, stiff mouth"
        ),
        "preservation": (
            "maintain overall face shape and identity, preserve hair style, "
            "keep same clothing and background, maintain skin tone"
        ),
        "muscles": [
            "corrugator",
            "depressor_anguli_oris",
            "mentalis",
            "orbicularis_oris",
            "procerus",
        ],
        "instructions_zh": [
            "添加眉间川字纹（皱眉肌收缩）",
            "增加眼眶红肿感",
            "添加鼻尖发红效果",
            "修正嘴角下拉的自然度",
            "添加下巴橘皮纹理（颏肌收缩）",
        ],
    },
    "surprise": {
        "positive": (
            "frontalis muscle creating horizontal forehead wrinkles, "
            "raised eyebrows in natural arc shape, "
            "widened eyes showing more sclera above and below iris, "
            "dropped jaw with oval mouth shape, relaxed lips, "
            "natural asymmetry in expression"
        ),
        "negative": (
            "smooth forehead while surprised, perfect round eyes, "
            "too symmetrical surprise, stiff expression, "
            "unnatural eyebrow shape"
        ),
        "preservation": (
            "maintain overall face shape and identity, preserve hair style, "
            "keep same clothing and background, maintain skin tone"
        ),
        "muscles": [
            "frontalis",
            "levator_palpebrae",
        ],
        "instructions_zh": [
            "添加额头横纹（额肌收缩）",
            "调整眉毛弧度",
            "修正眼睛睁大的自然度",
            "调整嘴型为自然椭圆",
        ],
    },
    "anger": {
        "positive": (
            "strong corrugator and procerus muscle contraction creating deep glabellar lines, "
            "lowered and drawn-together eyebrows, "
            "tense upper eyelids with intense stare, narrowed eyes, "
            "flared nostrils from dilator naris, "
            "tightened lip line or teeth-baring snarl, "
            "tensed masseter muscle creating defined jaw line"
        ),
        "negative": (
            "relaxed face while angry, normal nostrils, soft jaw line, "
            "wide open eyes while angry, smooth forehead, "
            "stiff expression, fake anger"
        ),
        "preservation": (
            "maintain overall face shape and identity, preserve hair style, "
            "keep same clothing and background, maintain skin tone"
        ),
        "muscles": [
            "corrugator",
            "procerus",
            "dilator_naris",
            "masseter",
            "orbicularis_oris",
        ],
        "instructions_zh": [
            "加深眉间川字纹",
            "调整鼻翼外张效果",
            "增强咬肌紧张感",
            "修正眼睛瞪视效果",
        ],
    },
}


class ExpressionEnhancementAgent(BaseEnhancementAgent):
    """
    Agent specialized in fixing facial expression muscle issues.
    
    Handles:
    - Unnatural smiles (missing crow's feet, flat cheeks)
    - Fake crying (no eye redness, smooth chin)
    - Stiff surprise (smooth forehead)
    - Weak anger expression (no nostril flare)
    """
    
    agent_type = AgentType.EXPRESSION
    
    # Keywords that indicate expression-related issues
    EXPRESSION_KEYWORDS = [
        # Laugh related
        "laugh", "笑", "smile", "微笑", "grin", "teeth", "牙",
        "crow's feet", "鱼尾纹", "cheek", "脸颊", "苹果肌",
        # Crying related
        "cry", "哭", "tear", "泪", "sad", "悲", "frown", "皱眉", "sob",
        # Surprise related
        "surprise", "惊", "shock", "震惊", "wide eyes",
        # Anger related
        "anger", "怒", "fury", "glare", "瞪",
        # General expression issues
        "expression", "表情", "stiff", "僵硬", "unnatural", "不自然",
        "muscle", "肌肉", "asymmetr", "对称", "fake", "假",
    ]
    
    def __init__(self):
        self.llm_client = get_llm_client()
    
    async def can_handle(self, context: EnhancementContext) -> bool:
        """Check if there are expression-related issues to fix."""
        # Only applicable for portraits
        if context.scene_type.lower() not in ["portrait", "street", "other"]:
            return False
        
        # Check if expression mode is "correct"
        if context.expression_mode == "correct":
            return True
        
        # Check for expression-related signals
        relevant_signals = self._find_relevant_signals(context, self.EXPRESSION_KEYWORDS)
        return len(relevant_signals) > 0
    
    async def enhance(self, context: EnhancementContext) -> AgentResult:
        """Execute expression enhancement based on the provided prompt."""
        try:
            prompt = context.agent_prompt
            prompt_dict = self._get_prompt_dict(context)
            
            # Get expression type from context or prompt
            expression_type = context.expression_type
            if prompt and prompt.expression_type:
                expression_type = prompt.expression_type
            
            # Get correction template
            template = EXPRESSION_CORRECTION_TEMPLATES.get(expression_type)
            
            if prompt and prompt.correction_prompt:
                # Use the specific correction from router
                changes_made = prompt.specific_instructions.copy() if prompt.specific_instructions else []
                
                intensity_desc = {
                    "light": "轻微",
                    "medium": "中等",
                    "strong": "较强"
                }.get(prompt.intensity, "中等")
                
                expression_type_zh = {
                    "big_laugh": "大笑",
                    "crying": "大哭",
                    "surprise": "惊讶",
                    "anger": "愤怒",
                    "neutral": "中性",
                }.get(expression_type, expression_type)
                
                description = (
                    f"表情肌肉修正 ({intensity_desc}强度) - "
                    f"表情类型: {expression_type_zh}, "
                    f"模式: {'修正' if prompt.expression_mode == 'correct' else '保留'}"
                )
                
            elif template:
                # Use default template
                changes_made = template["instructions_zh"].copy()
                description = f"表情肌肉修正 - 使用{expression_type}默认模板"
                
            else:
                # No specific template, use generic
                changes_made = ["修正表情自然度"]
                description = "表情优化 - 使用通用设置"
            
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
                description="表情修正失败",
                error_message=str(e),
                prompt_used=self._get_prompt_dict(context),
            )
    
    @staticmethod
    def get_correction_template(expression_type: str) -> dict:
        """Get the correction template for an expression type."""
        return EXPRESSION_CORRECTION_TEMPLATES.get(expression_type, {})
    
    @staticmethod
    def get_preservation_prompt(expression_type: str) -> str:
        """Get the preservation prompt for an expression type."""
        template = EXPRESSION_CORRECTION_TEMPLATES.get(expression_type, {})
        return template.get("preservation", 
            "maintain overall face shape and identity, preserve hair style")
    
    @staticmethod
    def get_correction_prompt(expression_type: str) -> str:
        """Get the correction prompt for an expression type."""
        template = EXPRESSION_CORRECTION_TEMPLATES.get(expression_type, {})
        return template.get("positive", "")
    
    @staticmethod
    def get_negative_prompt(expression_type: str) -> str:
        """Get the negative prompt for an expression type."""
        template = EXPRESSION_CORRECTION_TEMPLATES.get(expression_type, {})
        return template.get("negative", "fake expression, stiff, unnatural")
