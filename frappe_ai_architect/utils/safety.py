"""Safety utilities - backup, validation, rollback, permissions."""

import json
import frappe
from frappe.utils import now_datetime, get_datetime_str


class SafetyManager:
    """Ensures all AI operations are safe and reversible."""

    PROTECTED_DOCTYPES = frozenset({
        "User", "Role", "DocType", "Module Def", "System Settings",
        "Website Settings", "Email Account", "Domain", "DefaultValue",
        "Singles", "DocField", "DocPerm", "Communication", "Error Log",
        "Activity Log", "Version", "Comment", "AI Architect Settings", "AI Command Log",
    })

    DESTRUCTIVE_OPERATIONS = frozenset({
        "delete_doctype", "remove_field", "bulk_update", "cleanup_data",
        "delete_records", "rename_doctype", "convert_field_type",
    })

    VALID_FIELD_TYPES = frozenset({
        "Data", "Link", "Select", "Table", "Int", "Float", "Currency",
        "Date", "Datetime", "Time", "Text", "Small Text", "Long Text",
        "Text Editor", "HTML Editor", "Code", "Password", "Read Only",
        "Section Break", "Column Break", "Tab Break", "Heading", "HTML",
        "Image", "Attach", "Attach Image", "Check", "Color", "Rating",
        "Geolocation", "Barcode", "Duration", "Icon", "Autocomplete",
        "Dynamic Link", "Table MultiSelect", "Signature", "JSON",
        "Phone", "Percent",
    })

    @staticmethod
    def check_permissions():
        """Verify user has permission to use AI Architect."""
        allowed = ["System Manager", "Administrator"]
        try:
            if frappe.db.exists("DocType", "AI Architect Settings"):
                settings = frappe.get_single("AI Architect Settings")
                if settings.allowed_roles:
                    allowed = [r.strip() for r in settings.allowed_roles.split("\n") if r.strip()]
        except Exception:
            pass

        user_roles = frappe.get_roles()
        if not any(role in user_roles for role in allowed):
            frappe.throw(
                f"You don't have permission to use AI Architect. Required roles: {', '.join(allowed)}",
                frappe.PermissionError,
            )

    @staticmethod
    def is_protected(doctype_name):
        """Check if DocType is protected from modification."""
        if doctype_name in SafetyManager.PROTECTED_DOCTYPES:
            return True
        if frappe.db.exists("DocType", doctype_name):
            meta = frappe.get_meta(doctype_name)
            if not meta.custom:
                return True
        return False

    @staticmethod
    def validate_ai_response(response):
        """Validate AI response before execution."""
        errors = []
        if not isinstance(response, dict):
            return False, ["Response is not a dictionary"]
        if "status" not in response:
            errors.append("Missing 'status' field")
        if "steps" not in response or not isinstance(response.get("steps"), list):
            errors.append("Missing or invalid 'steps'")

        for i, step in enumerate(response.get("steps", [])):
            if "action" not in step:
                errors.append(f"Step {i+1}: Missing 'action'")
                continue
            params = step.get("params", {})
            dt = params.get("doctype_name") or params.get("doctype")
            if dt and SafetyManager.is_protected(dt):
                errors.append(f"Step {i+1}: Cannot modify protected DocType '{dt}'")
            for field in params.get("fields", []):
                ft = field.get("fieldtype")
                if ft and ft not in SafetyManager.VALID_FIELD_TYPES:
                    errors.append(f"Step {i+1}: Invalid field type '{ft}'")

        return len(errors) == 0, errors

    @staticmethod
    def create_backup(operation_id, target_doctype=None):
        """Create backup snapshot before operation."""
        backup = {
            "operation_id": operation_id,
            "timestamp": get_datetime_str(now_datetime()),
            "user": frappe.session.user,
            "target_doctype": target_doctype,
        }
        if target_doctype and frappe.db.exists("DocType", target_doctype):
            try:
                dt_doc = frappe.get_doc("DocType", target_doctype)
                backup["doctype_schema"] = dt_doc.as_dict()
            except Exception:
                pass

        try:
            if frappe.db.exists("DocType", "AI Command Log"):
                log = frappe.new_doc("AI Command Log")
                log.operation_id = operation_id
                log.backup_data = json.dumps(backup, default=str, indent=2)
                log.status = "Backup Created"
                log.insert(ignore_permissions=True)
                frappe.db.commit()
                return log.name
        except Exception as e:
            frappe.log_error(str(e), "AI Backup Error")
        return None

    @staticmethod
    def rollback(backup_id):
        """Rollback operation from backup."""
        try:
            if not frappe.db.exists("AI Command Log", backup_id):
                return {"status": "error", "message": f"Backup '{backup_id}' not found"}

            log = frappe.get_doc("AI Command Log", backup_id)
            backup = json.loads(log.backup_data)

            if backup.get("doctype_schema"):
                schema = backup["doctype_schema"]
                if frappe.db.exists("DocType", schema.get("name")):
                    dt = frappe.get_doc("DocType", schema["name"])
                    dt.update(schema)
                    dt.save(ignore_permissions=True)
                    frappe.db.commit()

            log.status = "Rolled Back"
            log.save(ignore_permissions=True)
            frappe.db.commit()
            return {"status": "success", "message": "Rollback successful"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
