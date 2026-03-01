"""
Gemini AI Client - REST API based (no SDK dependency).
Supports automatic API key failover.
"""

import json
import requests
import frappe
from frappe_ai_architect.config.ai_config import (
    get_all_api_keys,
    get_api_url,
    get_ai_settings,
    is_api_configured,
    MODEL,
)


SYSTEM_PROMPT = """You are an expert Frappe Framework & ERPNext AI System Architect.
You receive natural language commands and return ONLY valid JSON instructions.

CRITICAL RULES:
1. ALWAYS return valid JSON — no markdown, no explanation outside JSON
2. Use exact Frappe field type names
3. For destructive operations, set "requires_confirmation": true
4. Include "backup_required": true for any data-altering operation
5. Field names must be snake_case
6. DocType names must be Title Case with spaces

RESPONSE JSON SCHEMA:
{
    "status": "success" | "clarification_needed" | "error",
    "operation_type": "doctype_crud" | "field_ops" | "data_ops" | "report_ops" | "automation_ops" | "ui_ops" | "permission_ops" | "integration_ops" | "developer_ops" | "analysis",
    "requires_confirmation": true | false,
    "backup_required": true | false,
    "description": "Human-readable description",
    "impact_analysis": "What will be affected",
    "steps": [
        {
            "step_number": 1,
            "action": "action_name",
            "description": "What this step does",
            "params": { ... },
            "reversible": true | false
        }
    ],
    "warnings": [],
    "suggestions": []
}

VALID ACTIONS:
- create_doctype, edit_doctype, delete_doctype, rename_doctype
- add_field, add_fields, remove_field, modify_field, reorder_fields, convert_field_type
- create_child_table, link_doctypes, set_naming_series, set_autoname
- import_data, export_data, bulk_update, cleanup_data, generate_sample_data, migrate_data, add_child_rows
- create_report, create_dashboard, create_chart, create_number_card
- create_workflow, create_email_alert, create_assignment_rule, create_server_script, create_scheduled_job
- create_client_script, create_custom_button, set_field_visibility, create_property_setter
- create_role, set_permission, set_field_permission, set_user_permission
- create_api, create_webhook
- generate_code, generate_fixture, generate_patch, generate_test, run_sql
- explain_doctype, analyze_schema, suggest_improvements

VALID FRAPPE FIELD TYPES:
Data, Link, Select, Table, Int, Float, Currency, Date, Datetime, Time, Text, Small Text, Long Text, Text Editor, HTML Editor, Code, Password, Read Only, Section Break, Column Break, Tab Break, Heading, HTML, Image, Attach, Attach Image, Check, Color, Rating, Geolocation, Barcode, Duration, Icon, Autocomplete, Dynamic Link, Table MultiSelect, Signature, JSON, Phone, Percent

For create_doctype, params must include:
{
    "doctype_name": "Title Case Name",
    "module": "Module Name",
    "fields": [{"fieldname":"snake_case","fieldtype":"Type","label":"Label","reqd":0|1,"options":"","in_list_view":0|1}],
    "permissions": [{"role":"Role","read":1,"write":1,"create":1,"delete":0}]
}

If request is ambiguous, return status "clarification_needed" with questions in "suggestions" array.
"""


def call_gemini(prompt, api_key):
    """
    Call Gemini API with a single key via REST.

    Args:
        prompt: Full prompt text
        api_key: Gemini API key

    Returns:
        tuple: (success: bool, response_text: str or None, error: str or None)
    """
    url = get_api_url(api_key)

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "generationConfig": {
            "temperature": get_ai_settings()["temperature"],
            "maxOutputTokens": get_ai_settings()["max_output_tokens"],
            "responseMimeType": "application/json",
        },
    }

    try:
        response = requests.post(url, json=payload, timeout=60)

        if response.status_code == 200:
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return True, text, None

        elif response.status_code == 429:
            # Rate limit / quota exceeded — failover candidate
            return False, None, "QUOTA_EXCEEDED"

        elif response.status_code == 403:
            return False, None, "API_KEY_INVALID"

        else:
            error_msg = response.text[:200] if response.text else f"HTTP {response.status_code}"
            return False, None, error_msg

    except requests.exceptions.Timeout:
        return False, None, "TIMEOUT"
    except requests.exceptions.ConnectionError:
        return False, None, "CONNECTION_ERROR"
    except Exception as e:
        return False, None, str(e)[:200]


