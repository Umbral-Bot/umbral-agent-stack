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
    handle_notion_read_page,
    handle_notion_read_database,
    handle_notion_search_databases,
    handle_notion_create_database_page,
    handle_notion_update_page_properties,
    handle_notion_upsert_task,
    handle_notion_update_dashboard,
    handle_notion_create_report_page,
    handle_notion_enrich_bitacora_page,
    handle_notion_upsert_project,
    handle_notion_upsert_deliverable,
    handle_notion_upsert_bridge_item,
)
from .windows import (
    handle_windows_pad_run_flow,
    handle_windows_open_notepad,
    handle_windows_open_url,
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
from .linear import (
    handle_linear_create_issue,
    handle_linear_list_teams,
    handle_linear_update_issue_status,
    handle_linear_list_projects,
    handle_linear_create_project,
    handle_linear_attach_issue_to_project,
    handle_linear_list_project_issues,
    handle_linear_create_project_update,
    handle_linear_publish_agent_stack_followup,
    handle_linear_claim_agent_stack_issue,
    handle_linear_list_agent_stack_issues,
)
from .research import handle_research_web
from .llm import handle_llm_generate
from .composite import handle_composite_research_report
from .make_webhook import handle_make_post_webhook
from .n8n import (
    handle_n8n_list_workflows,
    handle_n8n_get_workflow,
    handle_n8n_create_workflow,
    handle_n8n_update_workflow,
    handle_n8n_post_webhook,
)
from .azure_audio import handle_azure_audio_generate
from .figma import (
    handle_figma_get_file,
    handle_figma_get_node,
    handle_figma_export_image,
    handle_figma_add_comment,
    handle_figma_list_comments,
)
from .document_generator import (
    handle_document_create_word,
    handle_document_create_pdf,
    handle_document_create_presentation,
)
from .granola import (
    handle_granola_capitalize_raw,
    handle_granola_classify_raw,
    handle_granola_create_human_task_from_curated_session,
    handle_granola_promote_operational_slice,
    handle_granola_update_commercial_project_from_curated_session,
    handle_granola_promote_curated_session,
    handle_granola_process_transcript,
    handle_granola_create_followup,
)
from .google_calendar import (
    handle_google_calendar_create_event,
    handle_google_calendar_list_events,
)
from .gmail import (
    handle_gmail_create_draft,
    handle_gmail_list_drafts,
)
from .google_audio import handle_google_audio_generate
from .google_image import handle_google_image_generate
from .browser import (
    handle_browser_navigate,
    handle_browser_click,
    handle_browser_press_key,
    handle_browser_read_page,
    handle_browser_screenshot,
    handle_browser_type_text,
)
from .gui import (
    handle_gui_desktop_status,
    handle_gui_screenshot,
    handle_gui_click,
    handle_gui_type_text,
    handle_gui_hotkey,
    handle_gui_list_windows,
    handle_gui_activate_window,
)
from .tournament import handle_tournament_run
from .rag import (
    handle_rag_ensure_index,
    handle_rag_index,
    handle_rag_search,
    handle_rag_query,
)
from .client_admin import (
    handle_client_register,
    handle_client_revoke,
    handle_client_rotate_key,
    handle_client_list,
    handle_client_usage,
    handle_client_get,
)

# Each handler: (input: dict) -> dict
TASK_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "ping": handle_ping,
    "notion.write_transcript": handle_notion_write_transcript,
    "notion.add_comment": handle_notion_add_comment,
    "notion.poll_comments": handle_notion_poll_comments,
    "notion.read_page": handle_notion_read_page,
    "notion.read_database": handle_notion_read_database,
    "notion.search_databases": handle_notion_search_databases,
    "notion.create_database_page": handle_notion_create_database_page,
    "notion.update_page_properties": handle_notion_update_page_properties,
    "notion.upsert_task": handle_notion_upsert_task,
    "notion.update_dashboard": handle_notion_update_dashboard,
    "windows.pad.run_flow": handle_windows_pad_run_flow,
    "windows.open_notepad": handle_windows_open_notepad,
    "windows.open_url": handle_windows_open_url,
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
    "linear.list_projects": handle_linear_list_projects,
    "linear.create_project": handle_linear_create_project,
    "linear.attach_issue_to_project": handle_linear_attach_issue_to_project,
    "linear.list_project_issues": handle_linear_list_project_issues,
    "linear.create_project_update": handle_linear_create_project_update,
    "linear.publish_agent_stack_followup": handle_linear_publish_agent_stack_followup,
    "linear.claim_agent_stack_issue": handle_linear_claim_agent_stack_issue,
    "linear.list_agent_stack_issues": handle_linear_list_agent_stack_issues,
    "research.web": handle_research_web,
    "llm.generate": handle_llm_generate,
    "composite.research_report": handle_composite_research_report,
    "notion.create_report_page": handle_notion_create_report_page,
    "notion.enrich_bitacora_page": handle_notion_enrich_bitacora_page,
    "notion.upsert_project": handle_notion_upsert_project,
    "notion.upsert_deliverable": handle_notion_upsert_deliverable,
    "notion.upsert_bridge_item": handle_notion_upsert_bridge_item,
    "make.post_webhook": handle_make_post_webhook,
    "n8n.list_workflows": handle_n8n_list_workflows,
    "n8n.get_workflow": handle_n8n_get_workflow,
    "n8n.create_workflow": handle_n8n_create_workflow,
    "n8n.update_workflow": handle_n8n_update_workflow,
    "n8n.post_webhook": handle_n8n_post_webhook,
    "azure.audio.generate": handle_azure_audio_generate,
    "figma.get_file": handle_figma_get_file,
    "figma.get_node": handle_figma_get_node,
    "figma.export_image": handle_figma_export_image,
    "figma.add_comment": handle_figma_add_comment,
    "figma.list_comments": handle_figma_list_comments,
    "document.create_word": handle_document_create_word,
    "document.create_pdf": handle_document_create_pdf,
    "document.create_presentation": handle_document_create_presentation,
    "granola.capitalize_raw": handle_granola_capitalize_raw,
    "granola.classify_raw": handle_granola_classify_raw,
    "granola.create_human_task_from_curated_session": handle_granola_create_human_task_from_curated_session,
    "granola.promote_operational_slice": handle_granola_promote_operational_slice,
    "granola.update_commercial_project_from_curated_session": handle_granola_update_commercial_project_from_curated_session,
    "granola.promote_session_capitalizable": handle_granola_promote_curated_session,
    "granola.promote_curated_session": handle_granola_promote_curated_session,
    "granola.process_transcript": handle_granola_process_transcript,
    "granola.create_followup": handle_granola_create_followup,
    "google.calendar.create_event": handle_google_calendar_create_event,
    "google.calendar.list_events": handle_google_calendar_list_events,
    "gmail.create_draft": handle_gmail_create_draft,
    "gmail.list_drafts": handle_gmail_list_drafts,
    "google.audio.generate": handle_google_audio_generate,
    "google.image.generate": handle_google_image_generate,
    "browser.navigate": handle_browser_navigate,
    "browser.read_page": handle_browser_read_page,
    "browser.screenshot": handle_browser_screenshot,
    "browser.click": handle_browser_click,
    "browser.type_text": handle_browser_type_text,
    "browser.press_key": handle_browser_press_key,
    "gui.desktop_status": handle_gui_desktop_status,
    "gui.screenshot": handle_gui_screenshot,
    "gui.click": handle_gui_click,
    "gui.type_text": handle_gui_type_text,
    "gui.hotkey": handle_gui_hotkey,
    "gui.list_windows": handle_gui_list_windows,
    "gui.activate_window": handle_gui_activate_window,
    "tournament.run": handle_tournament_run,
    "rag.ensure_index": handle_rag_ensure_index,
    "rag.index": handle_rag_index,
    "rag.search": handle_rag_search,
    "rag.query": handle_rag_query,
    "client.register": handle_client_register,
    "client.revoke": handle_client_revoke,
    "client.rotate_key": handle_client_rotate_key,
    "client.list": handle_client_list,
    "client.usage": handle_client_usage,
    "client.get": handle_client_get,
}
