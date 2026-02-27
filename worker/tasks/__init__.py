"""
Umbral Worker — Task Registry

Collects all task handlers into a single dispatch dict.
Import TASK_HANDLERS from here in app.py.
"""

from typing import Any, Callable, Dict

from .ping import handle_ping
from .notion import (
    handle_notion_write_transcript,
    handle_notion_add_comment,
    handle_notion_poll_comments,
)

# Each handler: (input: dict) -> dict
TASK_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "ping": handle_ping,
    "notion.write_transcript": handle_notion_write_transcript,
    "notion.add_comment": handle_notion_add_comment,
    "notion.poll_comments": handle_notion_poll_comments,
}
