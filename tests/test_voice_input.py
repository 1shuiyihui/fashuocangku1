from pathlib import Path

from services.voice_input import (
    VOICE_INPUT_LANGUAGE,
    merge_voice_text,
    normalize_voice_payload,
)


def test_normalize_voice_payload_accepts_component_dict():
    payload = {
        "text": "  共同犯罪包括共同故意和共同行为  ",
        "language": "zh-CN",
        "timestamp": 123,
    }

    assert normalize_voice_payload(payload) == "共同犯罪包括共同故意和共同行为"


def test_normalize_voice_payload_rejects_empty_or_invalid_values():
    assert normalize_voice_payload(None) == ""
    assert normalize_voice_payload({}) == ""
    assert normalize_voice_payload({"text": "   "}) == ""
    assert normalize_voice_payload("共同犯罪") == ""


def test_merge_voice_text_appends_without_duplicate_repeats():
    assert merge_voice_text("", "共同犯罪") == "共同犯罪"
    assert merge_voice_text("共同犯罪", "共同犯罪") == "共同犯罪"
    assert merge_voice_text("共同犯罪", "二人以上共同故意") == "共同犯罪\n二人以上共同故意"


def test_voice_component_html_contract():
    html = Path("components/voice_input/index.html").read_text(encoding="utf-8")

    assert VOICE_INPUT_LANGUAGE == "zh-CN"
    assert "webkitSpeechRecognition" in html
    assert "streamlit:setComponentValue" in html
    assert "streamlit:componentReady" in html
    assert "开始语音输入" in html
    assert "停止" in html
