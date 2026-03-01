"""AI Architect Settings - Configuration & Setup Controller."""

import frappe
import requests
from frappe.model.document import Document


class AIArchitectSettings(Document):
    def validate(self):
        if self.temperature is not None:
            if self.temperature < 0 or self.temperature > 2:
                frappe.throw("Temperature must be between 0.0 and 2.0")
        if self.max_tokens and self.max_tokens < 100:
            frappe.throw("Max tokens must be at least 100")
        # Force model to gemini-2.5-flash
        self.model = "gemini-2.5-flash"

    def on_update(self):
        if self.api_key and not self.is_setup_complete:
            self.db_set("is_setup_complete", 1, update_modified=False)
            frappe.clear_cache()


@frappe.whitelist()
def test_api_key():
    """Test if the configured Gemini API key works (REST API, no SDK)."""
    from frappe_ai_architect.config.ai_config import get_all_api_keys

    keys = get_all_api_keys()
    if not keys:
        return {"status": "error", "message": "❌ No API key configured"}

    results = []
    for i, key in enumerate(keys):
        masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
        label = ["Primary", "Failover 2", "Failover 3", "site_config"][i] if i < 4 else f"Key {i+1}"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"

        try:
            resp = requests.post(url, json={
                "contents": [{"parts": [{"text": "Say OK"}]}]
            }, timeout=10)

            if resp.status_code == 200:
                results.append({"key": label, "masked": masked, "status": "✅ Working"})
            elif resp.status_code == 429:
                results.append({"key": label, "masked": masked, "status": "⚠️ Quota exhausted (failover will skip)"})
            elif resp.status_code == 403:
                results.append({"key": label, "masked": masked, "status": "❌ Invalid key"})
            else:
                results.append({"key": label, "masked": masked, "status": f"❌ HTTP {resp.status_code}"})
        except Exception as e:
            results.append({"key": label, "masked": masked, "status": f"❌ {str(e)[:50]}"})

    working = sum(1 for r in results if "✅" in r["status"])
    detail = "<br>".join([f"<b>{r['key']}</b> ({r['masked']}): {r['status']}" for r in results])

    return {
        "status": "success" if working > 0 else "error",
        "message": f"{'✅' if working > 0 else '❌'} {working}/{len(results)} keys working<br><br>{detail}",
    }
