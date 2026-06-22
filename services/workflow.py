from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


PAGE_ENTRY = "错题/薄弱点录入"
PAGE_TRAINING = "苏格拉底训练"
PAGE_ANALYSIS = "薄弱点分析"
PAGE_REVIEW = "周度/月度复盘"

MASTERY_RISK = {
    "陌生": 4,
    "模糊": 3,
    "基本会": 2,
    "熟练": 1,
}


def build_learning_loop_state(
    weak_points: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
) -> dict[str, Any]:
    sessions_by_point = _sessions_by_weak_point(sessions)
    recent_entries = [_recent_entry_row(row, sessions_by_point.get(int(row["id"]), [])) for row in weak_points]
    priority_queue = _priority_queue(weak_points, sessions_by_point)
    subject_cards = _subject_cards(weak_points, sessions_by_point)
    knowledge_rankings = _knowledge_rankings(weak_points)
    mistake_reason_queue = _mistake_reason_queue(weak_points)

    finished_sessions = [row for row in sessions if row.get("status") == "finished"]
    untrained_count = sum(1 for row in weak_points if not sessions_by_point.get(int(row["id"])))

    return {
        "totals": {
            "weak_points": len(weak_points),
            "sessions": len(sessions),
            "finished_sessions": len(finished_sessions),
            "untrained_weak_points": untrained_count,
        },
        "next_action": _next_action(weak_points, sessions, priority_queue, knowledge_rankings),
        "recent_entries": sorted(recent_entries, key=lambda row: row["created_at"], reverse=True),
        "priority_queue": priority_queue,
        "subject_cards": subject_cards,
        "knowledge_rankings": knowledge_rankings,
        "mistake_reason_queue": mistake_reason_queue,
    }


def _sessions_by_weak_point(sessions: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for session in sessions:
        weak_point_id = session.get("weak_point_id")
        if weak_point_id is None:
            continue
        grouped[int(weak_point_id)].append(session)
    return grouped


def _recent_entry_row(weak_point: dict[str, Any], sessions: list[dict[str, Any]]) -> dict[str, Any]:
    status = _training_status(sessions)
    return {
        "id": int(weak_point["id"]),
        "科目": weak_point.get("subject", ""),
        "题型": weak_point.get("question_type", ""),
        "考点": weak_point.get("knowledge_point", ""),
        "错因": weak_point.get("mistake_reason", ""),
        "掌握度": weak_point.get("mastery_level", ""),
        "训练状态": status,
        "workflow_action": _workflow_action_label(status),
        "created_at": weak_point.get("created_at", ""),
    }


def _training_status(sessions: list[dict[str, Any]]) -> str:
    if any(row.get("status") == "active" for row in sessions):
        return "训练中"
    if any(row.get("status") == "finished" for row in sessions):
        return "已完成"
    return "未训练"


def _workflow_action_label(status: str) -> str:
    if status == "训练中":
        return "继续训练"
    if status == "已完成":
        return "再练一次"
    return "开始训练"


def _priority_queue(
    weak_points: list[dict[str, Any]],
    sessions_by_point: dict[int, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows = []
    for row in weak_points:
        weak_point_id = int(row["id"])
        sessions = sessions_by_point.get(weak_point_id, [])
        status = _training_status(sessions)
        risk = MASTERY_RISK.get(str(row.get("mastery_level", "")), 0)
        rows.append(
            {
                "id": weak_point_id,
                "subject": row.get("subject", ""),
                "knowledge_point": row.get("knowledge_point", ""),
                "mistake_reason": row.get("mistake_reason", ""),
                "mastery_level": row.get("mastery_level", ""),
                "training_status": status,
                "workflow_action": _workflow_action_label(status),
                "risk_score": risk,
                "created_at": row.get("created_at", ""),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            1 if row["training_status"] != "已完成" else 0,
            row["risk_score"],
            row["created_at"],
        ),
        reverse=True,
    )


def _subject_cards(
    weak_points: list[dict[str, Any]],
    sessions_by_point: dict[int, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in weak_points:
        grouped[str(row.get("subject", ""))].append(row)

    cards = []
    for subject, rows in grouped.items():
        trained_count = sum(
            1
            for row in rows
            if any(
                session.get("status") == "finished"
                for session in sessions_by_point.get(int(row["id"]), [])
            )
        )
        low_mastery_count = sum(
            1 for row in rows if MASTERY_RISK.get(str(row.get("mastery_level", "")), 0) >= 3
        )
        count = len(rows)
        cards.append(
            {
                "subject": subject,
                "count": count,
                "low_mastery_count": low_mastery_count,
                "trained_count": trained_count,
                "completion_rate": round(trained_count / count, 2) if count else 0,
            }
        )
    return sorted(cards, key=lambda row: (-row["count"], row["subject"]))


def _knowledge_rankings(weak_points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in weak_points:
        grouped[str(row.get("knowledge_point", ""))].append(row)

    rankings = []
    for point, rows in grouped.items():
        subjects = sorted({str(row.get("subject", "")) for row in rows if row.get("subject")})
        low_mastery_count = sum(
            1 for row in rows if MASTERY_RISK.get(str(row.get("mastery_level", "")), 0) >= 3
        )
        count = len(rows)
        rankings.append(
            {
                "knowledge_point": point,
                "count": count,
                "subjects": "、".join(subjects),
                "low_mastery_count": low_mastery_count,
                "recommendation": "优先复盘" if count >= 2 or low_mastery_count else "巩固",
            }
        )
    return sorted(rankings, key=lambda row: (-row["count"], -row["low_mastery_count"], row["knowledge_point"]))


def _mistake_reason_queue(weak_points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reason_counter = Counter(str(row.get("mistake_reason", "")) for row in weak_points)
    return [
        {
            "mistake_reason": reason,
            "count": count,
            "workflow_action": "错因修复追问",
        }
        for reason, count in sorted(reason_counter.items(), key=lambda item: (-item[1], item[0]))
        if reason
    ]


def _next_action(
    weak_points: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    priority_queue: list[dict[str, Any]],
    knowledge_rankings: list[dict[str, Any]],
) -> dict[str, Any]:
    if not weak_points:
        return {
            "kind": "entry",
            "page": PAGE_ENTRY,
            "title": "先录入一个训练点",
            "detail": "录入科目、题型、考点、错因和掌握度后，系统才能安排追问训练。",
        }

    active = next((row for row in sessions if row.get("status") == "active"), None)
    if active and active.get("weak_point_id") is not None:
        return {
            "kind": "continue_training",
            "page": PAGE_TRAINING,
            "weak_point_id": int(active["weak_point_id"]),
            "title": "继续当前苏格拉底训练",
            "detail": "已有训练正在进行，先完成它再进入复盘。",
        }

    if priority_queue:
        first = priority_queue[0]
        return {
            "kind": "train",
            "page": PAGE_TRAINING,
            "weak_point_id": first["id"],
            "title": "处理最高优先级训练点",
            "detail": f"{first['subject']}｜{first['knowledge_point']}｜{first['mastery_level']}",
        }

    if knowledge_rankings:
        first_point = knowledge_rankings[0]["knowledge_point"]
        return {
            "kind": "review",
            "page": PAGE_REVIEW,
            "review_focus": first_point,
            "title": "进入阶段复盘",
            "detail": f"围绕 {first_point} 生成本周或本月复盘。",
        }

    return {
        "kind": "analysis",
        "page": PAGE_ANALYSIS,
        "title": "查看薄弱点分析",
        "detail": "先查看科目、考点和错因分布，再决定下一轮训练。",
    }
