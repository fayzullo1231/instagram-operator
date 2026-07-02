"""Izoh kalit so'z qoidalarini tekshirish."""

from __future__ import annotations

import logging

from shop.models import CommentKeywordRule
from shop.utils.text import normalize_search_text

logger = logging.getLogger(__name__)


def match_comment_rule(
    comment_text: str,
    media_id: str,
) -> CommentKeywordRule | None:
    text = normalize_search_text(comment_text)
    if not text:
        return None

    rules = (
        CommentKeywordRule.objects.filter(is_active=True)
        .select_related("video")
        .order_by("-priority", "id")
    )

    scoped: list[CommentKeywordRule] = []
    global_rules: list[CommentKeywordRule] = []
    for rule in rules:
        if rule.video_id and rule.video and rule.video.is_active:
            if str(rule.video.media_id) == str(media_id):
                scoped.append(rule)
        elif not rule.video_id:
            global_rules.append(rule)

    for rule in scoped + global_rules:
        if _keyword_matches(text, rule):
            logger.info(
                "Izoh qoidasi topildi: keyword='%s', video=%s",
                rule.keyword,
                rule.video_id or "global",
            )
            return rule
    return None


def _keyword_matches(normalized_comment: str, rule: CommentKeywordRule) -> bool:
    keyword = normalize_search_text(rule.keyword)
    if not keyword:
        return False

    if rule.match_type == CommentKeywordRule.MATCH_EXACT:
        return normalized_comment == keyword
    if rule.match_type == CommentKeywordRule.MATCH_STARTS:
        return normalized_comment.startswith(keyword)
    return keyword in normalized_comment


def rule_to_response(rule: CommentKeywordRule) -> dict:
    return {
        "reply": rule.public_reply,
        "dm_reply": rule.dm_reply.strip() or None,
        "send_dm": rule.send_dm and bool(rule.dm_reply.strip()),
    }