def call_gemini_with_failover(prompt):
    """
    Call Gemini API with automatic failover across multiple keys.

    Tries each configured API key in order. If one fails due to
    quota/rate limit, tries the next key.

    Args:
        prompt: Full prompt text

    Returns:
        tuple: (success: bool, response_text: str or None, error: str or None, key_index: int)
    """
    keys = get_all_api_keys()

    if not keys:
        return False, None, "NO_API_KEY", -1

    last_error = None
    for i, key in enumerate(keys):
        masked_key = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
        frappe.logger().debug(f"AI Architect: Trying API key #{i+1} ({masked_key})")

        success, text, error = call_gemini(prompt, key)

        if success:
            frappe.logger().debug(f"AI Architect: Key #{i+1} succeeded")
            return True, text, None, i

        last_error = error
        frappe.logger().warning(f"AI Architect: Key #{i+1} failed: {error}")

        # Only failover on quota/rate limit/timeout errors
        # For invalid key or other errors, still try next key
        continue

    return False, None, last_error, -1


class GeminiClient:
    """Gemini API client with failover support."""

    def __init__(self):
        self.settings = get_ai_settings()

    def process_command(self, user_command, context=None):
        """Process natural language command → structured JSON plan."""
        parts = []
        if context:
            parts.append(f"SITE CONTEXT:\n{json.dumps(context, indent=2)}")
        parts.append(f"USER COMMAND: {user_command}")
        prompt = "\n\n".join(parts)

        success, text, error, key_idx = call_gemini_with_failover(prompt)

        if not success:
            return self._handle_error(error)

        try:
            result = json.loads(text)
            return result
        except json.JSONDecodeError:
            frappe.log_error(f"Invalid JSON: {(text or '')[:500]}", "AI Architect - JSON Error")
            return {
                "status": "error",
                "description": "AI returned invalid format. Please rephrase your command more clearly.",
                "steps": [],
            }

    def _handle_error(self, error):
        """Convert API error to user-friendly response."""
        error = error or "Unknown error"

        if "NO_API_KEY" in error:
            return {
                "status": "error",
                "description": "No API key configured. Go to AI Architect Settings to add your key.",
                "steps": [],
            }
        elif "QUOTA_EXCEEDED" in error:
            return {
                "status": "error",
                "description": "All API keys exhausted (quota/rate limit). Add more keys in Settings or wait and retry.",
                "steps": [],
            }
        elif "API_KEY_INVALID" in error:
            return {
                "status": "error",
                "description": "API key is invalid. Check your key in AI Architect Settings.",
                "steps": [],
            }
        elif "TIMEOUT" in error:
            return {
                "status": "error",
                "description": "Request timed out. Gemini server may be slow. Try again.",
                "steps": [],
            }
        elif "CONNECTION_ERROR" in error:
            return {
                "status": "error",
                "description": "Cannot connect to Gemini API. Check your internet connection.",
                "steps": [],
            }
        else:
            frappe.log_error(error, "AI Architect - Gemini Error")
            return {
                "status": "error",
                "description": f"Gemini API error: {error[:200]}",
                "steps": [],
            }

    def get_site_context(self):
        """Gather current site context."""
        try:
            custom_doctypes = frappe.get_all(
                "DocType", filters={"custom": 1}, fields=["name", "module"], limit=100
            )
            modules = frappe.get_all("Module Def", filters={"custom": 1}, pluck="name", limit=50)
            return {
                "custom_doctypes": [d["name"] for d in custom_doctypes],
                "custom_modules": modules,
                "frappe_version": frappe.__version__,
            }
        except Exception:
            return {}
