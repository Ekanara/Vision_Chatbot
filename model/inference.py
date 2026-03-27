import base64
import logging
import mimetypes
import os
from pathlib import Path
from typing import Dict, List, Optional

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are ImageSeeker, a helpful AI vision assistant. "
    "When an image is provided, describe what you see, answer user questions about it, "
    "and mention uncertainty when details are ambiguous. "
    "Keep responses concise but useful."
)


def _env(name: str, legacy_name: str = "") -> str:
    value = os.getenv(name, "")
    if value:
        return value
    if legacy_name:
        return os.getenv(legacy_name, "")
    return ""


def _guess_mime_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    return mime or "image/jpeg"


def _image_to_data_url(path: Path) -> str:
    raw = path.read_bytes()
    encoded = base64.b64encode(raw).decode("utf-8")
    mime = _guess_mime_type(path)
    return f"data:{mime};base64,{encoded}"


def _build_prompt(user_message: str, ocr_text: str) -> str:
    prompt = user_message or "Analyze this image and help me understand it."
    if ocr_text:
        prompt += f"\n\nOCR text extracted from image:\n{ocr_text[:2000]}"
    return prompt


def _to_responses_input(
    user_message: str,
    history: List[Dict[str, str]],
    image_path: Optional[Path],
    ocr_text: str,
):
    inputs = [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
        }
    ]

    for item in history[-8:]:
        role = item.get("role", "user")
        content = item.get("content", "")
        if content:
            inputs.append(
                {
                    "role": role,
                    "content": [{"type": "input_text", "text": content}],
                }
            )

    user_content = [{"type": "input_text", "text": _build_prompt(user_message, ocr_text)}]
    if image_path:
        user_content.append(
            {
                "type": "input_image",
                "image_url": _image_to_data_url(image_path),
            }
        )

    inputs.append({"role": "user", "content": user_content})
    return inputs


def _to_chat_messages(
    user_message: str,
    history: List[Dict[str, str]],
    image_path: Optional[Path],
    ocr_text: str,
):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for item in history[-8:]:
        role = item.get("role", "user")
        content = item.get("content", "")
        if content:
            messages.append({"role": role, "content": content})

    prompt = _build_prompt(user_message, ocr_text)
    if image_path:
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": _image_to_data_url(image_path)}},
                ],
            }
        )
    else:
        messages.append({"role": "user", "content": prompt})

    return messages


def _chat_text(response) -> str:
    try:
        content = response.choices[0].message.content
    except Exception:
        return ""

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(text)
            else:
                text = getattr(item, "text", None)
                if text:
                    parts.append(text)
        return "\n".join(parts).strip()

    return ""


def generate_vision_reply(
    user_message: str,
    image_path: Optional[Path] = None,
    ocr_text: str = "",
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    history = history or []

    api_key = _env("AI_API_KEY", "OPENAI_API_KEY")
    if not api_key:
        return "AI key is not configured. Set AI_API_KEY in your environment to enable vision responses."

    try:
        model = _env("AI_MODEL", "OPENAI_MODEL") or "gpt-4.1"
        base_url = _env("AI_BASE_URL", "OPENAI_BASE_URL").strip()
        force_chat = _env("AI_USE_CHAT_COMPLETIONS", "OPENAI_USE_CHAT_COMPLETIONS").lower() in {
            "1",
            "true",
            "yes",
        }

        client = OpenAI(api_key=api_key, base_url=base_url or None)

        if force_chat or base_url:
            response = client.chat.completions.create(
                model=model,
                messages=_to_chat_messages(
                    user_message=user_message,
                    history=history,
                    image_path=image_path,
                    ocr_text=ocr_text,
                ),
                temperature=0.2,
                max_tokens=700,
            )
            text = _chat_text(response)
        else:
            response = client.responses.create(
                model=model,
                input=_to_responses_input(
                    user_message=user_message,
                    history=history,
                    image_path=image_path,
                    ocr_text=ocr_text,
                ),
                temperature=0.2,
                max_output_tokens=700,
            )
            text = response.output_text.strip()

        if text:
            return text

        return "I could not generate a response from the model. Please try again."

    except AuthenticationError:
        return "Authentication failed. Check AI_API_KEY and AI_BASE_URL in .env, then restart the app."
    except RateLimitError:
        return "Provider rate limit reached. Please wait a moment and try again."
    except (APIConnectionError, APITimeoutError):
        return "Could not reach the model provider right now. Check your network and retry."
    except APIStatusError as exc:
        logger.warning("Model provider API status error: %s", exc)
        return "Model provider returned an error. Please try again in a moment."
    except Exception:
        logger.exception("Unexpected model call failure")
        return "Unexpected model error. Check server logs and try again."
