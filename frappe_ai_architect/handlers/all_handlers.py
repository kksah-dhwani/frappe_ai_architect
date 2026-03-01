"""
Combined Handlers - Data, Report, Automation, UI, Permission, Integration, Developer.
Each class handles one category of operations.
"""

import json
import frappe
from frappe.utils import today, add_days


# ══════════════════════════════════════════════════════════════════════════════
# DATA HANDLER
# ══════════════════════════════════════════════════════════════════════════════

class DataHandler:
    def execute_step(self, step):
        actions = {
            "import_data": self.import_data, "export_data": self.export_data,
            "bulk_update": self.bulk_update, "cleanup_data": self.cleanup_data,
            "generate_sample_data": self.generate_sample_data,
            "migrate_data": self.migrate_data, "add_child_rows": self.add_child_rows,
        }
        handler = actions.get(step.get("action"))
        if not handler:
            frappe.throw(f"Unknown data action: {step.get('action')}")
        return handler(step.get("params", {}))

    def import_data(self, p):
        dt = p.get("doctype")
        imported, errors = 0, []
        for row in p.get("data", []):
            try:
                doc = frappe.new_doc(dt)
                doc.update(row)
                doc.insert(ignore_permissions=True)
                imported += 1
            except Exception as e:
                errors.append(str(e)[:100])
        frappe.db.commit()
        return {"message": f"Imported {imported} records, {len(errors)} errors"}

    def export_data(self, p):
        data = frappe.get_all(p.get("doctype"), fields=p.get("fields", ["*"]),
                              filters=p.get("filters", {}), limit_page_length=p.get("limit", 1000))
        return {"count": len(data), "data": data, "message": f"Exported {len(data)} records"}

    def bulk_update(self, p):
        records = frappe.get_all(p.get("doctype"), filters=p.get("filters", {}),
                                  pluck="name", limit=p.get("limit", 500))
        for name in records:
            frappe.db.set_value(p.get("doctype"), name, p.get("updates", {}))
        frappe.db.commit()
        return {"message": f"Updated {len(records)} records"}

    def cleanup_data(self, p):
        dt = p.get("doctype")
        results = {}
        ops = p.get("operations", [])
        if "remove_duplicates" in ops:
            key = p.get("duplicate_key", "name")
            dups = frappe.db.sql(f"SELECT `{key}`, COUNT(*) c FROM `tab{dt}` GROUP BY `{key}` HAVING c > 1", as_dict=1)
            removed = 0
            for d in dups:
                recs = frappe.get_all(dt, filters={key: d[key]}, order_by="creation asc", pluck="name")
                for n in recs[1:]:
                    frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
                    removed += 1
            results["duplicates_removed"] = removed
        if "trim_whitespace" in ops:
            meta = frappe.get_meta(dt)
            for f in meta.fields:
                if f.fieldtype in ("Data", "Small Text", "Text"):
                    frappe.db.sql(f"UPDATE `tab{dt}` SET `{f.fieldname}`=TRIM(`{f.fieldname}`) WHERE `{f.fieldname}` != TRIM(`{f.fieldname}`)")
            results["trimmed"] = True
        frappe.db.commit()
        return {"message": f"Cleanup done on '{dt}'", "results": results}

    def generate_sample_data(self, p):
        import random
        dt = p.get("doctype")
        count = p.get("count", 10)
        meta = frappe.get_meta(dt)
        created = 0
        for i in range(count):
            doc = frappe.new_doc(dt)
            for f in meta.fields:
                if f.fieldtype in ("Section Break", "Column Break", "Tab Break", "HTML"):
                    continue
                if f.fieldtype == "Data" and f.reqd:
                    doc.set(f.fieldname, f"Sample {f.label or f.fieldname} {i+1}")
                elif f.fieldtype == "Int":
                    doc.set(f.fieldname, i + 1)
                elif f.fieldtype in ("Float", "Currency"):
                    doc.set(f.fieldname, round((i+1) * 100.5, 2))
                elif f.fieldtype == "Check":
                    doc.set(f.fieldname, i % 2)
                elif f.fieldtype == "Select" and f.options:
                    opts = [o for o in f.options.split("\n") if o.strip()]
                    if opts:
                        doc.set(f.fieldname, random.choice(opts))
                elif f.fieldtype == "Date":
                    doc.set(f.fieldname, add_days(today(), i))
            try:
                doc.insert(ignore_permissions=True)
                created += 1
            except Exception:
                pass
        frappe.db.commit()
        return {"message": f"Created {created} sample records in '{dt}'"}

    def migrate_data(self, p):
        mapping = p.get("field_mapping", {})
        data = frappe.get_all(p.get("source_doctype"), fields=list(mapping.keys()) or ["*"],
                               filters=p.get("filters", {}), limit_page_length=p.get("limit", 1000))
        migrated = 0
        for row in data:
            try:
                doc = frappe.new_doc(p.get("target_doctype"))
                for old, new in mapping.items():
                    if old in row:
                        doc.set(new, row[old])
                doc.insert(ignore_permissions=True)
                migrated += 1
            except Exception:
                pass
        frappe.db.commit()
        return {"message": f"Migrated {migrated} records"}

    def add_child_rows(self, p):
        doc = frappe.get_doc(p.get("parent_doctype"), p.get("parent_name"))
        for row in p.get("rows", []):
            doc.append(p.get("child_fieldname"), row)
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return {"message": f"Added {len(p.get('rows', []))} child rows"}


