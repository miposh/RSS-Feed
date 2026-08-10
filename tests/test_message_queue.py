"""Tests for the Telegram flood-control queue — no network."""
import asyncio
from datetime import datetime, timedelta

import pytest

from app.services.message_queue import MessageQueue, QueuedMessage


def _noop():
    async def _send():
        return None
    return _send


class TestExtractRetryAfter:
    @pytest.mark.parametrize(
        "message,expected",
        [
            ("Flood control exceeded. Retry in 34 seconds", 34),
            ("Too Many Requests: retry after 12", 12),
            ("RETRY AFTER 7 seconds", 7),
            ("Flood control exceeded", None),
            ("no digits here", None),
        ],
    )
    def test_parses_retry_hint(self, message, expected):
        assert MessageQueue()._extract_retry_after(message) == expected


class TestPriorityOrdering:
    async def test_higher_priority_jumps_the_line(self):
        q = MessageQueue()
        await q.enqueue(1, _noop(), priority=0)
        await q.enqueue(2, _noop(), priority=0)
        await q.enqueue(3, _noop(), priority=5)

        assert [m.chat_id for m in q.queue] == [3, 1, 2]

    async def test_equal_priority_is_fifo(self):
        q = MessageQueue()
        for chat_id in (1, 2, 3):
            await q.enqueue(chat_id, _noop(), priority=0)

        assert [m.chat_id for m in q.queue] == [1, 2, 3]

    async def test_enqueue_counts_toward_stats(self):
        q = MessageQueue()
        await q.enqueue(1, _noop())
        assert q.get_stats() == {
            "queue_size": 1,
            "total_sent": 0,
            "total_failed": 0,
            "total_queued": 1,
        }


class TestPerChatRateLimit:
    def test_allows_under_the_limit(self):
        q = MessageQueue(max_messages_per_chat_per_minute=3)
        for _ in range(2):
            q._track_sent_message(42)
        assert q._can_send_to_chat(42) is True

    def test_blocks_at_the_limit(self):
        q = MessageQueue(max_messages_per_chat_per_minute=3)
        for _ in range(3):
            q._track_sent_message(42)
        assert q._can_send_to_chat(42) is False

    def test_limit_is_per_chat_not_global(self):
        q = MessageQueue(max_messages_per_chat_per_minute=1)
        q._track_sent_message(42)
        assert q._can_send_to_chat(42) is False
        assert q._can_send_to_chat(99) is True

    def test_timestamps_older_than_a_minute_are_forgotten(self):
        q = MessageQueue(max_messages_per_chat_per_minute=2)
        stale = datetime.now() - timedelta(minutes=2)
        q.chat_timestamps[42] = __import__("collections").deque([stale, stale])

        assert q._can_send_to_chat(42) is True
        assert len(q.chat_timestamps[42]) == 0


class TestProcessing:
    async def test_message_is_actually_sent(self):
        q = MessageQueue(global_delay_seconds=0)
        sent = []

        async def send():
            sent.append("ok")

        await q.start()
        try:
            await q.enqueue(1, send)
            await asyncio.wait_for(self._drain(q), timeout=5)
        finally:
            await q.stop()

        assert sent == ["ok"]
        assert q.total_sent == 1
        assert q.total_failed == 0

    async def test_non_flood_failure_is_counted_and_not_retried(self):
        q = MessageQueue(global_delay_seconds=0)
        calls = []

        async def boom():
            calls.append(1)
            raise RuntimeError("chat not found")

        await q.start()
        try:
            await q.enqueue(1, boom)
            await asyncio.wait_for(self._drain(q), timeout=5)
            await asyncio.sleep(0.1)
        finally:
            await q.stop()

        assert calls == [1]
        assert q.total_failed == 1
        assert q.total_sent == 0

    async def test_stop_is_idempotent(self):
        q = MessageQueue()
        await q.start()
        await q.stop()
        await q.stop()

    @staticmethod
    async def _drain(q):
        while q.get_queue_size() > 0:
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.05)


class TestQueuedMessage:
    def test_created_at_defaults_to_now(self):
        msg = QueuedMessage(chat_id=1, send_func=_noop())
        assert isinstance(msg.created_at, datetime)
