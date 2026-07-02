import logging

from django.conf import settings

from shop.models import ProcessedMessage
from shop.services.ai_operator import AIOperatorService
from shop.services.comment_rules import match_comment_rule, rule_to_response
from shop.services.dm_dedup import collapse_dm_messages
from shop.services.instagram_client import InstagramClient
from shop.services.operator_prompts import COMMENT_ASK_DM_REPLY, COMMENT_DM_FAILED_REPLY
from shop.services.response_builder import ResponseBuilder
from shop.services.zernio_client import ZernioRateLimitError

logger = logging.getLogger(__name__)

PROCESSED_DM_PREFIX = "dm:"
PROCESSED_COMMENT_PREFIX = "comment:"
_poll_cycle = 0


class InstagramPoller:
    def __init__(self) -> None:
        self.enabled = settings.INSTAGRAM_ENABLED
        self.media_amount = settings.INSTAGRAM_MEDIA_AMOUNT
        self.client = InstagramClient()
        self.ai_operator = AIOperatorService()
        self._running = False

    @property
    def is_configured(self) -> bool:
        return self.enabled and self.client.can_auto_connect()

    @staticmethod
    def _is_processed(key: str) -> bool:
        return ProcessedMessage.objects.filter(message_key=key).exists()

    @staticmethod
    def _try_claim(key: str, message_type: str) -> bool:
        _, created = ProcessedMessage.objects.get_or_create(
            message_key=key,
            defaults={"message_type": message_type},
        )
        return created

    @staticmethod
    def _mark_processed(key: str, message_type: str) -> None:
        ProcessedMessage.objects.get_or_create(
            message_key=key,
            defaults={"message_type": message_type},
        )

    def warmup(self) -> None:
        return

    def poll_once(self) -> dict[str, int | bool]:
        if not self.is_configured:
            return {"dm_processed": 0, "comment_processed": 0, "skipped": True}

        if self._running:
            return {"dm_processed": 0, "comment_processed": 0, "skipped": True}

        self._running = True
        try:
            global _poll_cycle
            _poll_cycle += 1

            dm_count = self._poll_direct_messages()
            comment_count = 0
            if _poll_cycle % settings.INSTAGRAM_COMMENT_POLL_EVERY == 0:
                comment_count = self._poll_comments()
            return {
                "dm_processed": dm_count,
                "comment_processed": comment_count,
                "skipped": False,
            }
        except Exception as exc:
            logger.exception("Instagram polling xatosi: %s", exc)
            return {"dm_processed": 0, "comment_processed": 0, "skipped": True}
        finally:
            self._running = False

    def _add_to_baseline(self, message_id: str, *, comment: bool = False) -> None:
        if comment:
            if InstagramClient._baseline_comment_ids is not None:
                InstagramClient._baseline_comment_ids.add(message_id)
        elif InstagramClient._baseline_dm_ids is not None:
            InstagramClient._baseline_dm_ids.add(message_id)

    def _resolve_processable_item(
        self,
        item: dict,
        raw_by_id: dict[str, dict],
    ) -> dict | None:
        related_ids = [
            str(message_id)
            for message_id in (item.get("related_message_ids") or [item["message_id"]])
        ]
        unprocessed_ids = [
            message_id
            for message_id in related_ids
            if not self._is_processed(f"{PROCESSED_DM_PREFIX}{message_id}")
        ]
        if not unprocessed_ids:
            self._mark_dm_group_seen(item)
            return None

        if not self._is_processed(f"{PROCESSED_DM_PREFIX}{item['message_id']}"):
            return item

        candidates = [raw_by_id[message_id] for message_id in unprocessed_ids if message_id in raw_by_id]
        if not candidates:
            return None

        best = max(
            candidates,
            key=lambda message: (
                bool(message.get("image_url")),
                len(message.get("text") or ""),
                message.get("created_at") or "",
            ),
        )
        merged = dict(best)
        texts = [part for part in (item.get("text"), best.get("text")) if part]
        if texts:
            merged["text"] = " ".join(dict.fromkeys(" ".join(texts).split()))
        if item.get("image_url") and not merged.get("image_url"):
            merged["image_url"] = item["image_url"]
            merged["has_image"] = True
        merged["related_message_ids"] = related_ids
        logger.info(
            "DM guruhida yangi xabar tanlandi: %s (eski asosiy: %s)",
            merged["message_id"],
            item["message_id"],
        )
        return merged

    def _mark_dm_group_seen(self, item: dict) -> None:
        related_ids = item.get("related_message_ids") or [item["message_id"]]
        for message_id in related_ids:
            key = f"{PROCESSED_DM_PREFIX}{message_id}"
            self._mark_processed(key, ProcessedMessage.TYPE_DM)
            self._add_to_baseline(str(message_id))

    def _poll_direct_messages(self) -> int:
        processed = 0
        try:
            raw_messages = self.client.fetch_new_direct_messages()
        except ZernioRateLimitError as exc:
            logger.warning("DM o'qish: rate limit — %s", exc)
            return 0
        except Exception as exc:
            logger.error("DM o'qish xatosi: %s", exc)
            return 0

        collapsed = collapse_dm_messages(
            raw_messages,
            burst_seconds=settings.INSTAGRAM_DM_BURST_SECONDS,
        )
        raw_by_id = {str(message["message_id"]): message for message in raw_messages}
        if len(collapsed) < len(raw_messages):
            logger.info(
                "DM birlashtirildi: %d ta xabar → %d ta javob",
                len(raw_messages),
                len(collapsed),
            )

        for item in collapsed:
            item = self._resolve_processable_item(item, raw_by_id)
            if not item:
                continue

            primary_id = str(item["message_id"])
            primary_key = f"{PROCESSED_DM_PREFIX}{primary_id}"
            related_ids = [str(message_id) for message_id in (item.get("related_message_ids") or [primary_id])]

            if not self._try_claim(primary_key, ProcessedMessage.TYPE_DM):
                logger.debug("DM o'tkazildi (boshqa poll band qilgan): %s", primary_id)
                continue

            try:
                if item.get("image_url"):
                    logger.info(
                        "Rasm DM qayta ishlanmoqda: message_id=%s (jami %d ta xabar birlashtirildi)",
                        primary_id,
                        len(related_ids),
                    )

                response = self.ai_operator.process_message(
                    item.get("text", ""),
                    channel=ResponseBuilder.CHANNEL_DM,
                    image_url=item.get("image_url"),
                )
                if not (response.reply or "").strip():
                    self._mark_dm_group_seen(item)
                    logger.info(
                        "Rasm DM — katalogda topilmadi, javob yuborilmadi: message_id=%s",
                        primary_id,
                    )
                    continue

                self.client.send_direct_reply(item["thread_id"], response.reply)
                self._mark_dm_group_seen(item)
                processed += 1
                logger.info(
                    "DM ga javob berildi: '%s...'",
                    (item.get("text") or "[rasm]")[:50],
                )
            except ZernioRateLimitError as exc:
                logger.warning("DM javob: rate limit — %s", exc)
                ProcessedMessage.objects.filter(message_key=primary_key).delete()
                break
            except Exception as exc:
                logger.exception("DM qayta ishlash xatosi: %s", exc)
                ProcessedMessage.objects.filter(message_key=primary_key).delete()

        return processed

    def _poll_comments(self) -> int:
        processed = 0
        try:
            raw_comments = self.client.fetch_new_comments(self.media_amount)
        except ZernioRateLimitError as exc:
            logger.warning("Izoh o'qish: rate limit — %s", exc)
            return 0
        except Exception as exc:
            logger.error("Izoh o'qish xatosi: %s", exc)
            return 0

        for item in raw_comments:
            key = f"{PROCESSED_COMMENT_PREFIX}{item['comment_id']}"
            if self._is_processed(key):
                continue

            if not self._try_claim(key, ProcessedMessage.TYPE_COMMENT):
                continue

            try:
                rule = match_comment_rule(item["text"], str(item.get("media_id", "")))
                if rule:
                    preset = rule_to_response(rule)
                    public_reply = preset["reply"]
                    if preset["send_dm"] and preset["dm_reply"]:
                        dm_sent = self._try_send_dm(item.get("user_id", ""), preset["dm_reply"])
                        if not dm_sent:
                            public_reply = COMMENT_DM_FAILED_REPLY
                    self.client.reply_to_comment(
                        item["media_id"],
                        item["comment_id"],
                        public_reply,
                        item.get("username", ""),
                    )
                    self._mark_processed(key, ProcessedMessage.TYPE_COMMENT)
                    self._add_to_baseline(item["comment_id"], comment=True)
                    processed += 1
                    logger.info(
                        "Izohga qoida javobi: keyword='%s', '%s...'",
                        rule.keyword,
                        item["text"][:50],
                    )
                    continue

                response = self.ai_operator.process_message(
                    item["text"],
                    channel=ResponseBuilder.CHANNEL_COMMENT,
                )
                public_reply = response.reply

                if response.send_dm and response.dm_reply:
                    dm_sent = self._try_send_dm(item.get("user_id", ""), response.dm_reply)
                    if not dm_sent:
                        public_reply = COMMENT_DM_FAILED_REPLY
                elif response.send_dm and not response.dm_reply:
                    dm_sent = self._try_send_dm(item.get("user_id", ""), response.reply)
                    if not dm_sent:
                        public_reply = COMMENT_ASK_DM_REPLY

                self.client.reply_to_comment(
                    item["media_id"],
                    item["comment_id"],
                    public_reply,
                    item.get("username", ""),
                )
                self._mark_processed(key, ProcessedMessage.TYPE_COMMENT)
                self._add_to_baseline(item["comment_id"], comment=True)
                processed += 1
                logger.info("Izohga javob berildi: '%s...'", item["text"][:50])
            except ZernioRateLimitError as exc:
                logger.warning("Izoh javob: rate limit — %s", exc)
                ProcessedMessage.objects.filter(message_key=key).delete()
                break
            except Exception as exc:
                logger.exception("Izoh qayta ishlash xatosi: %s", exc)
                ProcessedMessage.objects.filter(message_key=key).delete()

        return processed

    def _try_send_dm(self, user_id: str, text: str) -> bool:
        if not user_id or not text:
            return False
        try:
            self.client.send_direct_to_user(user_id, text)
            logger.info("Izohdan DM yuborildi: user=%s", user_id)
            return True
        except Exception as exc:
            logger.warning("Izohdan DM yuborib bo'lmadi (user=%s): %s", user_id, exc)
            return False

    def get_status(self) -> dict:
        if not self.enabled:
            return {"enabled": False, "configured": False, "connected": False}

        if not self.client.is_configured:
            return {
                "enabled": self.enabled,
                "configured": False,
                "connected": False,
                "provider": "zernio",
                "message": "ZERNIO_API_KEY .env da ko'rsatilmagan",
            }

        try:
            info = self.client.get_account_info()
            return {
                "enabled": True,
                "configured": True,
                "connected": True,
                "provider": "zernio",
                "username": info["username"],
                "full_name": info["full_name"],
                "user_id": info["user_id"],
                "account_id": info.get("account_id"),
            }
        except Exception as exc:
            return {
                "enabled": True,
                "configured": bool(settings.ZERNIO_API_KEY),
                "connected": False,
                "provider": "zernio",
                "message": str(exc),
            }
