import json

from services.provenance import save_provenance_files


def test_save_provenance_files_writes_input_and_output_with_utf8(tmp_path):
    result = save_provenance_files(
        root=tmp_path / "provenance",
        event_type="training_ai_call",
        entity_type="session",
        entity_id=7,
        input_payload={"prompt": "请围绕抢劫罪继续追问", "round": 3},
        output_text="追问：行为人压制反抗的手段是什么？",
        metadata={"model": "deepseek-v4-pro"},
    )

    input_path = result["input_path"]
    output_path = result["output_path"]

    assert input_path.exists()
    assert output_path.exists()
    assert input_path.parent == output_path.parent
    assert "training_ai_call_session_7" in input_path.name
    assert json.loads(input_path.read_text(encoding="utf-8"))["prompt"] == "请围绕抢劫罪继续追问"
    assert "压制反抗" in output_path.read_text(encoding="utf-8")
    assert result["metadata"]["model"] == "deepseek-v4-pro"