# ══════════════════════════════════════════════════════════════════════════════
# REPORT HANDLER
# ══════════════════════════════════════════════════════════════════════════════

class ReportHandler:
    def execute_step(self, step):
        actions = {
            "create_report": self.create_report, "create_dashboard": self.create_dashboard,
            "create_chart": self.create_chart, "create_number_card": self.create_number_card,
        }
        handler = actions.get(step.get("action"))
        if not handler:
            frappe.throw(f"Unknown report action: {step.get('action')}")
        return handler(step.get("params", {}))

    def create_report(self, p):
        r = frappe.new_doc("Report")
        r.report_name = p.get("report_name")
        r.ref_doctype = p.get("doctype")
        r.report_type = p.get("report_type", "Script Report")
        r.module = p.get("module", "Custom")
        r.is_standard = "No"
        if p.get("query"): r.query = p["query"]
        if p.get("script"): r.report_script = p["script"]
        r.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"message": f"Report '{p.get('report_name')}' created"}

    def create_dashboard(self, p):
        d = frappe.new_doc("Dashboard")
        d.dashboard_name = p.get("dashboard_name")
        d.module = p.get("module", "Custom")
        d.is_standard = 0
        for c in p.get("charts", []):
            d.append("charts", {"chart": c.get("chart_name"), "width": c.get("width", "Full")})
        d.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"message": f"Dashboard '{p.get('dashboard_name')}' created"}

    def create_chart(self, p):
        c = frappe.new_doc("Dashboard Chart")
        c.chart_name = p.get("chart_name")
        c.chart_type = p.get("chart_type", "Count")
        c.document_type = p.get("doctype")
        c.based_on = p.get("based_on", "creation")
        c.timespan = p.get("timespan", "Last Year")
        c.time_interval = p.get("time_interval", "Monthly")
        c.type = p.get("type", "Bar")
        c.color = p.get("color", "#6C5CE7")
        c.is_standard = 0
        c.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"message": f"Chart '{p.get('chart_name')}' created"}

    def create_number_card(self, p):
        c = frappe.new_doc("Number Card")
        c.name1 = p.get("card_name")
        c.label = p.get("label", p.get("card_name"))
        c.document_type = p.get("doctype")
        c.function = p.get("function", "Count")
        c.is_standard = 0
        c.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"message": f"Number Card '{p.get('card_name')}' created"}


