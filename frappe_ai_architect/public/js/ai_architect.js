/**
 * Frappe AI Architect - Desk Integration
 * Keyboard shortcut Ctrl+Shift+A to open AI Architect
 */
frappe.provide("frappe.ai_architect");

frappe.ai_architect = {
    open: function() {
        window.open("/ai-architect", "_blank");
    }
};

// Keyboard shortcut: Ctrl+Shift+A
document.addEventListener("keydown", function(e) {
    if (e.ctrlKey && e.shiftKey && (e.key === "A" || e.key === "a")) {
        e.preventDefault();
        frappe.ai_architect.open();
    }
});
