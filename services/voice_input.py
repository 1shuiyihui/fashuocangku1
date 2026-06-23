from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components


VOICE_INPUT_LANGUAGE = "zh-CN"
VOICE_INPUT_HEIGHT = 176
VOICE_INPUT_DIR = Path(__file__).resolve().parents[1] / "components" / "voice_input"

_voice_input_component = components.declare_component(
    "fashuo_voice_input",
    path=str(VOICE_INPUT_DIR),
)


def voice_input(
    label: str,
    key: str,
    language: str = VOICE_INPUT_LANGUAGE,
    helper_text: str = "",
) -> dict[str, Any] | None:
    return _voice_input_component(
        label=label,
        language=language,
        helperText=helper_text,
        default=None,
        key=key,
        height=VOICE_INPUT_HEIGHT,
    )


def normalize_voice_payload(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    text = str(payload.get("text") or payload.get("final_text") or "").strip()
    return " ".join(text.split())


def merge_voice_text(existing: str, addition: str) -> str:
    existing = str(existing or "").strip()
    addition = str(addition or "").strip()
    if not addition:
        return existing
    if not existing:
        return addition
    if addition in existing:
        return existing
    return f"{existing}\n{addition}"
