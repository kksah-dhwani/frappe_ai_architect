import frappe

no_cache = 1

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw("Please login to access AI Architect", frappe.AuthenticationError)
    context.no_cache = 1
