"""
LLM 客户端封装

兼容 OpenAI API 格式，支持 deepseek 等服务商
"""
import base64
import json
import logging
from typing import Optional

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM 调用客户端"""

    def __init__(self):
        logger.info(f"LLMClient 初始化: provider={settings.LLM_PROVIDER}, model={settings.LLM_MODEL}, base_url={settings.LLM_BASE_URL}")
        self.client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            timeout=180.0,  # Token Plan 视觉请求需要较长时间
            max_retries=1,   # 减少 SDK 自动重试，更快返回错误
        )
        self.model = settings.LLM_MODEL

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 4000,
    ) -> str:
        """纯文本对话"""
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    def _compress_image(self, image_bytes: bytes, ext: str, max_kb: int = 150) -> bytes:
        """压缩图片，减少传输体积"""
        try:
            from PIL import Image
            from io import BytesIO
            img = Image.open(BytesIO(image_bytes))
            w, h = img.size
            # 限制最大边长 2048px
            max_side = 2048
            if max(w, h) > max_side:
                ratio = max_side / max(w, h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            # 转 RGB（去掉 alpha 通道）
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            # 逐步降低质量直到满足大小要求
            buf = BytesIO()
            for quality in (75, 60, 45, 30):
                buf.seek(0)
                buf.truncate()
                img.save(buf, format="JPEG", quality=quality, optimize=True)
                if buf.tell() <= max_kb * 1024:
                    break
            result = buf.getvalue()
            logger.info(f"_compress_image: {len(image_bytes)//1024}KB -> {len(result)//1024}KB, size={img.size}, quality~{quality}")
            return result
        except Exception as e:
            logger.warning(f"_compress_image: 压缩失败 {e}, 使用原始图片")
            return image_bytes

    def chat_with_image(
        self,
        system_prompt: str,
        user_prompt: str,
        image_path: str,
        temperature: float = 0.0,
        max_tokens: int = 4000,
    ) -> str:
        """带图片的视觉对话"""
        import os as _os
        _img_size_kb = _os.path.getsize(image_path) / 1024
        logger.info(f"chat_with_image: model={self.model}, base_url={settings.LLM_BASE_URL}, image={image_path} ({_img_size_kb:.1f}KB)")

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        ext = image_path.split(".")[-1].lower()
        # 压缩图片以加快传输
        image_bytes = self._compress_image(image_bytes, ext)
        mime = "image/jpeg"  # 统一用 JPEG
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime};base64,{b64}"
        logger.info(f"chat_with_image: data_url长度={len(data_url)//1024}KB")

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    },
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result = resp.choices[0].message.content or ""
            logger.info(f"chat_with_image: 成功, 返回{len(result)}字符")
            return result
        except Exception as e:
            logger.error(f"chat_with_image: 失败! type={type(e).__name__}, msg={e}", exc_info=True)
            raise


# 全局单例
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
