"""
AI Configuration Manager
- Reads API keys from AI Architect Settings or site_config.json
- Supports MULTIPLE API keys for failover (ek fail → dusri use)
- Fixed model: gemini-2.5-flash
"""

import frappe

MODEL = "gemini-2.5-flash"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
MAX_OUTPUT_TOKENS = 8192
DEFAULT_TEMPERATURE = 0.1


def get_all_api_keys():
    """
    Get ALL configured API keys as a list (for failover).

    Sources (in priority order):
    1. AI Architect Settings → api_key (primary)
    2. AI Architect Settings → api_key_2 (failover 1)
    3. AI Architect Settings → api_key_3 (failover 2)
    4. site_config.json → GEMINI_API_KEY (fallback)

    Returns:
        list: List of valid API key strings (empty if none configured)
    """
    keys = []

    # Priority 1-3: From AI Architect Settings DocType
    try:
        if frappe.db.exists("DocType", "AI Architect Settings"):
            settings = frappe.get_single("AI Architect Settings")
            for field in ("api_key", "api_key_2", "api_key_3"):
                if settings.get(field):
                    key = settings.get_password(field)
                    if key and key.strip():
                        keys.append(key.strip())
    except Exception:
        pass

    # Priority 4: From site_config.json
    site_key = frappe.conf.get("GEMINI_API_KEY")
    if site_key and site_key.strip() and site_key.strip() not in keys:
        keys.append(site_key.strip())

    return keys


def get_gemini_api_key():
    """Get the primary API key (first available)."""
    keys = get_all_api_keys()
    return keys[0] if keys else None


def is_api_configured():
    """Check if at least one API key is configured."""
    return bool(get_all_api_keys())


def get_api_url(api_key):
    """Build Gemini API URL with given key."""
    return GEMINI_API_URL.format(model=MODEL, key=api_key)


def get_ai_settings():
    """Get all AI settings."""
    settings = {
        "model": MODEL,
        "temperature": DEFAULT_TEMPERATURE,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "safety_mode": True,
        "auto_backup": True,
    }

    try:
        if frappe.db.exists("DocType", "AI Architect Settings"):
            doc = frappe.get_single("AI Architect Settings")
            settings["temperature"] = doc.temperature if doc.temperature is not None else DEFAULT_TEMPERATURE
            settings["max_output_tokens"] = doc.max_tokens or MAX_OUTPUT_TOKENS
            settings["safety_mode"] = bool(doc.safety_mode)
            settings["auto_backup"] = bool(doc.auto_backup)
    except Exception:
        pass

    return settings
