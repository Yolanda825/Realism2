"""Stage 2: Fake Signal Detector - Identifies AI-generated artifacts in images."""

from dataclasses import dataclass, field
from app.models.schemas import FakeSignal, Severity, DimensionSignals
from app.services.llm_client import get_llm_client

SYSTEM_PROMPT = """You are an expert at detecting AI-generated image artifacts.

IMPORTANT RULES:
1. Never describe or infer the identity of any person in the image.
2. Focus only on technical artifacts and realism issues.
3. Be specific about the location and nature of detected issues.
4. Do not mention names or identify specific individuals.

You must return ONLY valid JSON, no other text."""


# Expression analysis result
@dataclass
class ExpressionAnalysis:
    """Result of facial expression analysis."""
    expression_type: str = "neutral"  # neutral, big_laugh, crying, surprise, anger, other
    expression_natural: bool = True
    expression_issues: list[str] = field(default_factory=list)
    muscle_problems: list[str] = field(default_factory=list)
    correction_needed: bool = False


# Expression detection prompt
EXPRESSION_DETECTION_PROMPT = """分析这张图像中的面部表情（如果有人脸的话）。

1. 表情类型识别：
   - neutral (中性/平静)
   - big_laugh (大笑/开心大笑)
   - crying (大哭/悲伤流泪)
   - surprise (惊讶)
   - anger (愤怒)
   - other (其他表情)

2. 表情自然度问题检测（针对AI生成的常见问题）：

【大笑表情常见问题】
- 眼睛没有眯起（真实大笑时眼轮匝肌会收缩）
- 缺少鱼尾纹（crow's feet）
- 颧骨处苹果肌不明显（zygomatic major未激活）
- 鼻唇沟过浅或方向错误
- 嘴型僵硬，牙齿暴露不自然
- 下巴缺少颏肌收缩纹理

【大哭表情常见问题】
- 眉间缺少川字纹（皱眉肌未收缩）
- 眼眶不红，泪腺区域没有肿胀感
- 鼻尖没有发红
- 嘴角下拉不自然
- 下巴缺少"橘皮"纹理（颏肌收缩）

【惊讶表情常见问题】
- 额头缺少横纹（额肌未收缩）
- 眼睛睁大但太过完美圆形
- 嘴型过于规则

【愤怒表情常见问题】
- 眉间皱纹不够深
- 鼻翼没有外张
- 咬肌不够紧张

返回JSON格式：
{
  "has_face": true/false,
  "expression_type": "neutral" | "big_laugh" | "crying" | "surprise" | "anger" | "other",
  "expression_natural": true/false,
  "expression_issues": [
    "具体问题描述1",
    "具体问题描述2"
  ],
  "muscle_problems": [
    "orbicularis_oculi_missing",
    "zygomatic_major_weak",
    "corrugator_missing",
    "frontalis_missing",
    "mentalis_missing"
  ]
}

如果图中没有人脸，返回 has_face: false 和 expression_type: "neutral"。
只返回JSON，不要其他内容。"""

DETECTION_PROMPT = """Analyze this image for signs of AI generation or digital manipulation.

Focus on detecting these common AI artifacts by dimension:

【SKIN - 皮肤】
- Unnaturally smooth or plastic-looking skin
- Missing pores and skin texture details
- Airbrushed or overly perfect complexion
- Inconsistent skin texture between regions

【LIGHTING - 光线】
- Inconsistent light direction between subjects
- Missing or incorrect shadows
- Unnatural highlights or reflections
- Physically impossible light behavior

【TEXTURE - 纹理】
- Over-uniform textures on surfaces
- Missing micro-variations in materials
- Too-perfect gradients
- Repetitive texture patterns

【GEOMETRY - 几何（包括表情）】
- Extra or missing fingers
- Distorted anatomy or proportions
- Impossible poses or perspectives
- Facial asymmetry (if portrait)
- Expression issues: unnatural smile, missing crow's feet, etc.

【COLOR - 色彩】
- Oversaturated or unnatural colors
- HDR-like appearance
- Inconsistent color temperature
- Unnatural color transitions

For each issue found, rate its severity:
- "low": Minor issue, barely noticeable
- "medium": Noticeable upon inspection
- "high": Obviously artificial, immediately visible

Return your analysis as JSON with dimension-tagged signals:
{
  "fake_signals": [
    {
      "signal": "<description of the specific issue>",
      "severity": "low" | "medium" | "high",
      "dimension": "skin" | "lighting" | "texture" | "geometry" | "color"
    }
  ]
}

If no issues are detected, return an empty array.
Return ONLY the JSON object, no explanations or markdown."""


