"""Field Handler - Add, Remove, Modify, Reorder, Convert fields."""

import frappe
from frappe_ai_architect.utils.safety import SafetyManager


class FieldHandler:
    def execute_step(self, step):
        actions = {
            "add_field": self.add_field, "add_fields": self.add_fields,
            "remove_field": self.remove_field, "modify_field": self.modify_field,
            "reorder_fields": self.reorder_fields, "convert_field_type": self.convert_field_type,
        }
        handler = actions.get(step.get("action"))
        if not handler:
            frappe.throw(f"Unknown field action: {step.get('action')}")
        return handler(step.get("params", {}))

    def add_field(self, p):
        dt_name = p.get("doctype")
        if SafetyManager.is_protected(dt_name):
            frappe.throw(f"Cannot modify '{dt_name}'")
        dt = frappe.get_doc("DocType", dt_name)
        fn = p.get("fieldname")
        if any(f.fieldname == fn for f in dt.fields):
            frappe.throw(f"Field '{fn}' already exists")
        dt.append("fields", {
            "fieldname": fn, "fieldtype": p.get("fieldtype", "Data"),
            "label": p.get("label", fn.replace("_", " ").title()),
            "options": p.get("options"), "reqd": p.get("reqd", 0),
            "unique": p.get("unique", 0), "in_list_view": p.get("in_list_view", 0),
            "in_standard_filter": p.get("in_standard_filter", 0),
            "default": p.get("default"), "description": p.get("description"),
            "depends_on": p.get("depends_on"), "hidden": p.get("hidden", 0),
            "read_only": p.get("read_only", 0), "bold": p.get("bold", 0),
            "fetch_from": p.get("fetch_from"),
        })
        dt.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype=dt_name)
        return {"message": f"Field '{fn}' ({p.get('fieldtype', 'Data')}) added to '{dt_name}'"}

    def add_fields(self, p):
        dt_name = p.get("doctype")
        dt = frappe.get_doc("DocType", dt_name)
        existing = {f.fieldname for f in dt.fields}
        added = []
        for f in p.get("fields", []):
            fn = f.get("fieldname")
            if fn in existing:
                continue
            dt.append("fields", {
                "fieldname": fn, "fieldtype": f.get("fieldtype", "Data"),
                "label": f.get("label", fn.replace("_", " ").title()),
                "options": f.get("options"), "reqd": f.get("reqd", 0),
                "in_list_view": f.get("in_list_view", 0), "bold": f.get("bold", 0),
            })
            added.append(fn)
        dt.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype=dt_name)
        return {"message": f"{len(added)} fields added to '{dt_name}'", "fields": added}

    def remove_field(self, p):
        dt_name = p.get("doctype")
        fn = p.get("fieldname")
        dt = frappe.get_doc("DocType", dt_name)
        target = next((f for f in dt.fields if f.fieldname == fn), None)
        if not target:
            frappe.throw(f"Field '{fn}' not found")
        dt.fields.remove(target)
        dt.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype=dt_name)
        return {"message": f"Field '{fn}' removed from '{dt_name}'"}

    def modify_field(self, p):
        dt_name = p.get("doctype")
        fn = p.get("fieldname")
        dt = frappe.get_doc("DocType", dt_name)
        target = next((f for f in dt.fields if f.fieldname == fn), None)
        if not target:
            frappe.throw(f"Field '{fn}' not found")
        for k, v in p.get("changes", {}).items():
            if hasattr(target, k):
                setattr(target, k, v)
        dt.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype=dt_name)
        return {"message": f"Field '{fn}' updated in '{dt_name}'"}

    def reorder_fields(self, p):
        dt_name = p.get("doctype")
        order = p.get("field_order", [])
        dt = frappe.get_doc("DocType", dt_name)
        fmap = {f.fieldname: f for f in dt.fields}
        idx = 1
        for fn in order:
            if fn in fmap:
                fmap[fn].idx = idx
                idx += 1
        for f in dt.fields:
            if f.fieldname not in order:
                f.idx = idx
                idx += 1
        dt.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype=dt_name)
        return {"message": f"Fields reordered in '{dt_name}'"}

    def convert_field_type(self, p):
        dt_name = p.get("doctype")
        fn = p.get("fieldname")
        new_type = p.get("new_fieldtype")
        dt = frappe.get_doc("DocType", dt_name)
        target = next((f for f in dt.fields if f.fieldname == fn), None)
        if not target:
            frappe.throw(f"Field '{fn}' not found")
        old = target.fieldtype
        target.fieldtype = new_type
        if "new_options" in p:
            target.options = p["new_options"]
        dt.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype=dt_name)
        return {"message": f"Field '{fn}' converted: {old} → {new_type}"}
