from __future__ import annotations

from collections import Counter
from typing import Any

from services.error_analysis import build_review_drill_pack


MASTERY_RISK = {
    "陌生": 4,
    "模糊": 3,
    "基本会": 2,
    "熟练": 1,
}


def compute_weak_point_stats(
    weak_points: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
) -> dict[str, Any]:
    subject_counter = Counter(row["subject"] for row in weak_points)
    point_counter = Counter(row["knowledge_point"] for row in weak_points)
    reason_counter = Counter(row["mistake_reason"] for row in weak_points)
    low_mastery = [
        row
        for row in weak_points
        if MASTERY_RISK.get(row.get("mastery_level", ""), 0) >= 3
    ]
    finished_sessions = [row for row in sessions if row.get("status") == "finished"]

    return {
        "total_weak_points": len(weak_points),
        "total_sessions": len(sessions),
        "finished_sessions": len(finished_sessions),
        "by_subject": _counter_rows(subject_counter, "subject"),
        "by_knowledge_point": _counter_rows(point_counter, "knowledge_point"),
        "by_mistake_reason": _counter_rows(reason_counter, "mistake_reason"),
        "low_mastery": sorted(
            low_mastery,
            key=lambda row: (
                MASTERY_RISK.get(row.get("mastery_level", ""), 0),
                row["created_at"],
            ),
            reverse=True,
        ),
    }


def build_review_report(
    period_label: str,
    weak_points: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    error_analyses: list[dict[str, Any]] | None = None,
) -> str:
    stats = compute_weak_point_stats(weak_points, sessions)
    top_points = stats["by_knowledge_point"][:5]
    top_reasons = stats["by_mistake_reason"][:5]
    low_mastery = stats["low_mastery"][:5]

    lines = [
        f"# {period_label}复盘",
        "",
        "## 学习概况",
        f"- 新增/累计薄弱点：{stats['total_weak_points']} 个",
        f"- 苏格拉底训练：{stats['total_sessions']} 次，其中已完成 {stats['finished_sessions']} 次",
        "",
        "## 高频薄弱考点",
    ]
    lines.extend(_bullet_rows(top_points, "knowledge_point"))
    lines.extend(["", "## 高频错因"])
    lines.extend(_bullet_rows(top_reasons, "mistake_reason"))
    if error_analyses:
        lines.extend(["", "## 错因还原"])
        for row in error_analyses[:8]:
            lines.append(
                f"- {row.get('knowledge_point', '')}｜{row.get('error_location', '')}｜{row.get('root_cause', '')}：{row.get('evidence', '')}"
            )
        lines.extend(["", "## 复盘练习与变式练习"])
        for pack in build_review_drill_pack(error_analyses)[:5]:
            lines.append(f"- {pack['root_cause']}（{pack['count']} 次）：{pack['focus_points']}")
            for drill in pack["review_drills"][:2]:
                lines.append(f"  - 复盘练习：{drill}")
            for drill in pack["variant_drills"][:2]:
                lines.append(f"  - 变式练习：{drill}")
    lines.extend(["", "## 建议优先训练"])
    if low_mastery:
        for row in low_mastery:
            lines.append(
                f"- {row['subject']}｜{row['knowledge_point']}｜掌握度：{row['mastery_level']}｜建议使用：错因修复追问或构成要件追问"
            )
    else:
        lines.append("- 暂无低掌握度考点，建议选择最近新增错题进行巩固追问。")
    lines.extend(
        [
            "",
            "## 下阶段计划",
            "- 每天至少选择 1 个低掌握度考点完成一次苏格拉底训练。",
            "- 对出现 2 次及以上的考点，优先使用概念辨析追问或案例分析追问。",
            "- 对主观题相关错因，训练结束后补写一版完整采分表达。",
        ]
    )
    return "\n".join(lines)


def _counter_rows(counter: Counter[str], key: str) -> list[dict[str, Any]]:
    return [
        {key: name, "count": count}
        for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _bullet_rows(rows: list[dict[str, Any]], key: str) -> list[str]:
    if not rows:
        return ["- 暂无记录。"]
    return [f"- {row[key]}：{row['count']} 次" for row in rows]
