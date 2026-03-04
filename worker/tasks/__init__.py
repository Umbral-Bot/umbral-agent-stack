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
    handle_notion_upsert_task,
    handle_notion_update_dashboard,
)
from .windows import (
    handle_windows_pad_run_flow,
    handle_windows_open_notepad,
    handle_windows_write_worker_token,
    handle_windows_firewall_allow_port,
    handle_windows_start_interactive_worker,
    handle_windows_add_interactive_worker_to_startup,
)
from .windows_fs import (
    handle_windows_fs_ensure_dirs,
    handle_windows_fs_list,
    handle_windows_fs_read_text,
    handle_windows_fs_write_text,
)
from .windows_fs_bin import (
    handle_windows_fs_write_bytes_b64,
)
from .observability import handle_ooda_report, handle_self_eval
from .linear import handle_linear_create_issue, handle_linear_list_teams, handle_linear_update_issue_status
from .research import handle_research_web
from .llm import handle_llm_generate

# Each handler: (input: dict) -> dict
TASK_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "ping": handle_ping,
    "notion.write_transcript": handle_notion_write_transcript,
    "notion.add_comment": handle_notion_add_comment,
    "notion.poll_comments": handle_notion_poll_comments,
    "notion.upsert_task": handle_notion_upsert_task,
    "notion.update_dashboard": handle_notion_update_dashboard,
    "windows.pad.run_flow": handle_windows_pad_run_flow,
    "windows.open_notepad": handle_windows_open_notepad,
    "windows.write_worker_token": handle_windows_write_worker_token,
    "windows.firewall_allow_port": handle_windows_firewall_allow_port,
    "windows.start_interactive_worker": handle_windows_start_interactive_worker,
    "windows.add_interactive_worker_to_startup": handle_windows_add_interactive_worker_to_startup,
    "windows.fs.ensure_dirs": handle_windows_fs_ensure_dirs,
    "windows.fs.list": handle_windows_fs_list,
    "windows.fs.read_text": handle_windows_fs_read_text,
    "windows.fs.write_text": handle_windows_fs_write_text,
    "windows.fs.write_bytes_b64": handle_windows_fs_write_bytes_b64,
    "system.ooda_report": handle_ooda_report,
    "system.self_eval": handle_self_eval,
    "linear.create_issue": handle_linear_create_issue,
    "linear.list_teams": handle_linear_list_teams,
    "linear.update_issue_status": handle_linear_update_issue_status,
    "research.web": handle_research_web,
    "llm.generate": handle_llm_generate,
}
