"""DocType Handler - Create, Edit, Delete, Rename, Child Tables, Naming."""

import frappe
from frappe_ai_architect.utils.safety import SafetyManager


class DocTypeHandler:
    def execute_step(self, step):
        action = step.get("action")
        params = step.get("params", {})
        actions = {
            "create_doctype": self.create_doctype,
            "edit_doctype": self.edit_doctype,
            "delete_doctype": self.delete_doctype,
            "rename_doctype": self.rename_doctype,
            "create_child_table": self.create_child_table,
            "link_doctypes": self.link_doctypes,
            "set_naming_series": self.set_naming_series,
            "set_autoname": self.set_autoname,
        }
        handler = actions.get(action)
        if not handler:
            frappe.throw(f"Unknown action: {action}")
        return handler(params)

    def create_doctype(self, p):
        name = p.get("doctype_name")
        if not name:
            frappe.throw("DocType name is required")
        if frappe.db.exists("DocType", name):
            frappe.throw(f"DocType '{name}' already exists")

        module = p.get("module", "Custom")
        if not frappe.db.exists("Module Def", module):
            frappe.get_doc({"doctype": "Module Def", "module_name": module, "custom": 1}).insert(ignore_permissions=True)

        dt = frappe.new_doc("DocType")
        dt.name = name
        dt.module = module
        dt.custom = 1
        dt.istable = p.get("is_child", 0)
        dt.issingle = p.get("is_single", 0)
        dt.is_tree = p.get("is_tree", 0)
        dt.is_submittable = p.get("is_submittable", 0)
        dt.editable_grid = p.get("editable_grid", 1)

        if p.get("autoname"):
            dt.autoname = p["autoname"]
        elif p.get("naming_rule"):
            nm = {"autoincrement": "autoincrement", "random": "hash", "by_naming_series": "naming_series:"}
            dt.autoname = nm.get(p["naming_rule"], p.get("autoname", "hash"))

        if p.get("title_field"):
            dt.title_field = p["title_field"]
        if p.get("search_fields"):
            dt.search_fields = p["search_fields"]

        for i, f in enumerate(p.get("fields", [])):
            dt.append("fields", {
                "fieldname": f.get("fieldname"),
                "fieldtype": f.get("fieldtype", "Data"),
                "label": f.get("label", (f.get("fieldname") or "").replace("_", " ").title()),
                "options": f.get("options"),
                "reqd": f.get("reqd", 0),
                "unique": f.get("unique", 0),
                "in_list_view": f.get("in_list_view", 0),
                "in_standard_filter": f.get("in_standard_filter", 0),
                "default": f.get("default"),
                "description": f.get("description"),
                "depends_on": f.get("depends_on"),
                "hidden": f.get("hidden", 0),
                "read_only": f.get("read_only", 0),
                "bold": f.get("bold", 0),
                "idx": i + 1,
            })

        perms = p.get("permissions", [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}])
        for pm in perms:
            dt.append("permissions", {
                "role": pm.get("role", "System Manager"),
                "read": pm.get("read", 1), "write": pm.get("write", 0),
                "create": pm.get("create", 0), "delete": pm.get("delete", 0),
                "submit": pm.get("submit", 0), "cancel": pm.get("cancel", 0),
                "amend": pm.get("amend", 0),
            })

        dt.insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype=name)
        return {"doctype": name, "message": f"DocType '{name}' created with {len(dt.fields)} fields",
                "url": f"/app/{name.lower().replace(' ', '-')}"}

    def edit_doctype(self, p):
        name = p.get("doctype_name") or p.get("doctype")
        if SafetyManager.is_protected(name):
            frappe.throw(f"Cannot modify protected DocType '{name}'")
        dt = frappe.get_doc("DocType", name)
        for k, v in p.get("changes", {}).items():
            if hasattr(dt, k):
                setattr(dt, k, v)
        dt.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype=name)
        return {"doctype": name, "message": f"DocType '{name}' updated"}

    def delete_doctype(self, p):
        name = p.get("doctype_name") or p.get("doctype")
        if SafetyManager.is_protected(name):
            frappe.throw(f"Cannot delete protected DocType '{name}'")
        if not frappe.db.exists("DocType", name):
            frappe.throw(f"DocType '{name}' not found")
        count = frappe.db.count(name)
        frappe.delete_doc("DocType", name, force=True, ignore_permissions=True)
        frappe.db.commit()
        return {"doctype": name, "message": f"DocType '{name}' deleted ({count} records removed)"}

    def rename_doctype(self, p):
        old = p.get("old_name") or p.get("doctype_name")
        new = p.get("new_name")
        if SafetyManager.is_protected(old):
            frappe.throw(f"Cannot rename protected DocType '{old}'")
        frappe.rename_doc("DocType", old, new, force=True)
        frappe.db.commit()
        return {"message": f"Renamed '{old}' → '{new}'"}

    def create_child_table(self, p):
        p["is_child"] = 1
        result = self.create_doctype(p)
        parent = p.get("parent_doctype")
        if parent and frappe.db.exists("DocType", parent):
            pd = frappe.get_doc("DocType", parent)
            pd.append("fields", {
                "fieldname": p.get("parent_fieldname", p["doctype_name"].lower().replace(" ", "_")),
                "fieldtype": "Table",
                "label": p.get("parent_field_label", p["doctype_name"]),
                "options": p["doctype_name"],
            })
            pd.save(ignore_permissions=True)
            frappe.db.commit()
            result["linked_to"] = parent
        return result

    def link_doctypes(self, p):
        src = p.get("source_doctype")
        tgt = p.get("target_doctype")
        dt = frappe.get_doc("DocType", src)
        fn = p.get("fieldname", tgt.lower().replace(" ", "_"))
        if any(f.fieldname == fn for f in dt.fields):
            frappe.throw(f"Field '{fn}' already exists")
        dt.append("fields", {"fieldname": fn, "fieldtype": "Link", "label": p.get("label", tgt),
                              "options": tgt, "reqd": p.get("reqd", 0), "in_list_view": p.get("in_list_view", 0)})
        dt.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype=src)
        return {"message": f"Link '{fn}' added: '{src}' → '{tgt}'"}

    def set_naming_series(self, p):
        name = p.get("doctype_name")
        dt = frappe.get_doc("DocType", name)
        dt.autoname = p.get("autoname", "naming_series:")
        if not any(f.fieldname == "naming_series" for f in dt.fields):
            dt.append("fields", {"fieldname": "naming_series", "fieldtype": "Select",
                                  "label": "Series", "options": p.get("naming_series", ""), "reqd": 1, "no_copy": 1})
        dt.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype=name)
        return {"message": f"Naming series set for '{name}'"}

    def set_autoname(self, p):
        name = p.get("doctype_name")
        dt = frappe.get_doc("DocType", name)
        dt.autoname = p.get("autoname")
        dt.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype=name)
        return {"message": f"Autoname set to '{p.get('autoname')}' for '{name}'"}
