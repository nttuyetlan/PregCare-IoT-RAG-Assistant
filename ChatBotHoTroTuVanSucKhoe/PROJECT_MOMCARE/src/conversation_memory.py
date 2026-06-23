"""
src/conversation_memory.py — Sliding Window Conversation Memory

PURPOSE:
    Maintains a fixed-size sliding window of conversation turns.
    Limited to 3 turns (configurable) to prevent RAM overflow on
    Orange Pi 5 while providing enough context for query rewriting.

ARCHITECTURE DECISIONS:
    - Hard limit of N turns (not tokens) — simpler and predictable
    - Stores both user and assistant messages
    - Thread-safe via collections.deque with maxlen
    - No persistence — memory is ephemeral per session
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Literal

from src.config import get_settings


@dataclass
class Message:
    """A single conversation turn."""
    role: Literal["user", "assistant"]
    content: str


class ConversationMemory:
    """
    Sliding window memory for conversation context.

    Keeps the last N turns (user + assistant pairs) to provide
    context for query rewriting without overflowing RAM.

    The window size is deliberately small (default=3) because:
    1. Edge device RAM is limited
    2. Medical queries are usually self-contained
    3. Qwen 1.5B has limited context window
    """

    def __init__(self, window_size: int | None = None):
        """
        Args:
            window_size: Max number of turn pairs to keep.
                         Defaults to config.memory_window_size (3).
        """
        if window_size is None:
            window_size = get_settings().memory_window_size

        # maxlen = window_size * 2 because each turn has user + assistant
        self._history: deque[Message] = deque(maxlen=window_size * 2)
        self._window_size = window_size

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation history."""
        self._history.append(Message(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation history."""
        self._history.append(Message(role="assistant", content=content))

    def get_history_text(self) -> str:
        """
        Format conversation history as plain text for prompt injection.

        Returns:
            Formatted history string like:
            "Mẹ: ...\\nMầm Nhỏ: ...\\nMẹ: ..."
        """
        if not self._history:
            return ""

        lines = []
        for msg in self._history:
            prefix = "Mẹ" if msg.role == "user" else "Mầm Nhỏ"
            lines.append(f"{prefix}: {msg.content}")

        return "\n".join(lines)

    def get_messages(self) -> list[Message]:
        """Return a copy of current message history."""
        return list(self._history)

    def clear(self) -> None:
        """Clear all conversation history (e.g., on session reset)."""
        self._history.clear()

    @property
    def turn_count(self) -> int:
        """Number of user messages in history."""
        return sum(1 for m in self._history if m.role == "user")

    @property
    def is_empty(self) -> bool:
        return len(self._history) == 0

    def __len__(self) -> int:
        return len(self._history)

    def __repr__(self) -> str:
        return (
            f"ConversationMemory(window={self._window_size}, "
            f"messages={len(self._history)})"
        )
