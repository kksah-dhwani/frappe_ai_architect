app_name = "frappe_ai_architect"
app_title = "Frappe AI Architect"
app_publisher = "Suvaidyam - Villintel"
app_description = "AI-Powered System Architect for Frappe Framework using Gemini API"
app_email = "suvaidyam@villintel.com"
app_license = "MIT"
app_version = "1.0.0"

# ── App Includes ──────────────────────────────────────────────────────────────
app_include_css = "/assets/frappe_ai_architect/css/ai_architect.css"
app_include_js = "/assets/frappe_ai_architect/js/ai_architect.js"

# ── After Install Hook ────────────────────────────────────────────────────────
# This triggers the setup wizard after app installation
after_install = "frappe_ai_architect.utils.setup.after_install"

# ── Website Route Rules ───────────────────────────────────────────────────────
website_route_rules = [
    {"from_route": "/ai-architect", "to_route": "ai_architect"},
]

# ── Fixtures (export these when doing bench export-fixtures) ──────────────────
# fixtures = []

# ── Override Whitelisted Methods ──────────────────────────────────────────────
# override_whitelisted_methods = {}
