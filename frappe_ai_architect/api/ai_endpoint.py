"""
AI Architect API Endpoints - Main entry point for all operations.
"""

import json
import frappe
from frappe_ai_architect.utils.gemini_client import GeminiClient
from frappe_ai_architect.utils.safety import SafetyManager
from frappe_ai_architect.config.ai_config import is_api_configured
from frappe_ai_architect.handlers.doctype_handler import DocTypeHandler
from frappe_ai_architect.handlers.field_handler import FieldHandler
from frappe_ai_architect.handlers.all_handlers import (
    DataHandler, ReportHandler, AutomationHandler, UIHandler,
    PermissionHandler, IntegrationHandler, DeveloperHandler,
)

# ── Handler Registry ──────────────────────────────────────────────────────────
HANDLER_MAP = {
    "doctype_crud": DocTypeHandler,
    "field_ops": FieldHandler,
    "data_ops": DataHandler,
    "report_ops": ReportHandler,
    "automation_ops": AutomationHandler,
    "ui_ops": UIHandler,
    "permission_ops": PermissionHandler,
    "integration_ops": IntegrationHandler,
    "developer_ops": DeveloperHandler,
    "analysis": DeveloperHandler,
}

ACTION_TO_TYPE = {
    "create_doctype": "doctype_crud", "edit_doctype": "doctype_crud",
    "delete_doctype": "doctype_crud", "rename_doctype": "doctype_crud",
    "create_child_table": "doctype_crud", "link_doctypes": "doctype_crud",
    "set_naming_series": "doctype_crud", "set_autoname": "doctype_crud",
    "add_field": "field_ops", "add_fields": "field_ops",
    "remove_field": "field_ops", "modify_field": "field_ops",
    "reorder_fields": "field_ops", "convert_field_type": "field_ops",
    "import_data": "data_ops", "export_data": "data_ops",
    "bulk_update": "data_ops", "cleanup_data": "data_ops",
    "generate_sample_data": "data_ops", "migrate_data": "data_ops",
    "add_child_rows": "data_ops",
    "create_report": "report_ops", "create_dashboard": "report_ops",
    "create_chart": "report_ops", "create_number_card": "report_ops",
    "create_workflow": "automation_ops", "create_email_alert": "automation_ops",
    "create_assignment_rule": "automation_ops", "create_server_script": "automation_ops",
    "create_scheduled_job": "automation_ops",
    "create_client_script": "ui_ops", "create_custom_button": "ui_ops",
    "set_field_visibility": "ui_ops", "create_property_setter": "ui_ops",
    "create_role": "permission_ops", "set_permission": "permission_ops",
    "set_field_permission": "permission_ops", "set_user_permission": "permission_ops",
    "create_api": "integration_ops", "create_webhook": "integration_ops",
    "generate_code": "developer_ops", "generate_fixture": "developer_ops",
    "generate_patch": "developer_ops", "generate_test": "developer_ops",
    "run_sql": "developer_ops", "explain_doctype": "developer_ops",
    "analyze_schema": "developer_ops", "suggest_improvements": "developer_ops",
}