# ══════════════════════════════════════════════════════════════════════════════
# AUTOMATION HANDLER
# ══════════════════════════════════════════════════════════════════════════════

class AutomationHandler:
    def execute_step(self, step):
        actions = {
            "create_workflow": self.create_workflow, "create_email_alert": self.create_email_alert,
            "create_assignment_rule": self.create_assignment_rule,
            "create_server_script": self.create_server_script,
            "create_scheduled_job": self.create_scheduled_job,
        }
        handler = actions.get(step.get("action"))
        if not handler:
            frappe.throw(f"Unknown automation action: {step.get('action')}")
        return handler(step.get("params", {}))

    def create_workflow(self, p):
        wf = frappe.new_doc("Workflow")
        wf.workflow_name = p.get("workflow_name")
        wf.document_type = p.get("doctype")
        wf.is_active = p.get("is_active", 1)
        wf.workflow_state_field = p.get("state_field", "workflow_state")
        for s in p.get("states", []):
            wf.append("states", {"state": s.get("state"), "doc_status": s.get("doc_status", 0),
                                   "allow_edit": s.get("allow_edit", "System Manager")})
        for t in p.get("transitions", []):
            wf.append("transitions", {"state": t.get("state"), "action": t.get("action"),
                                        "next_state": t.get("next_state"),
                                        "allowed": t.get("allowed", "System Manager"),
                                        "allow_self_approval": t.get("allow_self_approval", 1)})
        wf.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"message": f"Workflow '{wf.workflow_name}' created with {len(wf.states)} states"}

    def create_email_alert(self, p):
        n = frappe.new_doc("Notification")
        n.name1 = p.get("name")
        n.subject = p.get("subject", "")
        n.document_type = p.get("doctype")
        n.event = p.get("event", "Value Change")
        n.channel = p.get("channel", "Email")
        n.message = p.get("message", "")
        n.enabled = 1
        for r in p.get("recipients", []):
            n.append("recipients", {"receiver_by_document_field": r.get("field"), "receiver_by_role": r.get("role")})
        n.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"message": "Email notification created"}

    def create_assignment_rule(self, p):
        r = frappe.new_doc("Assignment Rule")
        r.name1 = p.get("name")
        r.document_type = p.get("doctype")
        r.assign_condition = p.get("condition", "")
        r.disabled = 0
        r.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"message": "Assignment rule created"}

    def create_server_script(self, p):
        ss = frappe.new_doc("Server Script")
        ss.name1 = p.get("name")
        ss.script_type = p.get("script_type", "DocType Event")
        ss.reference_doctype = p.get("doctype")
        ss.doctype_event = p.get("event", "Before Save")
        ss.script = p.get("script", "")
        ss.disabled = 0
        ss.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"message": f"Server Script created for '{p.get('doctype')}'"}

    def create_scheduled_job(self, p):
        ss = frappe.new_doc("Server Script")
        ss.name1 = p.get("name")
        ss.script_type = "Scheduler Event"
        ss.event_frequency = p.get("frequency", "Daily")
        ss.script = p.get("script", "")
        ss.disabled = 0
        ss.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"message": f"Scheduled job created ({p.get('frequency', 'Daily')})"}


# ══════════════════════════════════════════════════════════════════════════════
# UI HANDLER
# ══════════════════════════════════════════════════════════════════════════════

