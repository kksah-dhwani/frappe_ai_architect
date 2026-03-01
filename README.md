# 🧠 Frappe AI Architect

AI-Powered System Architect for Frappe Framework using Google Gemini API.

**Natural language → Frappe operations.** Create DocTypes, manage fields, workflows, reports, permissions — just by describing what you want.

## Features

- 🏗️ **DocType Ops** — Create/Edit/Delete/Rename DocTypes, Child Tables, Naming Series
- 📋 **Field Ops** — Add/Remove/Modify/Reorder/Convert fields
- 📊 **Data Ops** — Import, Export, Bulk Update, Cleanup, Sample Data, Migrate
- 📈 **Reports** — Script Reports, Query Reports, Charts, Dashboards
- ⚙️ **Automation** — Workflows, Email Alerts, Assignment Rules, Scheduled Jobs
- 🎨 **UI/UX** — Client Scripts, Custom Buttons, Dynamic Visibility
- 🔐 **Permissions** — Roles, Permission Matrix, Field-level Security
- 🌐 **Integrations** — REST API, Webhooks
- 👨‍💻 **Developer** — Code Generation, Fixtures, Patches, Tests
- 🛡️ **Safety** — Auto Backup, Confirmation, Rollback, Audit Log

## Installation

```bash
bench get-app https://github.com/your-repo/frappe_ai_architect.git
bench --site your-site.local install-app frappe_ai_architect
bench --site your-site.local migrate
bench build --app frappe_ai_architect
bench restart
```

## Setup

After installation, open `/ai-architect` — a setup wizard will guide you:

1. Get free API key from [Google AI Studio](https://aistudio.google.com/apikey)
2. Paste the key in the wizard
3. Done! Start using AI Architect

Or configure manually at `/app/ai-architect-settings`

## Usage

- Open `/ai-architect` in browser
- Or press `Ctrl+Shift+A` from anywhere in Frappe

## License

MIT
