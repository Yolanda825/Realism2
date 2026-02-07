"""Image model service for executing image enhancement."""

import json
import asyncio
import base64
import time
import uuid
from typing import Optional, TYPE_CHECKING
import httpx

from app.config import get_settings
from app.models.schemas import ModelRouting, EnhancementResult
from app.services.llm_client import get_llm_client

# Try to import MHC SDK
try:
    from lib.ai import api as mhc_api
    MHC_SDK_AVAILABLE = True
except ImportError:
    MHC_SDK_AVAILABLE = False
    mhc_api = None

if TYPE_CHECKING:
    from app.agents.router import AgentPrompt


class ImageModelClient:
    """Client for interacting with image enhancement models."""

    def __init__(self):
        """Initialize the image model client."""
        settings = get_settings()
        self.endpoint = settings.image_model_endpoint
        self.llm_base_url = settings.llm_base_url
        self.llm_api_key = settings.llm_api_key
        self.client = httpx.AsyncClient(timeout=120.0)
        
        # MHC API configuration
        self.mhc_app = settings.mhc_app
        self.mhc_biz = settings.mhc_biz
        self.mhc_region = settings.mhc_region
        self.mhc_env = settings.mhc_env
        self.mhc_api_path = settings.mhc_api_path
        self.mhc_nano_token = getattr(settings, "mhc_nano_token", "") or ""

        # Initialize MHC client if SDK is available
        self.mhc_client = None
        if MHC_SDK_AVAILABLE and self.mhc_app and self.mhc_biz:
            try:
                self.mhc_client = mhc_api.AiApi(
                    self.mhc_app,
                    self.mhc_biz,
                    self.mhc_region,
                    env=self.mhc_env
                )
            except Exception as e:
                print(f"Warning: Failed to initialize MHC client: {e}")
                self.mhc_client = None
    
    def compose_prompt_from_agent(self, agent_prompt: "AgentPrompt") -> tuple[str, str, float]:
        """
        Compose the final prompt from an AgentPrompt with preservation/correction logic.
        
        Args:
            agent_prompt: The AgentPrompt object with all prompt components
            
        Returns:
            Tuple of (positive_prompt, negative_prompt, denoising_strength)
        """
        parts = []
        
        # 1. Add preservation prompt first (identity, pose, etc.)
        if agent_prompt.preservation_prompt:
            parts.append(agent_prompt.preservation_prompt)
        
        # 2. Add correction prompt if in correction mode
        if agent_prompt.expression_mode == "correct" and agent_prompt.correction_prompt:
            parts.append(agent_prompt.correction_prompt)
        
        # 3. Add the main positive prompt
        if agent_prompt.positive_prompt:
            parts.append(agent_prompt.positive_prompt)
        
        # Combine positive prompt
        final_positive = ", ".join(filter(None, parts))
        
        # Build negative prompt
        negative_parts = []
        if agent_prompt.negative_prompt:
            negative_parts.append(agent_prompt.negative_prompt)
        
        # Add expression preservation to negative if in preserve mode
        if agent_prompt.expression_mode == "preserve":
            negative_parts.append("altered expression, different emotion, changed facial expression")
        
        final_negative = ", ".join(filter(None, negative_parts))
        
        return final_positive, final_negative, agent_prompt.denoising_strength
    
    def compose_prompt_for_model_routing(
        self,
        model_routing: ModelRouting,
        preservation_prompt: str = "",
        correction_prompt: str = "",
        expression_mode: str = "preserve",
    ) -> tuple[str, str]:
        """
        Compose the final prompt for ModelRouting with optional preservation/correction.
        
        Args:
            model_routing: The ModelRouting object
            preservation_prompt: Optional preservation constraints
            correction_prompt: Optional correction guidance
            expression_mode: "preserve" or "correct"
            
        Returns:
            Tuple of (positive_prompt, negative_prompt)
        """
        parts = []
        
        # 1. Preservation first
        if preservation_prompt:
            parts.append(preservation_prompt)
        
        # 2. Correction if needed
        if expression_mode == "correct" and correction_prompt:
            parts.append(correction_prompt)
        
        # 3. Original prompt
        if model_routing.prompt:
            parts.append(model_routing.prompt)
        
        final_positive = ", ".join(filter(None, parts))
        
        # Negative prompt
        negative_parts = []
        if model_routing.negative_prompt:
            negative_parts.append(model_routing.negative_prompt)
        
        if expression_mode == "preserve":
            negative_parts.append("altered expression, different emotion")
        
        final_negative = ", ".join(filter(None, negative_parts))
        
        return final_positive, final_negative

    async def execute_enhancement(
        self,
        image_base64: str,
        model_routing: ModelRouting,
        preservation_prompt: str = "",
        correction_prompt: str = "",
        expression_mode: str = "preserve",
    ) -> EnhancementResult:
        """
        Execute image enhancement using the specified model.

        Supports multiple backends:
        1. Direct image model endpoint (if configured)
        2. LLM-based image editing (using vision model)
        3. Mock mode for testing

        Args:
            image_base64: Base64-encoded source image
            model_routing: Model routing with prompt and parameters
            preservation_prompt: Optional preservation constraints (identity, expression)
            correction_prompt: Optional correction guidance (for expression correction)
            expression_mode: "preserve" or "correct"

        Returns:
            EnhancementResult with enhanced image or error
        """
        # Compose prompts with preservation/correction
        final_positive, final_negative = self.compose_prompt_for_model_routing(
            model_routing,
            preservation_prompt,
            correction_prompt,
            expression_mode,
        )
        
        # Create modified model routing with composed prompts
        composed_routing = ModelRouting(
            model_name=model_routing.model_name,
            model_type=model_routing.model_type,
            prompt=final_positive,
            negative_prompt=final_negative,
            parameters=model_routing.parameters,
            reasoning=model_routing.reasoning,
        )
        
        # Try different enhancement methods in order
        
        # Method 1: Use MHC API if available
        if self.mhc_client:
            result = await self._call_mhc_api(image_base64, composed_routing)
            if result.success:
                return result
        
        # Method 2: Use dedicated image model endpoint if configured (SD API style)
        if self.endpoint:
            result = await self._call_image_endpoint(image_base64, composed_routing)
            if result.success:
                return result

        # Method 3: Use LLM with image editing capability
        result = await self._call_llm_image_edit(image_base64, composed_routing)
        if result.success:
            return result

        # Method 4: Return original with note (fallback)
        return EnhancementResult(
            success=True,
            enhanced_image_base64=image_base64,  # Return original
            error_message="图像增强模型未配置，返回原图。请配置 MHC API 或 IMAGE_MODEL_ENDPOINT 以启用增强功能。",
        )
    
    async def execute_with_agent_prompt(
        self,
        image_base64: str,
        agent_prompt: "AgentPrompt",
    ) -> EnhancementResult:
        """
        Execute enhancement using an AgentPrompt directly.
        
        This method composes the prompt from the AgentPrompt's preservation,
        correction, and positive prompts based on the expression mode.
        
        Args:
            image_base64: Base64-encoded source image
            agent_prompt: AgentPrompt with all prompt components
            
        Returns:
            EnhancementResult with enhanced image or error
        """
        # Compose prompts
        final_positive, final_negative, denoising = self.compose_prompt_from_agent(agent_prompt)
        
        # Create model routing
        model_routing = ModelRouting(
            model_name="img2img-realism",
            model_type="img2img",
            prompt=final_positive,
            negative_prompt=final_negative,
            parameters={
                "denoising_strength": denoising,
                "steps": 25 if agent_prompt.expression_mode == "correct" else 20,
                "cfg_scale": 7.0,
                "sampler": "DPM++ 2M Karras",
                "seed": -1,
            },
            reasoning=f"Agent: {agent_prompt.agent_type.value}, Mode: {agent_prompt.expression_mode}",
        )
        
        # Try enhancement methods
        
        # Method 1: MHC API
        if self.mhc_client:
            result = await self._call_mhc_api(image_base64, model_routing)
            if result.success:
                return result
        
        # Method 2: SD API
        if self.endpoint:
            result = await self._call_image_endpoint(image_base64, model_routing)
            if result.success:
                return result
        
        # Method 3: LLM
        result = await self._call_llm_image_edit(image_base64, model_routing)
        if result.success:
            return result
        
        return EnhancementResult(
            success=True,
            enhanced_image_base64=image_base64,
            error_message="图像增强模型未配置，返回原图。",
        )

    async def _call_mhc_api(
        self,
        image_base64: str,
        model_routing: ModelRouting,
    ) -> EnhancementResult:
        """
        Call MHC image-to-image API（与 test_minimal.py 一致：runAsync + queryResult）.

        使用 lib.ai.api.AiApi.runAsync 提交异步任务，再用 queryResult 轮询结果；
        参数采用外采改图接口：app_scene=go, path_scene=imgEdit, model=gemini-3-pro-image-preview 等。
        """
        if not self.mhc_client:
            return EnhancementResult(
                success=False,
                enhanced_image_base64=None,
                error_message="MHC API 客户端未初始化",
            )
        if not self.mhc_nano_token:
            return EnhancementResult(
                success=False,
                enhanced_image_base64=None,
                error_message="未配置 MHC_NANO_TOKEN（外采改图权限 Token，联系元建获取）",
            )

        try:
            # 与 test_minimal 一致的 parameter 结构（外采 image-to-image 接口）
            params = {
                "parameter": {
                    "app_scene": "go",
                    "aspect_ratio": "1:1",
                    "expire_queue_time": 1200,
                    "model": "gemini-3-pro-image-preview",
                    "path_scene": "imgEdit",
                    "prompt": model_routing.prompt or "",
                    "resolution": "2K",
                    "rsp_media_type": "url",
                    "token": self.mhc_nano_token,
                    "trace_id": str(uuid.uuid4()),
                }
            }

            # 输入图：与 test_minimal 一致 [{"url": image_url}]
            if not image_base64.startswith("data:"):
                image_url = f"data:image/jpeg;base64,{image_base64}"
            else:
                image_url = image_base64

            loop = asyncio.get_event_loop()
            task_result = await loop.run_in_executor(
                None,
                lambda: self.mhc_client.runAsync(
                    [{"url": image_url}],
                    params,
                    self.mhc_api_path,
                    "mtlab",
                ),
            )

            # 与 test_minimal 一致：从 data.result 取 task_id，再 queryResult
            data = task_result.get("data") or {}
            result_inner = data.get("result") or {}
            task_id = result_inner.get("id") or task_result.get("msg_id")
            if not task_id:
                return EnhancementResult(
                    success=False,
                    enhanced_image_base64=None,
                    error_message=f"MHC API 任务提交失败，无 task_id: {json.dumps(task_result)[:500]}",
                )

            # 轮询结果（与 test_minimal 一致：queryResult 返回 { is_finished, result }，result 为完整响应）
            max_attempts = 30
            for _ in range(max_attempts):
                await asyncio.sleep(2)
                raw = await loop.run_in_executor(
                    None,
                    lambda tid=task_id: self.mhc_client.queryResult(tid),
                )
                if not isinstance(raw, dict):
                    continue
                # queryResult 返回 {"is_finished": bool, "result": taskResult}
                task_result = raw.get("result") or raw
                data = task_result.get("data") if isinstance(task_result, dict) else {}
                status = data.get("status")

                if status == 10 or status == 2 or status == 20:
                    output = data.get("output") or data.get("result") or data
                    enhanced_image = None
                    if isinstance(output, dict):
                        enhanced_image = (
                            output.get("image_base64")
                            or output.get("base64")
                            or output.get("image")
                            or output.get("result_image")
                        )
                        if not enhanced_image and output.get("url"):
                            enhanced_image = await self._download_image_as_base64(output["url"])
                    elif isinstance(output, str):
                        if output.startswith("http"):
                            enhanced_image = await self._download_image_as_base64(output)
                        else:
                            enhanced_image = output
                    if enhanced_image:
                        if "base64," in str(enhanced_image):
                            enhanced_image = str(enhanced_image).split("base64,")[-1]
                        return EnhancementResult(
                            success=True,
                            enhanced_image_base64=enhanced_image,
                            error_message=None,
                        )
                    return EnhancementResult(
                        success=False,
                        enhanced_image_base64=None,
                        error_message=f"MHC API 返回格式未知: {json.dumps(raw)[:500]}",
                    )
                if status in ("failed", "error") or (isinstance(status, int) and status not in (0, 1, 9)):
                    err = data.get("error") or data.get("message") or "未知错误"
                    return EnhancementResult(
                        success=False,
                        enhanced_image_base64=None,
                        error_message=f"MHC API 任务失败: {err}",
                    )

            return EnhancementResult(
                success=False,
                enhanced_image_base64=None,
                error_message="MHC API 任务超时（60秒）",
            )
        except Exception as e:
            return EnhancementResult(
                success=False,
                enhanced_image_base64=None,
                error_message=f"MHC API 调用失败: {str(e)}",
            )
    
    async def _download_image_as_base64(self, url: str) -> Optional[str]:
        """Download an image from URL and convert to base64."""
        try:
            response = await self.client.get(url, timeout=30.0)
            response.raise_for_status()
            return base64.b64encode(response.content).decode("utf-8")
        except Exception:
            return None

    async def _call_image_endpoint(
        self,
        image_base64: str,
        model_routing: ModelRouting,
    ) -> EnhancementResult:
        """Call dedicated image enhancement endpoint (SD API style)."""
        try:
            payload = {
                "init_images": [f"data:image/jpeg;base64,{image_base64}"],
                "prompt": model_routing.prompt,
                "negative_prompt": model_routing.negative_prompt,
                "denoising_strength": model_routing.parameters.get("denoising_strength", 0.25),
                "steps": model_routing.parameters.get("steps", 20),
                "cfg_scale": model_routing.parameters.get("cfg_scale", 7.0),
                "sampler_name": model_routing.parameters.get("sampler", "DPM++ 2M Karras"),
                "seed": model_routing.parameters.get("seed", -1),
            }

            response = await self.client.post(
                f"{self.endpoint}/sdapi/v1/img2img",
                json=payload,
                timeout=180.0,
            )
            response.raise_for_status()
            result = response.json()

            if "images" in result and result["images"]:
                return EnhancementResult(
                    success=True,
                    enhanced_image_base64=result["images"][0],
                    error_message=None,
                )
            else:
                return EnhancementResult(
                    success=False,
                    enhanced_image_base64=None,
                    error_message="图像增强API未返回结果",
                )

        except httpx.TimeoutException:
            return EnhancementResult(
                success=False,
                enhanced_image_base64=None,
                error_message="图像增强请求超时",
            )
        except Exception as e:
            return EnhancementResult(
                success=False,
                enhanced_image_base64=None,
                error_message=f"图像增强失败: {str(e)}",
            )

    async def _call_llm_image_edit(
        self,
        image_base64: str,
        model_routing: ModelRouting,
    ) -> EnhancementResult:
        """
        Use LLM with image generation capability for enhancement.
        
        This attempts to use models that support image generation/editing.
        """
        try:
            llm_client = get_llm_client()
            
            # Check if we have a valid API key
            if llm_client.mock_mode:
                return EnhancementResult(
                    success=False,
                    enhanced_image_base64=None,
                    error_message="LLM API未配置有效密钥",
                )

            # Try calling image generation endpoint if available
            # This is a placeholder - actual implementation depends on
            # what image generation APIs are available on the model router
            
            # For now, return failure to fall back to original image
            return EnhancementResult(
                success=False,
                enhanced_image_base64=None,
                error_message="当前LLM不支持图像生成",
            )

        except Exception as e:
            return EnhancementResult(
                success=False,
                enhanced_image_base64=None,
                error_message=f"LLM图像编辑失败: {str(e)}",
            )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global client instance
_client: Optional[ImageModelClient] = None


def get_image_model_client() -> ImageModelClient:
    """Get or create the global image model client instance."""
    global _client
    if _client is None:
        _client = ImageModelClient()
    return _client