class UIHandler:
    def execute_step(self, step):
        actions = {
            "create_client_script": self.create_client_script,
            "create_custom_button": self.create_custom_button,
            "set_field_visibility": self.set_field_visibility,
            "create_property_setter": self.create_property_setter,
        }
        handler = actions.get(step.get("action"))
        if not handler:
            frappe.throw(f"Unknown UI action: {step.get('action')}")
        return handler(step.get("params", {}))

    def create_client_script(self, p):
        cs = frappe.new_doc("Client Script")
        cs.name1 = p.get("name", f"{p.get('doctype')} Script")
        cs.dt = p.get("doctype")
        cs.script = p.get("script", "")
        cs.enabled = 1
        cs.view = p.get("view", "Form")
        cs.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"message": f"Client Script created for '{p.get('doctype')}'"}

    def create_custom_button(self, p):
        dt = p.get("doctype")
        label = p.get("button_label", "Action")
        action = p.get("action_script", f"frappe.msgprint('{label}')")
        script = f"frappe.ui.form.on('{dt}', {{refresh: function(frm) {{ frm.add_custom_button(__('{label}'), function() {{ {action} }}); }} }});"
        return self.create_client_script({"name": f"{dt} - {label}", "doctype": dt, "script": script})

    def set_field_visibility(self, p):
        dt_name = p.get("doctype")
        dt = frappe.get_doc("DocType", dt_name)
        modified = []
        for rule in p.get("rules", []):
            for f in dt.fields:
                if f.fieldname == rule.get("fieldname"):
                    for k in ("depends_on", "hidden", "read_only_depends_on", "mandatory_depends_on"):
                        if k in rule:
                            setattr(f, k, rule[k])
                    modified.append(f.fieldname)
        dt.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype=dt_name)
        return {"message": f"Visibility updated for {len(modified)} fields"}

    def create_property_setter(self, p):
        ps = frappe.new_doc("Property Setter")
        ps.doctype_or_field = "DocField" if p.get("fieldname") else "DocType"
        ps.doc_type = p.get("doctype")
        ps.field_name = p.get("fieldname")
        ps.property = p.get("property")
        ps.value = p.get("value")
        ps.property_type = p.get("property_type", "Small Text")
        ps.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"message": f"Property '{p.get('property')}' set"}


# ══════════════════════════════════════════════════════════════════════════════
# PERMISSION HANDLER
# ══════════════════════════════════════════════════════════════════════════════

class PermissionHandler:
    def execute_step(self, step):
        actions = {
            "create_role": self.create_role, "set_permission": self.set_permission,
            "set_field_permission": self.set_field_permission,
            "set_user_permission": self.set_user_permission,
        }
        handler = actions.get(step.get("action"))
        if not handler:
            frappe.throw(f"Unknown permission action: {step.get('action')}")
        return handler(step.get("params", {}))

    def create_role(self, p):
        name = p.get("role_name")
        if frappe.db.exists("Role", name):
            return {"message": f"Role '{name}' already exists"}
        frappe.get_doc({"doctype": "Role", "role_name": name, "desk_access": p.get("desk_access", 1),
                        "is_custom": 1}).insert(ignore_permissions=True)
        frappe.db.commit()
        return {"message": f"Role '{name}' created"}

    def set_permission(self, p):
        dt = frappe.get_doc("DocType", p.get("doctype"))
        role = p.get("role")
        existing = next((x for x in dt.permissions if x.role == role and x.permlevel == p.get("permlevel", 0)), None)
        perm_keys = ["read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "print", "email", "share"]
        if existing:
            for k in perm_keys:
                if k in p: setattr(existing, k, p[k])
        else:
            pdata = {"role": role, "permlevel": p.get("permlevel", 0)}
            for k in perm_keys:
                pdata[k] = p.get(k, 0)
            dt.append("permissions", pdata)
        dt.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype=p.get("doctype"))
        return {"message": f"Permissions set for '{role}' on '{p.get('doctype')}'"}

    def set_field_permission(self, p):
        dt = frappe.get_doc("DocType", p.get("doctype"))
        for f in dt.fields:
            if f.fieldname == p.get("fieldname"):
                f.permlevel = p.get("permlevel", 1)
                break
        for rp in p.get("roles_with_access", []):
            dt.append("permissions", {"role": rp["role"], "permlevel": p.get("permlevel", 1),
                                       "read": rp.get("read", 0), "write": rp.get("write", 0)})
        dt.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype=p.get("doctype"))
        return {"message": f"Field permission set for '{p.get('fieldname')}'"}

    def set_user_permission(self, p):
        up = frappe.new_doc("User Permission")
        up.user = p.get("user")
        up.allow = p.get("doctype")
        up.for_value = p.get("value")
        if p.get("applicable_for"):
            up.applicable_for = p["applicable_for"]
        up.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"message": f"User permission created for '{p.get('user')}'"}


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION HANDLER
# ══════════════════════════════════════════════════════════════════════════════

