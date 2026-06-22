from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAFE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9_\-\u4e00-\u9fff]+")


def save_provenance_files(
    root: str | Path,
    event_type: str,
    entity_type: str,
    entity_id: int | None,
    input_payload: dict[str, Any],
    output_text: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    now = datetime.now(timezone.utc)
    day_dir = Path(root) / now.strftime("%Y%m%d")
    day_dir.mkdir(parents=True, exist_ok=True)

    suffix_id = "none" if entity_id is None else str(entity_id)
    stem = _safe_name(f"{event_type}_{entity_type}_{suffix_id}_{now.strftime('%H%M%S%f')}")
    input_path = day_dir / f"{stem}_input.json"
    output_path = day_dir / f"{stem}_output.md"

    input_path.write_text(
        json.dumps(input_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    output_path.write_text(str(output_text), encoding="utf-8")

    return {
        "input_path": input_path,
        "output_path": output_path,
        "metadata": {
            **metadata,
            "saved_at": now.isoformat(timespec="seconds"),
        },
    }


def _safe_name(value: str) -> str:
    safe = SAFE_NAME_PATTERN.sub("_", value).strip("_")
    return safe or "provenance"
