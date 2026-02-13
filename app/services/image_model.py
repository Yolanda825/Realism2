"""Image model service for executing image enhancement."""

import json
import asyncio
import base64
import uuid
from typing import Optional, TYPE_CHECKING
import httpx

from app.config import get_settings
from app.models.schemas import ModelRouting, EnhancementResult

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
        self.client = httpx.AsyncClient(timeout=120.0)
        # Store last nano/MHC raw results for debugging
        self._last_mhc: dict = {}
        
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
                print(f"[ImageModelClient] Warning: Failed to initialize MHC client: {e}")
                self.mhc_client = None
        
        if self.mhc_client:
            print("[ImageModelClient] MHC client initialized successfully")
        else:
            print("[ImageModelClient] MHC client not available - enhancement will fail until configured")
     
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
        Execute image enhancement using MHC API.

        Args:
            image_base64: Base64-encoded image data
            model_routing: Model routing with prompt and parameters
            preservation_prompt: Optional preservation constraints (identity, expression)
            correction_prompt: Optional correction guidance (for expression correction)
            expression_mode: "preserve" or "correct"

        Returns:
            EnhancementResult with enhanced image or error
        """
        # Check MHC client availability
        if not self.mhc_client:
            return EnhancementResult(
                success=False,
                enhanced_image_base64=None,
                error_message="MHC 客户端未初始化。请在 .env 中配置 MHC_APP, MHC_BIZ, MHC_NANO_TOKEN",
                debug_mhc=None,
            )
        
        if not self.mhc_nano_token:
            return EnhancementResult(
                success=False,
                enhanced_image_base64=None,
                error_message="MHC_NANO_TOKEN 未配置。请联系元建获取 Token，并在 .env 中配置",
                debug_mhc=None,
            )
        
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
        
        # Call MHC API
        return await self._call_mhc_api(image_base64, composed_routing)
    
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
        # Check MHC client availability
        if not self.mhc_client:
            return EnhancementResult(
                success=False,
                enhanced_image_base64=None,
                error_message="MHC 客户端未初始化。请在 .env 中配置 MHC_APP, MHC_BIZ, MHC_NANO_TOKEN",
                debug_mhc=None,
            )
        
        if not self.mhc_nano_token:
            return EnhancementResult(
                success=False,
                enhanced_image_base64=None,
                error_message="MHC_NANO_TOKEN 未配置",
                debug_mhc=None,
            )
        
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
        
        # Call MHC API
        return await self._call_mhc_api(image_base64, model_routing)

    async def _call_mhc_api(
        self,
        image_base64: str,
        model_routing: ModelRouting,
    ) -> EnhancementResult:
        """Call MHC image-to-image API

        使用 lib.ai.api.AiApi.runAsync 提交异步任务，再用 queryResult 轮询结果；
        参数采用外采改图接口：app_scene=go, path_scene=imgEdit, model=gemini-3-pro-image-preview 等。
        """
        try:
            # Base parameter payload; will augment with inlineData
            params = {
                "parameter": {
                    "app_scene": "go",
                    "model": "gemini-3-pro-image-preview",
                    "path_scene": "imgEdit",
                    "prompt": model_routing.prompt,
                    "resolution": "2K",
                    "token": self.mhc_nano_token,
                    "trace_id": str(uuid.uuid4()),
                }
            }

            # Prepare image payloads: prefer public URL for init_images, and include inlineData for providers requiring it
            image_url = None
            mime_type = "image/jpeg"
            if image_base64.startswith("http://") or image_base64.startswith("https://"):
                image_url = image_base64
            elif image_base64.startswith("data:"):
                try:
                    header, b64data = image_base64.split(",", 1)
                    # e.g., data:image/png;base64,
                    if ";" in header and header.startswith("data:"):
                        mime_part = header.split(":", 1)[1].split(";", 1)[0]
                        mime_type = mime_part or mime_type
                    image_base64 = b64data
                except Exception:
                    pass
            else:
                # Raw base64 input; keep default mime_type
                pass

            # Inject inlineData into parameter
            params["parameter"]["image"] = {
                "inlineData": {
                    "mimeType": mime_type,
                    "data": image_base64,
                }
            }

            # 从 settings 读取 apipath
            apiPath = self.mhc_api_path

            print("[MHC] Submitting image enhancement task...")
            loop = asyncio.get_event_loop()
            # Build init_images: prefer public URL; otherwise provide inlineData
            init_images = None
            if image_url:
                init_images = [{"url": image_url}]
            else:
                init_images = [{"inlineData": {"mimeType": mime_type, "data": image_base64}}]

            task_result = await loop.run_in_executor(
                None,
                lambda: self.mhc_client.runAsync(
                    init_images,
                    params,
                    apiPath,
                    "mtlab",
                ),
            )
            # Debug: record and print submit response
            self._last_mhc = {"submit": task_result}
            try:
                print("[MHC] submit response:", json.dumps(task_result, ensure_ascii=False)[:800])
            except Exception:
                print("[MHC] submit response (non-serializable)")

            # 从 data.result 取 task_id，再 queryResult
            data = task_result.get("data") or {}
            result_inner = data.get("result") or {}
            task_id = result_inner.get("id") or task_result.get("msg_id")
            if not task_id:
                return EnhancementResult(
                    success=False,
                    enhanced_image_base64=None,
                    error_message=f"MHC API 任务提交失败，无 task_id: {json.dumps(task_result, ensure_ascii=False)[:500]}",
                    debug_mhc=self._last_mhc,
                )

            print(f"[MHC] Task submitted successfully, task_id: {task_id}")
            
            # 轮询结果（与 test_minimal 一致：queryResult 返回 { is_finished, result }，result 为完整响应）
            max_attempts = 150  # ~5 minutes at 2s interval to allow external processing
            for attempt in range(max_attempts):
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

                print(f"[MHC] Polling attempt {attempt + 1}/{max_attempts}, status: {status}")

                if status == 10 or status == 2 or status == 20:
                    # Debug: record and print final response
                    self._last_mhc["final"] = raw
                    try:
                        print("[MHC] final response:", json.dumps(raw, ensure_ascii=False)[:1200])
                    except Exception:
                        print("[MHC] final response (non-serializable)")
                    output = data.get("output") or data.get("result") or data
                    enhanced_image = None
                    if isinstance(output, dict):
                        enhanced_image = (
                            output.get("image_base64")
                            or output.get("base64")
                            or output.get("image")
                            or output.get("result_image")
                        )
                        # Try top-level 'urls' array
                        if not enhanced_image:
                            urls = output.get("urls") or output.get("images") or []
                            if isinstance(urls, list) and urls:
                                enhanced_image = await self._download_image_as_base64(urls[0])
                        # Try nested media_info_list under 'data'
                        if not enhanced_image:
                            inner_data = output.get("data") or {}
                            media_list = inner_data.get("media_info_list") or []
                            if isinstance(media_list, list) and media_list:
                                url = media_list[0].get("media_data") or media_list[0].get("url") or media_list[0].get("image_url")
                                if url:
                                    enhanced_image = await self._download_image_as_base64(url)
                        # Single 'url' field
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
                        print(f"[MHC] enhanced image base64 length: {len(enhanced_image)}")
                        return EnhancementResult(
                            success=True,
                            enhanced_image_base64=enhanced_image,
                            error_message=None,
                            debug_mhc=self._last_mhc,
                        )
                    msg = (task_result.get("message") or data.get("error_msg") or data.get("msg") or "未知错误")
                    return EnhancementResult(
                        success=False,
                        enhanced_image_base64=None,
                        error_message=f"MHC API 返回格式未知/无输出: {msg}",
                        debug_mhc=self._last_mhc,
                    )
                if status in ("failed", "error") or (isinstance(status, int) and status not in (0, 1, 9)):
                    err = data.get("error") or data.get("error_msg") or task_result.get("message") or "未知错误"
                    self._last_mhc["final"] = raw
                    print(f"[MHC] task failed: {err}")
                    return EnhancementResult(
                        success=False,
                        enhanced_image_base64=None,
                        error_message=f"MHC API 任务失败: {err}",
                        debug_mhc=self._last_mhc,
                    )

            return EnhancementResult(
                success=False,
                enhanced_image_base64=None,
                error_message="MHC API 任务超时（60秒）",
                debug_mhc=self._last_mhc,
            )
        except Exception as e:
            self._last_mhc["error"] = str(e)
            print(f"[MHC] exception: {str(e)}")
            return EnhancementResult(
                success=False,
                enhanced_image_base64=None,
                error_message=f"MHC API 调用失败: {str(e)}",
                debug_mhc=self._last_mhc,
            )
    
    async def _download_image_as_base64(self, url: str) -> Optional[str]:
        """Download an image from URL and convert to base64."""
        try:
            response = await self.client.get(url, timeout=30.0)
            response.raise_for_status()
            return base64.b64encode(response.content).decode("utf-8")
        except Exception as e:
            print(f"[MHC] Failed to download image from {url}: {e}")
            return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    # Debug helper
    def get_last_mhc_debug(self) -> dict:
        return self._last_mhc


# Global client instance
_client: Optional[ImageModelClient] = None


def get_image_model_client() -> ImageModelClient:
    """Get or create the global image model client instance."""
    global _client
    if _client is None:
        _client = ImageModelClient()
    return _client
