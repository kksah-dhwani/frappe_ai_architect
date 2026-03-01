frappe.ui.form.on("AI Architect Settings", {
    refresh: function(frm) {
        frm.add_custom_button(__("🧪 Test All API Keys"), function() {
            frappe.call({
                method: "frappe_ai_architect.doctype.ai_architect_settings.ai_architect_settings.test_api_key",
                freeze: true,
                freeze_message: "Testing all API keys...",
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: "API Key Test Results",
                            indicator: r.message.status === "success" ? "green" : "red",
                            message: r.message.message
                        });
                    }
                }
            });
        }).addClass("btn-primary");

        frm.add_custom_button(__("🧠 Open AI Architect"), function() {
            window.open("/ai-architect", "_blank");
        });

        if (!frm.doc.is_setup_complete && !frm.doc.api_key) {
            show_setup_wizard();
        }
    },

    after_save: function(frm) {
        if (frm.doc.api_key) {
            frappe.show_alert({
                message: "✅ Saved! <a href='/ai-architect'>Open AI Architect →</a>",
                indicator: "green"
            }, 7);
        }
    }
});

function show_setup_wizard() {
    var d = new frappe.ui.Dialog({
        title: "🧠 AI Architect Setup",
        size: "large",
        fields: [
            {
                fieldtype: "HTML",
                options: '<div style="padding:8px 0">' +
                    '<div style="text-align:center;margin-bottom:20px">' +
                    '<span style="font-size:48px">🧠</span>' +
                    '<h3 style="margin:8px 0 4px">Welcome to Frappe AI Architect!</h3>' +
                    '<p style="color:#666;margin:0">Setup takes 2 minutes. Just get a free API key and paste it below.</p>' +
                    '</div>' +
                    '<div style="background:#f0f7ff;border:1px solid #d0e3f7;border-radius:8px;padding:16px;margin:16px 0">' +
                    '<h4 style="margin:0 0 12px;color:#2c5282">Step 1: Get Free API Key</h4>' +
                    '<ol style="margin:0;padding-left:20px">' +
                    '<li style="margin:8px 0">Click → <a href="https://aistudio.google.com/apikey" target="_blank" style="color:#6C5CE7;font-weight:700;font-size:15px">🔗 Open Google AI Studio</a></li>' +
                    '<li style="margin:8px 0">Sign in with <b>Google account</b> (Gmail)</li>' +
                    '<li style="margin:8px 0">Click <b>"Create API Key"</b> → Copy it</li>' +
                    '</ol>' +
                    '<div style="background:#e8f5e9;border-radius:6px;padding:10px;margin-top:10px">' +
                    '<span style="color:#2e7d32">✅ <b>Free:</b> 15 req/min, 1,500/day — no credit card!</span>' +
                    '</div>' +
                    '</div></div>'
            },
            {
                fieldtype: "Section Break",
                label: "Step 2: Paste Your API Key"
            },
            {
                fieldname: "wizard_api_key",
                fieldtype: "Password",
                label: "Gemini API Key",
                description: "Paste the key you copied from Google AI Studio",
                reqd: 1
            },
            {
                fieldtype: "Column Break"
            },
            {
                fieldname: "wizard_model",
                fieldtype: "Data",
                label: "AI Model",
                default: "gemini-2.5-flash",
                read_only: 1,
                description: "Fixed: gemini-2.5-flash"
            }
        ],
        primary_action_label: "✅ Complete Setup",
        primary_action: function(values) {
            if (!values.wizard_api_key) {
                frappe.msgprint("Please paste your API key!");
                return;
            }
            frappe.call({
                method: "frappe.client.set_value",
                args: {
                    doctype: "AI Architect Settings",
                    name: "AI Architect Settings",
                    fieldname: {
                        api_key: values.wizard_api_key,
                        model: "gemini-2.5-flash",
                        is_setup_complete: 1
                    }
                },
                freeze: true,
                freeze_message: "Saving...",
                callback: function() {
                    d.hide();
                    frappe.msgprint({
                        title: "🎉 Setup Complete!",
                        indicator: "green",
                        message: '<div style="text-align:center;padding:16px">' +
                            '<span style="font-size:48px">🎉</span>' +
                            '<h3>You\'re all set!</h3>' +
                            '<a href="/ai-architect" class="btn btn-primary btn-lg" style="margin-top:12px;background:#6C5CE7;border:none">🧠 Open AI Architect →</a>' +
                            '<br><br><small>Press <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd> from anywhere</small>' +
                            '</div>'
                    });
                    if (cur_frm) cur_frm.reload_doc();
                }
            });
        },
        secondary_action_label: "Skip",
        secondary_action: function() { d.hide(); }
    });
    d.show();
}
