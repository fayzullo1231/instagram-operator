from unittest.mock import MagicMock, patch

from shop.services.instagram_poller import InstagramPoller
from shop.services.operator_prompts import (
    COMMENT_DM_FAILED_REPLY,
    COMMENT_INFO_REPLY,
    COMMENT_PRICE_REPLY,
)


def _comment_item() -> dict:
    return {
        "comment_id": "c1",
        "media_id": "m1",
        "user_id": "u1",
        "username": "tester",
        "text": "narx",
    }


@patch.object(InstagramPoller, "_deliver_comment_dm", return_value=True)
def test_post_comment_reply_success_only_when_dm_sent(mock_dm):
    poller = InstagramPoller()
    poller.client = MagicMock()

    dm_sent, posted = poller._post_comment_reply(
        _comment_item(),
        public_reply=COMMENT_PRICE_REPLY,
        dm_reply="Mahsulot narxi 10 000 so'm",
        send_dm=True,
    )

    assert dm_sent is True
    assert posted is True
    poller.client.reply_to_comment.assert_called_once_with(
        "m1",
        "c1",
        COMMENT_PRICE_REPLY,
        "tester",
    )


@patch.object(InstagramPoller, "_deliver_comment_dm", return_value=False)
def test_post_comment_reply_failure_when_dm_not_sent(mock_dm):
    poller = InstagramPoller()
    poller.client = MagicMock()

    _, posted = poller._post_comment_reply(
        _comment_item(),
        public_reply=COMMENT_PRICE_REPLY,
        dm_reply="Mahsulot narxi 10 000 so'm",
        send_dm=True,
    )

    assert posted is True
    poller.client.reply_to_comment.assert_called_once_with(
        "m1",
        "c1",
        COMMENT_DM_FAILED_REPLY,
        "tester",
    )


@patch.object(InstagramPoller, "_try_send_dm")
def test_duplicate_private_reply_treated_as_success(mock_send_dm):
    poller = InstagramPoller()
    poller.client = MagicMock()
    poller.client.send_private_comment_reply.side_effect = RuntimeError(
        "Zernio API 400: private reply already sent"
    )

    assert poller._try_send_private_reply("m1", "c1", "salom", "u1") is True
    mock_send_dm.assert_not_called()


def test_is_duplicate_private_reply_error():
    assert InstagramPoller._is_duplicate_private_reply_error(
        RuntimeError("duplicate private reply")
    )
    assert not InstagramPoller._is_duplicate_private_reply_error(
        RuntimeError("network timeout")
    )


@patch.object(InstagramPoller, "_deliver_comment_dm", return_value=True)
def test_post_comment_reply_without_dm_uses_public_text(mock_dm):
    poller = InstagramPoller()
    poller.client = MagicMock()

    _, posted = poller._post_comment_reply(
        _comment_item(),
        public_reply=COMMENT_INFO_REPLY,
        send_dm=False,
    )

    assert posted is True
    mock_dm.assert_not_called()
    poller.client.reply_to_comment.assert_called_once_with(
        "m1",
        "c1",
        COMMENT_INFO_REPLY,
        "tester",
    )
