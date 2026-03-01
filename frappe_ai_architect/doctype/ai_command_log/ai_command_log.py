"""AI Command Log - Audit trail for all AI operations."""

import frappe
from frappe.model.document import Document


class AICommandLog(Document):
    def validate(self):
        if not self.status:
            self.status = "Pending"

    def before_save(self):
        # Truncate oversized fields
        for field in ("ai_response", "execution_result"):
            val = self.get(field)
            if val and len(val) > 10000:
                self.set(field, val[:10000] + "\n... (truncated)")
        if self.backup_data and len(self.backup_data) > 50000:
            self.backup_data = self.backup_data[:50000] + "\n... (truncated)"
