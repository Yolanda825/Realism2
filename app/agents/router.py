"""Router Agent - Decides which expert agents to invoke and generates specific prompts."""

from dataclasses import dataclass, field
from app.agents.base import (
    BaseEnhancementAgent,
    EnhancementContext,
    AgentType,
)
from app.agents.skin_agent import SkinEnhancementAgent
from app.agents.lighting_agent import LightingEnhancementAgent
from app.agents.texture_agent import TextureEnhancementAgent
from app.agents.geometry_agent import GeometryEnhancementAgent
from app.agents.color_agent import ColorEnhancementAgent
from app.agents.expression_agent import ExpressionEnhancementAgent, EXPRESSION_CORRECTION_TEMPLATES
from app.services.llm_client import get_llm_client


@dataclass
class AgentPrompt:
    """Structured prompt for an expert agent."""
    agent_type: AgentType
    positive_prompt: str  # What to add/enhance
    negative_prompt: str  # What to avoid/remove
    intensity: str  # "light", "medium", "strong"
    specific_instructions: list[str] = field(default_factory=list)
    target_areas: list[str] = field(default_factory=list)
    # New fields for preservation/correction
    preservation_prompt: str = ""  # What to preserve (identity, pose, etc.)
    correction_prompt: str = ""  # What to correct (expression muscles, etc.)
    denoising_strength: float = 0.2  # Suggested denoising strength
    expression_mode: str = "preserve"  # "preserve" or "correct"
    expression_type: str = "neutral"  # Type of expression detected
    expression_issues: list[str] = field(default_factory=list)  # Specific expression problems
    
    def to_dict(self) -> dict:
        return {
            "agent_type": self.agent_type.value,
            "positive_prompt": self.positive_prompt,
            "negative_prompt": self.negative_prompt,
            "intensity": self.intensity,
            "specific_instructions": self.specific_instructions,
            "target_areas": self.target_areas,
            "preservation_prompt": self.preservation_prompt,
            "correction_prompt": self.correction_prompt,
            "denoising_strength": self.denoising_strength,
            "expression_mode": self.expression_mode,
            "expression_type": self.expression_type,
            "expression_issues": self.expression_issues,
        }


@dataclass
class RoutingDecision:
    """Decision made by the router agent."""
    agents_to_invoke: list[AgentType]
    reasoning: str
    priority_order: list[AgentType]
    agent_prompts: dict[AgentType, AgentPrompt] = field(default_factory=dict)
    
    def get_prompt(self, agent_type: AgentType) -> AgentPrompt:
        """Get the prompt for a specific agent."""
        return self.agent_prompts.get(agent_type)