class FakeSignalDetector:
    """Detects AI-generated artifacts and realism issues in images."""

    def __init__(self):
        """Initialize the fake signal detector."""
        self.llm_client = get_llm_client()

    async def detect(self, image_base64: str) -> list[FakeSignal]:
        """
        Detect fake signals (AI artifacts) in an image.

        Args:
            image_base64: Base64-encoded image data

        Returns:
            List of detected FakeSignal objects with dimension tags
        """
        response = await self.llm_client.chat_completion_with_image(
            prompt=DETECTION_PROMPT,
            image_base64=image_base64,
            system_prompt=SYSTEM_PROMPT,
            temperature=0,
            max_tokens=2048,
        )

        # Parse the JSON response
        result = await self.llm_client.parse_json_response(response)

        signals = []
        for item in result.get("fake_signals", []):
            severity_str = item.get("severity", "low").lower()
            try:
                severity = Severity(severity_str)
            except ValueError:
                severity = Severity.LOW

            dimension = item.get("dimension", "general").lower()
            valid_dimensions = ["skin", "lighting", "texture", "geometry", "color"]
            if dimension not in valid_dimensions:
                dimension = "general"

            signals.append(FakeSignal(
                signal=item.get("signal", ""),
                severity=severity,
                dimension=dimension,
            ))

        return signals

    def categorize_by_dimension(self, signals: list[FakeSignal]) -> DimensionSignals:
        """
        Categorize fake signals by dimension.

        Args:
            signals: List of fake signals

        Returns:
            DimensionSignals with signals grouped by dimension
        """
        result = DimensionSignals()
        for signal in signals:
            if signal.dimension == "skin":
                result.skin.append(signal)
            elif signal.dimension == "lighting":
                result.lighting.append(signal)
            elif signal.dimension == "texture":
                result.texture.append(signal)
            elif signal.dimension == "geometry":
                result.geometry.append(signal)
            elif signal.dimension == "color":
                result.color.append(signal)
            else:
                result.general.append(signal)
        return result

    async def detect_expression(self, image_base64: str) -> ExpressionAnalysis:
        """
        Analyze facial expression in an image.
        
        Args:
            image_base64: Base64-encoded image data
            
        Returns:
            ExpressionAnalysis with expression type and issues
        """
        try:
            response = await self.llm_client.chat_completion_with_image(
                prompt=EXPRESSION_DETECTION_PROMPT,
                image_base64=image_base64,
                system_prompt=SYSTEM_PROMPT,
                temperature=0,
                max_tokens=1024,
            )
            
            result = await self.llm_client.parse_json_response(response)
            
            # Check if there's a face
            has_face = result.get("has_face", False)
            if not has_face:
                return ExpressionAnalysis(
                    expression_type="neutral",
                    expression_natural=True,
                    expression_issues=[],
                    muscle_problems=[],
                    correction_needed=False,
                )
            
            expression_type = result.get("expression_type", "neutral")
            expression_natural = result.get("expression_natural", True)
            expression_issues = result.get("expression_issues", [])
            muscle_problems = result.get("muscle_problems", [])
            
            # Determine if correction is needed
            # Correction is needed for intense expressions with issues
            intense_expressions = ["big_laugh", "crying", "surprise", "anger"]
            correction_needed = (
                expression_type in intense_expressions
                and not expression_natural
                and len(expression_issues) > 0
            )
            
            return ExpressionAnalysis(
                expression_type=expression_type,
                expression_natural=expression_natural,
                expression_issues=expression_issues,
                muscle_problems=muscle_problems,
                correction_needed=correction_needed,
            )
            
        except Exception as e:
            # Return default neutral analysis on error
            return ExpressionAnalysis(
                expression_type="neutral",
                expression_natural=True,
                expression_issues=[],
                muscle_problems=[],
                correction_needed=False,
            )
    
    async def detect_with_expression(
        self, image_base64: str
    ) -> tuple[list[FakeSignal], ExpressionAnalysis]:
        """
        Detect both fake signals and expression issues.
        
        Args:
            image_base64: Base64-encoded image data
            
        Returns:
            Tuple of (fake_signals, expression_analysis)
        """
        # Run both detections
        signals = await self.detect(image_base64)
        expression = await self.detect_expression(image_base64)
        
        # If expression has issues, add them to fake signals
        if expression.correction_needed:
            for issue in expression.expression_issues:
                signals.append(FakeSignal(
                    signal=f"[表情问题] {issue}",
                    severity=Severity.MEDIUM,
                ))
        
        return signals, expression
