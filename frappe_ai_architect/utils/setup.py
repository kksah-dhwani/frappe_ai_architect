"""
Setup utilities - runs after app installation.
Triggers the setup wizard for first-time configuration.
"""

import frappe


def after_install():
    """Called after bench install-app. Creates default settings."""
    try:
        # Create default settings if not exists
        if not frappe.db.exists("AI Architect Settings"):
            settings = frappe.new_doc("AI Architect Settings")
            settings.model = "gemini-2.0-flash"
            settings.temperature = 0.1
            settings.max_tokens = 8192
            settings.safety_mode = 1
            settings.auto_backup = 1
            settings.allowed_roles = "System Manager\nAdministrator"
            settings.is_setup_complete = 0
            settings.insert(ignore_permissions=True)
            frappe.db.commit()

        frappe.clear_cache()
        print("✅ Frappe AI Architect installed successfully!")
        print("👉 Go to: /app/ai-architect-settings to configure your API key")
        print("👉 Or visit: /ai-architect to start using")

    except Exception as e:
        frappe.log_error(str(e), "AI Architect - After Install Error")
        print(f"⚠️ AI Architect installed but setup had an issue: {e}")
        print("👉 Go to /app/ai-architect-settings to complete setup manually")