ROUTING_PROMPT = """你是一个图像增强路由专家。根据检测到的AI痕迹和表情分析结果，决定应该调用哪些专家Agent来修复图像，并为每个专家生成具体的修图指令。

图像类型: {scene_type}
AI生成可能性: {ai_likelihood:.0%}

检测到的问题：
{signals}

表情分析：
- 表情类型: {expression_type}
- 表情是否自然: {expression_natural}
- 表情模式: {expression_mode}
{expression_issues}

可用的专家Agent：
1. SKIN - 皮肤专家：处理皮肤过于光滑、缺乏毛孔、塑料感等问题
2. LIGHTING - 光线专家：处理光源不一致、阴影错误、高光异常等问题
3. TEXTURE - 纹理专家：处理纹理过于均匀、缺少细节、表面过于干净等问题
4. GEOMETRY - 几何专家：处理手指异常、比例失调、透视错误等问题
5. COLOR - 色彩专家：处理颜色过饱和、HDR感、色温不一致等问题
6. EXPRESSION - 表情专家：处理面部表情肌肉问题（大笑缺少鱼尾纹、大哭缺少眼眶红肿等）

【重要】表情处理策略：
- 如果 expression_mode 是 "preserve"（表情自然）：
  * 在所有agent的preservation_prompt中添加"preserve exact facial expression"
  * 在negative_prompt中添加"altered expression, different emotion"
  * 不调用EXPRESSION专家
  
- 如果 expression_mode 是 "correct"（表情不自然，需要修正）：
  * 调用EXPRESSION专家
  * 根据表情类型生成专业的肌肉修正prompt
  * preservation_prompt中保留身份但允许表情修正
  * 提高denoising_strength到0.25-0.35

你需要：
1. 选择需要调用的专家
2. 为每个选中的专家生成完整的提示词（包含新字段）

强度与denoising_strength对应：
- "light": denoising_strength 0.10-0.15（仅微调）
- "medium": denoising_strength 0.18-0.25（标准调整）
- "strong": denoising_strength 0.28-0.35（较强调整）
- 表情修正时，建议使用0.25-0.35

返回JSON格式：
{{
  "agents_to_invoke": ["EXPRESSION", "SKIN"],
  "reasoning": "选择理由的简短说明",
  "priority_order": ["EXPRESSION", "SKIN"],
  "agent_prompts": {{
    "EXPRESSION": {{
      "preservation_prompt": "maintain overall face shape and identity, preserve hair style",
      "correction_prompt": "Duchenne smile with crow's feet at eye corners, raised apple cheeks, deepened nasolabial folds",
      "positive_prompt": "natural smile with proper muscle engagement, eye squint from orbicularis oculi",
      "negative_prompt": "fake smile, eyes wide open while laughing, flat cheeks, stiff expression",
      "intensity": "medium",
      "denoising_strength": 0.28,
      "expression_mode": "correct",
      "expression_type": "big_laugh",
      "expression_issues": ["眼睛没有眯起", "缺少鱼尾纹", "苹果肌不明显"],
      "specific_instructions": ["添加眼角鱼尾纹", "增强颧骨苹果肌", "加深鼻唇沟"],
      "target_areas": ["eyes", "cheeks", "mouth"]
    }},
    "SKIN": {{
      "preservation_prompt": "preserve corrected facial expression, maintain identity",
      "correction_prompt": "",
      "positive_prompt": "add subtle skin pores, natural skin texture",
      "negative_prompt": "plastic skin, airbrushed, altered expression",
      "intensity": "light",
      "denoising_strength": 0.15,
      "expression_mode": "preserve",
      "expression_type": "big_laugh",
      "expression_issues": [],
      "specific_instructions": ["添加轻微毛孔纹理"],
      "target_areas": ["face"]
    }}
  }}
}}

注意：
- 只为选中的专家生成提示词
- 提示词要具体，针对检测到的具体问题
- preservation_prompt 必须包含身份保留约束
- expression_mode为"preserve"时，所有agent都要在negative中包含"altered expression"
- expression_mode为"correct"时，EXPRESSION专家优先执行
- specific_instructions 用中文描述具体操作
- positive_prompt 和 negative_prompt 用英文

只返回JSON，不要其他内容。"""


