"""DM xabarlarini birlashtirish — bitta rasm uchun bitta javob."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def parse_message_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def collapse_dm_messages(
    messages: list[dict[str, Any]],
    *,
    burst_seconds: int,
) -> list[dict[str, Any]]:
    """Bir suhbatdagi yaqin vaqtli xabarlarni bitta xabarga birlashtiradi."""
    if not messages:
        return []

    by_thread: dict[str, list[dict[str, Any]]] = {}
    for message in messages:
        by_thread.setdefault(str(message.get("thread_id", "")), []).append(message)

    collapsed: list[dict[str, Any]] = []
    for thread_messages in by_thread.values():
        thread_messages.sort(
            key=lambda item: item.get("created_at") or "",
            reverse=True,
        )
        groups: list[list[dict[str, Any]]] = []
        for message in thread_messages:
            message_time = parse_message_time(message.get("created_at"))
            matched = False
            for group in groups:
                anchor_time = parse_message_time(group[0].get("created_at"))
                if (
                    message_time
                    and anchor_time
                    and abs((anchor_time - message_time).total_seconds()) <= burst_seconds
                ):
                    group.append(message)
                    matched = True
                    break
            if not matched:
                groups.append([message])

        for group in groups:
            collapsed.append(_merge_message_group(group))

    collapsed.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return collapsed


def _merge_message_group(group: list[dict[str, Any]]) -> dict[str, Any]:
    primary = max(
        group,
        key=lambda item: (
            bool(item.get("image_url")),
            len(item.get("text") or ""),
            item.get("created_at") or "",
        ),
    )
    merged = dict(primary)
    texts: list[str] = []
    image_url = merged.get("image_url")
    related_ids: list[str] = []

    for item in group:
        related_ids.append(str(item["message_id"]))
        text = (item.get("text") or "").strip()
        if text and text not in texts:
            texts.append(text)
        if not image_url and item.get("image_url"):
            image_url = item.get("image_url")

    if texts:
        merged["text"] = " ".join(texts)
    if image_url:
        merged["image_url"] = image_url
        merged["has_image"] = True
    merged["related_message_ids"] = list(dict.fromkeys(related_ids))
    return merged