@frappe.whitelist()
def process_command(command, confirmed=False):
    """Main entry point — processes natural language command."""
    SafetyManager.check_permissions()

    if isinstance(confirmed, str):
        confirmed = confirmed.lower() in ("true", "1", "yes")

    # Check if API is configured
    if not is_api_configured():
        return {
            "status": "setup_required",
            "message": "🔧 Gemini API key is not configured yet.",
            "setup_url": "/app/ai-architect-settings",
        }

    # Get AI plan from Gemini
    try:
        client = GeminiClient()
        context = client.get_site_context()
        ai_plan = client.process_command(command, context=context)
    except Exception as e:
        frappe.log_error(str(e), "AI Architect Error")
        return {"status": "error", "message": f"AI error: {str(e)[:200]}"}

    if ai_plan.get("status") == "error":
        return ai_plan
    if ai_plan.get("status") == "clarification_needed":
        return {"status": "clarification_needed", "message": ai_plan.get("description", ""),
                "questions": ai_plan.get("questions", []), "suggestions": ai_plan.get("suggestions", [])}

    # Validate
    is_valid, errors = SafetyManager.validate_ai_response(ai_plan)
    if not is_valid:
        return {"status": "validation_error", "message": "Invalid plan", "errors": errors}

    # Confirmation check
    if ai_plan.get("requires_confirmation") and not confirmed:
        return {
            "status": "confirmation_required",
            "plan": {
                "description": ai_plan.get("description"),
                "impact": ai_plan.get("impact_analysis"),
                "warnings": ai_plan.get("warnings", []),
                "steps": [{"step": s.get("step_number"), "action": s.get("action"),
                           "description": s.get("description"), "reversible": s.get("reversible", True)}
                          for s in ai_plan.get("steps", [])],
            },
            "message": "⚠️ Review and confirm this operation.",
        }

    # Backup
    backup_id = None
    if ai_plan.get("backup_required"):
        first = ai_plan["steps"][0] if ai_plan.get("steps") else {}
        dt = first.get("params", {}).get("doctype_name") or first.get("params", {}).get("doctype")
        backup_id = SafetyManager.create_backup(frappe.generate_hash(length=10), dt)

    # Execute steps
    results = []
    for step in ai_plan.get("steps", []):
        action = step.get("action")
        op_type = ACTION_TO_TYPE.get(action) or ai_plan.get("operation_type")
        handler_class = HANDLER_MAP.get(op_type)

        if not handler_class:
            results.append({"step": step.get("step_number"), "action": action,
                           "status": "error", "error": f"No handler for '{action}'"})
            continue
        try:
            handler = handler_class()
            result = handler.execute_step(step)
            results.append({"step": step.get("step_number"), "action": action,
                           "status": "success", "result": result})
        except Exception as e:
            frappe.log_error(str(e), f"AI Step {step.get('step_number')} Error")
            results.append({"step": step.get("step_number"), "action": action,
                           "status": "error", "error": str(e)})
            break

    # Log command
    _log_command(command, ai_plan, results)
    frappe.db.commit()

    return {
        "status": "success" if all(r["status"] == "success" for r in results) else "partial",
        "description": ai_plan.get("description", ""),
        "results": results,
        "backup_id": backup_id,
        "suggestions": ai_plan.get("suggestions", []),
        "warnings": ai_plan.get("warnings", []),
    }


@frappe.whitelist()
def check_setup():
    """Check if AI Architect is properly configured."""
    result = {"api_configured": is_api_configured(), "sdk_installed": False, "setup_complete": False}
    try:
        import google.generativeai
        result["sdk_installed"] = True
    except ImportError:
        pass

    try:
        if frappe.db.exists("DocType", "AI Architect Settings"):
            settings = frappe.get_single("AI Architect Settings")
            result["setup_complete"] = bool(settings.is_setup_complete)
    except Exception:
        pass

    return result


@frappe.whitelist()
def get_site_info():
    """Get site info for UI."""
    SafetyManager.check_permissions()
    return {
        "frappe_version": frappe.__version__,
        "site_name": frappe.local.site,
        "user": frappe.session.user,
        "custom_doctypes": frappe.get_all("DocType", filters={"custom": 1},
                                           fields=["name", "module"], limit=500),
        "custom_modules": frappe.get_all("Module Def", filters={"custom": 1}, pluck="name"),
        "installed_apps": frappe.get_installed_apps(),
    }


@frappe.whitelist()
def rollback(backup_id):
    """Rollback an operation."""
    SafetyManager.check_permissions()
    return SafetyManager.rollback(backup_id)


@frappe.whitelist()
def get_command_history(limit=20):
    """Get recent command history."""
    SafetyManager.check_permissions()
    if not frappe.db.exists("DocType", "AI Command Log"):
        return []
    return frappe.get_all("AI Command Log",
                           fields=["name", "command", "status", "operation_type", "creation"],
                           order_by="creation desc", limit_page_length=int(limit))


def _log_command(command, ai_plan, results):
    """Log command to audit trail."""
    try:
        if frappe.db.exists("DocType", "AI Command Log"):
            log = frappe.new_doc("AI Command Log")
            log.command = (command or "")[:500]
            log.operation_type = ai_plan.get("operation_type", "")
            log.ai_response = json.dumps(ai_plan, default=str)[:10000]
            log.execution_result = json.dumps(results, default=str)[:10000]
            log.status = "Success" if all(r.get("status") == "success" for r in results) else "Failed"
            log.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(str(e), "AI Logging Error")