class RouterAgent:
    """
    Router Agent that decides which expert agents to invoke
    and generates specific prompts for each.
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
        
        # Initialize all available expert agents
        self.available_agents: dict[AgentType, BaseEnhancementAgent] = {
            AgentType.SKIN: SkinEnhancementAgent(),
            AgentType.LIGHTING: LightingEnhancementAgent(),
            AgentType.TEXTURE: TextureEnhancementAgent(),
            AgentType.GEOMETRY: GeometryEnhancementAgent(),
            AgentType.COLOR: ColorEnhancementAgent(),
            AgentType.EXPRESSION: ExpressionEnhancementAgent(),
        }
    
    async def route(self, context: EnhancementContext) -> RoutingDecision:
        """
        Decide which expert agents to invoke and generate prompts.
        
        Args:
            context: The enhancement context with detected issues
            
        Returns:
            RoutingDecision with agents, order, and specific prompts
        """
        if not context.fake_signals:
            return RoutingDecision(
                agents_to_invoke=[],
                reasoning="未检测到AI痕迹，无需调用专家Agent",
                priority_order=[],
                agent_prompts={},
            )
        
        # Format signals for prompt
        signals_text = "\n".join([
            f"- [{s.severity.value.upper()}] {s.signal}"
            for s in context.fake_signals
        ])
        
        # Format expression issues
        expression_issues_text = ""
        if context.expression_issues:
            expression_issues_text = "表情问题：\n" + "\n".join([
                f"  - {issue}" for issue in context.expression_issues
            ])
        
        # Determine expression mode
        expression_mode = context.expression_mode if hasattr(context, 'expression_mode') else "preserve"
        expression_type = context.expression_type if hasattr(context, 'expression_type') else "neutral"
        expression_natural = context.expression_natural if hasattr(context, 'expression_natural') else True
        
        prompt = ROUTING_PROMPT.format(
            scene_type=context.scene_type,
            ai_likelihood=context.ai_likelihood,
            signals=signals_text,
            expression_type=expression_type,
            expression_natural="是" if expression_natural else "否",
            expression_mode=expression_mode,
            expression_issues=expression_issues_text,
        )
        
        try:
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )
            
            result = await self.llm_client.parse_json_response(response)
            
            # Parse agent types
            agents_to_invoke = []
            for agent_name in result.get("agents_to_invoke", []):
                try:
                    agent_type = AgentType(agent_name.lower())
                    if agent_type in self.available_agents:
                        agents_to_invoke.append(agent_type)
                except ValueError:
                    continue
            
            # Parse priority order
            priority_order = []
            for agent_name in result.get("priority_order", []):
                try:
                    agent_type = AgentType(agent_name.lower())
                    if agent_type in agents_to_invoke:
                        priority_order.append(agent_type)
                except ValueError:
                    continue
            
            # Ensure all invoked agents are in priority order
            for agent_type in agents_to_invoke:
                if agent_type not in priority_order:
                    priority_order.append(agent_type)
            
            # Parse agent prompts
            agent_prompts = {}
            raw_prompts = result.get("agent_prompts", {})
            
            for agent_name, prompt_data in raw_prompts.items():
                try:
                    agent_type = AgentType(agent_name.lower())
                    if agent_type in agents_to_invoke:
                        agent_prompts[agent_type] = AgentPrompt(
                            agent_type=agent_type,
                            positive_prompt=prompt_data.get("positive_prompt", ""),
                            negative_prompt=prompt_data.get("negative_prompt", ""),
                            intensity=prompt_data.get("intensity", "medium"),
                            specific_instructions=prompt_data.get("specific_instructions", []),
                            target_areas=prompt_data.get("target_areas", []),
                            # New fields
                            preservation_prompt=prompt_data.get("preservation_prompt", ""),
                            correction_prompt=prompt_data.get("correction_prompt", ""),
                            denoising_strength=prompt_data.get("denoising_strength", 0.2),
                            expression_mode=prompt_data.get("expression_mode", expression_mode),
                            expression_type=prompt_data.get("expression_type", expression_type),
                            expression_issues=prompt_data.get("expression_issues", []),
                        )
                except (ValueError, KeyError):
                    continue
            
            # Generate default prompts for agents without specific prompts
            for agent_type in agents_to_invoke:
                if agent_type not in agent_prompts:
                    agent_prompts[agent_type] = self._generate_default_prompt(
                        agent_type, context
                    )
            
            return RoutingDecision(
                agents_to_invoke=agents_to_invoke,
                reasoning=result.get("reasoning", ""),
                priority_order=priority_order,
                agent_prompts=agent_prompts,
            )
            
        except Exception as e:
            # Fallback: use heuristic-based routing
            return await self._fallback_routing(context)
    
    def _generate_default_prompt(
        self,
        agent_type: AgentType,
        context: EnhancementContext,
    ) -> AgentPrompt:
        """Generate a default prompt for an agent type."""
        # Get expression context
        expression_mode = getattr(context, 'expression_mode', 'preserve')
        expression_type = getattr(context, 'expression_type', 'neutral')
        expression_issues = getattr(context, 'expression_issues', [])
        
        # Base preservation prompt
        base_preservation = "maintain overall face shape and identity, preserve hair style"
        if expression_mode == "preserve":
            base_preservation += ", preserve exact facial expression"
        
        # Base negative addition for expression preservation
        expression_negative = ""
        if expression_mode == "preserve":
            expression_negative = ", altered expression, different emotion, changed pose"
        
        defaults = {
            AgentType.SKIN: AgentPrompt(
                agent_type=AgentType.SKIN,
                positive_prompt="natural skin texture, visible pores, subtle imperfections, realistic skin detail",
                negative_prompt="plastic skin, airbrushed, overly smooth, waxy, artificial" + expression_negative,
                intensity="medium",
                specific_instructions=["添加自然的皮肤纹理", "增加毛孔细节"],
                target_areas=["face", "skin areas"],
                preservation_prompt=base_preservation,
                denoising_strength=0.18,
                expression_mode=expression_mode,
                expression_type=expression_type,
            ),
            AgentType.LIGHTING: AgentPrompt(
                agent_type=AgentType.LIGHTING,
                positive_prompt="natural lighting, consistent shadows, soft light falloff, realistic highlights",
                negative_prompt="harsh lighting, inconsistent shadows, artificial highlights, flat lighting" + expression_negative,
                intensity="medium",
                specific_instructions=["统一光源方向", "柔化阴影边缘"],
                target_areas=["global"],
                preservation_prompt=base_preservation,
                denoising_strength=0.18,
                expression_mode=expression_mode,
                expression_type=expression_type,
            ),
            AgentType.TEXTURE: AgentPrompt(
                agent_type=AgentType.TEXTURE,
                positive_prompt="detailed texture, natural surface variation, micro details, material authenticity",
                negative_prompt="uniform texture, repetitive patterns, overly clean surfaces, artificial smoothness" + expression_negative,
                intensity="medium",
                specific_instructions=["增加表面细节", "添加自然磨损感"],
                target_areas=["surfaces", "materials"],
                preservation_prompt=base_preservation,
                denoising_strength=0.18,
                expression_mode=expression_mode,
                expression_type=expression_type,
            ),
            AgentType.GEOMETRY: AgentPrompt(
                agent_type=AgentType.GEOMETRY,
                positive_prompt="correct anatomy, natural proportions, proper perspective, realistic pose",
                negative_prompt="distorted anatomy, extra fingers, wrong proportions, impossible geometry" + expression_negative,
                intensity="medium",
                specific_instructions=["修正解剖学错误", "调整比例"],
                target_areas=["body", "hands", "face"],
                preservation_prompt=base_preservation,
                denoising_strength=0.20,
                expression_mode=expression_mode,
                expression_type=expression_type,
            ),
            AgentType.COLOR: AgentPrompt(
                agent_type=AgentType.COLOR,
                positive_prompt="natural colors, balanced saturation, consistent color temperature, realistic tones",
                negative_prompt="oversaturated, HDR look, artificial colors, inconsistent temperature" + expression_negative,
                intensity="medium",
                specific_instructions=["降低过度饱和", "统一色温"],
                target_areas=["global"],
                preservation_prompt=base_preservation,
                denoising_strength=0.15,
                expression_mode=expression_mode,
                expression_type=expression_type,
            ),
            AgentType.EXPRESSION: self._generate_expression_prompt(context),
        }
        return defaults.get(agent_type, AgentPrompt(
            agent_type=agent_type,
            positive_prompt="realistic, natural",
            negative_prompt="artificial, fake" + expression_negative,
            intensity="medium",
            specific_instructions=[],
            target_areas=[],
            preservation_prompt=base_preservation,
            denoising_strength=0.18,
            expression_mode=expression_mode,
            expression_type=expression_type,
        ))
    
    def _generate_expression_prompt(self, context: EnhancementContext) -> AgentPrompt:
        """Generate a prompt specifically for expression correction."""
        expression_type = getattr(context, 'expression_type', 'neutral')
        expression_issues = getattr(context, 'expression_issues', [])
        
        # Get template from ExpressionAgent
        template = EXPRESSION_CORRECTION_TEMPLATES.get(expression_type, {})
        
        if template:
            return AgentPrompt(
                agent_type=AgentType.EXPRESSION,
                positive_prompt=template.get("positive", "natural expression"),
                negative_prompt=template.get("negative", "fake expression, stiff"),
                intensity="medium",
                specific_instructions=template.get("instructions_zh", ["修正表情自然度"]),
                target_areas=["face", "eyes", "mouth"],
                preservation_prompt=template.get("preservation", "maintain face shape and identity"),
                correction_prompt=template.get("positive", ""),
                denoising_strength=0.28,
                expression_mode="correct",
                expression_type=expression_type,
                expression_issues=expression_issues,
            )
        else:
            return AgentPrompt(
                agent_type=AgentType.EXPRESSION,
                positive_prompt="natural facial expression with proper muscle engagement",
                negative_prompt="fake expression, stiff face, unnatural smile",
                intensity="medium",
                specific_instructions=["修正表情肌肉走向"],
                target_areas=["face"],
                preservation_prompt="maintain face shape and identity",
                correction_prompt="",
                denoising_strength=0.25,
                expression_mode="correct",
                expression_type=expression_type,
                expression_issues=expression_issues,
            )
    
    async def _fallback_routing(self, context: EnhancementContext) -> RoutingDecision:
        """
        Fallback routing using heuristics when LLM fails.
        """
        agents_to_invoke = []
        
        for agent_type, agent in self.available_agents.items():
            if await agent.can_handle(context):
                agents_to_invoke.append(agent_type)
        
        # Default priority order - EXPRESSION first if correction needed
        expression_mode = getattr(context, 'expression_mode', 'preserve')
        
        if expression_mode == "correct":
            priority_order = [
                AgentType.EXPRESSION,  # Expression correction first
                AgentType.GEOMETRY,
                AgentType.SKIN,
                AgentType.LIGHTING,
                AgentType.TEXTURE,
                AgentType.COLOR,
            ]
        else:
            priority_order = [
                AgentType.GEOMETRY,
                AgentType.SKIN,
                AgentType.LIGHTING,
                AgentType.TEXTURE,
                AgentType.COLOR,
            ]
        
        priority_order = [a for a in priority_order if a in agents_to_invoke]
        
        # Generate default prompts
        agent_prompts = {
            agent_type: self._generate_default_prompt(agent_type, context)
            for agent_type in agents_to_invoke
        }
        
        return RoutingDecision(
            agents_to_invoke=agents_to_invoke,
            reasoning="基于规则的路由决策（LLM调用失败时的后备方案）",
            priority_order=priority_order,
            agent_prompts=agent_prompts,
        )
    
    def get_agent(self, agent_type: AgentType) -> BaseEnhancementAgent:
        """Get an agent instance by type."""
        return self.available_agents.get(agent_type)