class IntegrationHandler:
    def execute_step(self, step):
        actions = {"create_api": self.create_api, "create_webhook": self.create_webhook}
        handler = actions.get(step.get("action"))
        if not handler:
            frappe.throw(f"Unknown integration action: {step.get('action')}")
        return handler(step.get("params", {}))

    def create_api(self, p):
        ss = frappe.new_doc("Server Script")
        ss.name1 = p.get("api_name")
        ss.script_type = "API"
        ss.api_method = p.get("api_name")
        ss.allow_guest = p.get("allow_guest", 0)
        ss.script = p.get("script", "frappe.response['message'] = 'Hello'")
        ss.disabled = 0
        ss.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"message": f"API '/api/method/{p.get('api_name')}' created"}

    def create_webhook(self, p):
        wh = frappe.new_doc("Webhook")
        wh.webhook_name = p.get("webhook_name", f"{p.get('doctype')} Webhook")
        wh.webhook_doctype = p.get("doctype")
        wh.webhook_docevent = p.get("event", "after_insert")
        wh.request_url = p.get("request_url")
        wh.request_method = p.get("request_method", "POST")
        wh.request_structure = p.get("request_structure", "JSON")
        wh.enabled = 1
        for h in p.get("webhook_headers", []):
            wh.append("webhook_headers", {"key": h.get("key"), "value": h.get("value")})
        for d in p.get("webhook_data", []):
            wh.append("webhook_data", {"fieldname": d.get("fieldname"), "key": d.get("key", d.get("fieldname"))})
        wh.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"message": f"Webhook created for '{p.get('doctype')}'"}


# ══════════════════════════════════════════════════════════════════════════════
# DEVELOPER HANDLER
# ══════════════════════════════════════════════════════════════════════════════

class DeveloperHandler:
    def execute_step(self, step):
        actions = {
            "generate_code": self.generate_code, "generate_fixture": self.generate_fixture,
            "generate_patch": self.generate_patch, "generate_test": self.generate_test,
            "run_sql": self.run_sql, "explain_doctype": self.passthrough,
            "analyze_schema": self.passthrough, "suggest_improvements": self.passthrough,
        }
        handler = actions.get(step.get("action"))
        if not handler:
            frappe.throw(f"Unknown developer action: {step.get('action')}")
        return handler(step.get("params", {}))

    def passthrough(self, p):
        return {"description": p.get("description", ""), "message": "Analysis complete"}

    def generate_code(self, p):
        return {"code": p.get("code", ""), "code_type": p.get("code_type", ""),
                "language": "python" if "python" in p.get("code_type", "").lower() else "javascript",
                "message": f"Code generated for '{p.get('doctype', '')}'"}

    def generate_fixture(self, p):
        dt = p.get("doctype")
        records = frappe.get_all(dt, fields=["*"], limit_page_length=p.get("limit", 100))
        return {"count": len(records), "fixture_json": json.dumps(records, default=str, indent=2),
                "message": f"Fixture generated with {len(records)} records"}

    def generate_patch(self, p):
        return {"code": p.get("script", ""), "message": f"Patch '{p.get('patch_name', '')}' generated"}

    def generate_test(self, p):
        return {"code": p.get("code", ""), "message": f"Test cases generated for '{p.get('doctype', '')}'"}

    def run_sql(self, p):
        query = (p.get("query") or "").strip()
        if not query.upper().startswith("SELECT"):
            frappe.throw("Only SELECT queries allowed")
        result = frappe.db.sql(query, as_dict=True)
        return {"data": result[:100], "row_count": len(result), "message": f"Query returned {len(result)} rows"}
