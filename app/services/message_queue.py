"""
Message queue manager for controlling Telegram API flood limits.

Telegram API limits:
- 30 messages per second to different users
- 20 messages per minute to the same group/channel
- MediaGroup counts as 1 message regardless of media count
"""

import asyncio
import logging
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine, Deque, Optional

logger = logging.getLogger(__name__)


@dataclass
class QueuedMessage:
    """Represents a message in the queue."""
    chat_id: int
    send_func: Callable[[], Coroutine[Any, Any, None]]
    priority: int = 0  # Higher priority = sent first
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class MessageQueue:
    """
    Global message queue with Telegram API flood control.

    This ensures all messages across all workers respect Telegram's rate limits:
    - Max 20 messages per minute per chat
    - Global delay between messages to avoid hitting API limits
    """

    def __init__(
        self,
        max_messages_per_chat_per_minute: int = 18,  # Conservative limit (Telegram allows 20)
        global_delay_seconds: float = 2.5,  # Delay between any messages
        retry_delay_seconds: float = 15.0,  # Delay before retrying after flood error
    ):
        self.max_messages_per_chat_per_minute = max_messages_per_chat_per_minute
        self.global_delay_seconds = global_delay_seconds
        self.retry_delay_seconds = retry_delay_seconds

        # Global message queue (all chats)
        self.queue: Deque[QueuedMessage] = deque()

        # Per-chat tracking for rate limiting
        self.chat_timestamps: dict[int, Deque[datetime]] = {}

        # Queue processing
        self.running = False
        self.processor_task: Optional[asyncio.Task] = None
        self.queue_lock = asyncio.Lock()

        # Statistics
        self.total_sent = 0
        self.total_failed = 0
        self.total_queued = 0

    async def start(self) -> None:
        """Start the queue processor."""
        if self.running:
            logger.warning("MessageQueue is already running")
            return

        self.running = True
        self.processor_task = asyncio.create_task(self._process_queue())
        logger.info(
            f"MessageQueue started (max {self.max_messages_per_chat_per_minute} msg/min per chat, "
            f"{self.global_delay_seconds}s global delay)"
        )

    async def stop(self) -> None:
        """Stop the queue processor."""
        if not self.running:
            return

        self.running = False

        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass

        pending_count = len(self.queue)
        if pending_count > 0:
            logger.warning(f"MessageQueue stopped with {pending_count} pending messages")

        logger.info(
            f"MessageQueue stopped (sent: {self.total_sent}, failed: {self.total_failed}, "
            f"pending: {pending_count})"
        )

    async def enqueue(
        self,
        chat_id: int,
        send_func: Callable[[], Coroutine[Any, Any, None]],
        priority: int = 0
    ) -> None:
        """
        Add a message to the queue.

        Args:
            chat_id: Telegram chat/channel ID
            send_func: Async function that sends the message (takes no args)
            priority: Message priority (higher = sent first)
        """
        async with self.queue_lock:
            message = QueuedMessage(
                chat_id=chat_id,
                send_func=send_func,
                priority=priority
            )

            # Insert based on priority (higher priority first)
            inserted = False
            for i, existing in enumerate(self.queue):
                if priority > existing.priority:
                    self.queue.insert(i, message)
                    inserted = True
                    break

            if not inserted:
                self.queue.append(message)

            self.total_queued += 1

            logger.debug(
                f"Enqueued message for chat {chat_id} (priority={priority}, queue_size={len(self.queue)})"
            )

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self.queue)

    def get_stats(self) -> dict:
        """Get queue statistics."""
        return {
            "queue_size": len(self.queue),
            "total_sent": self.total_sent,
            "total_failed": self.total_failed,
            "total_queued": self.total_queued,
        }

    async def _process_queue(self) -> None:
        """Process messages from the queue."""
        while self.running:
            try:
                # Get next message
                message = await self._get_next_message()

                if message is None:
                    # Queue is empty, wait a bit
                    await asyncio.sleep(0.5)
                    continue

                # Check if we can send to this chat (rate limiting)
                if not self._can_send_to_chat(message.chat_id):
                    # Put message back in queue
                    async with self.queue_lock:
                        self.queue.appendleft(message)

                    logger.debug(
                        f"Rate limit for chat {message.chat_id}, waiting {self.retry_delay_seconds}s..."
                    )
                    await asyncio.sleep(self.retry_delay_seconds)
                    continue

                # Send the message
                try:
                    await message.send_func()
                    self._track_sent_message(message.chat_id)
                    self.total_sent += 1

                    # Wait before processing next message (global rate limiting)
                    await asyncio.sleep(self.global_delay_seconds)

                except Exception as e:
                    error_str = str(e).lower()

                    # Check if it's a flood control error
                    if "flood" in error_str or "too many requests" in error_str:
                        # Extract retry time if available
                        retry_after = self._extract_retry_after(str(e))

                        if retry_after:
                            logger.warning(
                                f"Flood control for chat {message.chat_id}: "
                                f"retry after {retry_after}s. Requeueing message..."
                            )

                            # Put message back in queue with lower priority
                            async with self.queue_lock:
                                message.priority = max(message.priority - 1, -10)
                                self.queue.append(message)

                            # Wait the specified time
                            await asyncio.sleep(retry_after)
                        else:
                            logger.error(
                                f"Flood control error for chat {message.chat_id} (no retry time): {e}"
                            )
                            self.total_failed += 1
                    else:
                        # Other error, don't retry
                        logger.error(f"Error sending message to chat {message.chat_id}: {e}")
                        self.total_failed += 1

            except Exception as e:
                logger.error(f"Error processing queue: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _get_next_message(self) -> Optional[QueuedMessage]:
        """Get next message from queue (thread-safe)."""
        async with self.queue_lock:
            if self.queue:
                return self.queue.popleft()
            return None

    def _can_send_to_chat(self, chat_id: int) -> bool:
        """Check if we can send a message to this chat (rate limiting)."""
        now = datetime.now()

        # Initialize tracking for this chat if needed
        if chat_id not in self.chat_timestamps:
            self.chat_timestamps[chat_id] = deque()

        timestamps = self.chat_timestamps[chat_id]

        # Remove timestamps older than 1 minute
        while timestamps and (now - timestamps[0]) > timedelta(minutes=1):
            timestamps.popleft()

        # Check if we're under the limit
        return len(timestamps) < self.max_messages_per_chat_per_minute

    def _track_sent_message(self, chat_id: int) -> None:
        """Track that a message was sent to a chat."""
        if chat_id not in self.chat_timestamps:
            self.chat_timestamps[chat_id] = deque()

        self.chat_timestamps[chat_id].append(datetime.now())

    def _extract_retry_after(self, error_message: str) -> Optional[int]:
        """
        Extract retry_after seconds from flood control error message.

        Example: "Flood control exceeded. Retry in 34 seconds"
        """
        # Try to find "retry after X" or "retry in X"
        patterns = [
            r"retry\s+after\s+(\d+)",
            r"retry\s+in\s+(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, error_message.lower())
            if match:
                return int(match.group(1))

        return None


# Global singleton instance
_global_queue: Optional[MessageQueue] = None


def get_message_queue() -> MessageQueue:
    """Get the global message queue instance."""
    global _global_queue
    if _global_queue is None:
        _global_queue = MessageQueue()
    return _global_queue


async def start_message_queue() -> None:
    """Start the global message queue."""
    queue = get_message_queue()
    await queue.start()


async def stop_message_queue() -> None:
    """Stop the global message queue."""
    queue = get_message_queue()
    await queue.stop()
