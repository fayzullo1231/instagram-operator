"""Izoh kalit so'z qoidalarini tekshirish."""

from __future__ import annotations

import logging

from django.conf import settings

from shop.models import CommentKeywordRule
from shop.utils.text import normalize_search_text

logger = logging.getLogger(__name__)

DEFAULT_PUBLIC_IMAGE_REPLY = "Ma'lumotni Direct xabarda yubordik"


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
                rule.video.title if rule.video_id else "global",
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


def _absolute_media_url(relative_url: str) -> str:
    if relative_url.startswith("http://") or relative_url.startswith("https://"):
        return relative_url
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    path = relative_url if relative_url.startswith("/") else f"/{relative_url}"
    return f"{base}{path}"


def resolve_rule_image_url(rule: CommentKeywordRule) -> str | None:
    if rule.dm_image:
        return _absolute_media_url(rule.dm_image.url)
    if rule.reply_image:
        return _absolute_media_url(rule.reply_image.url)
    return None


def rule_to_response(rule: CommentKeywordRule) -> dict:
    image_url = resolve_rule_image_url(rule)
    public_reply = (rule.public_reply or "").strip()
    dm_reply = (rule.dm_reply or "").strip() or None

    if not public_reply and image_url:
        public_reply = DEFAULT_PUBLIC_IMAGE_REPLY

    send_dm = rule.send_dm and bool(dm_reply or image_url)

    return {
        "reply": public_reply,
        "dm_reply": dm_reply,
        "send_dm": send_dm,
        "image_url": image_url,
    }
