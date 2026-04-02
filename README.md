# Chief of Staff Hub

A personal productivity dashboard for Technical Program Managers, built with FastAPI and designed to work with Claude AI.

**Author:** [Steven Balalis](https://github.com/steve-balalis-pm)

## Features

- **Task Management** - Syncs with a markdown-based `TASKS.md` file for easy editing
- **Jira Integration** - Dashboard for tracking tickets across multiple projects
- **Daily Briefing** - AI-generated prioritized task recommendations
- **Portfolio Tracking** - Log accomplishments for 1:1 prep and reviews
- **Meeting Notes** - Process notes and extract action items
- **Team Reference** - Quick lookup for team members, tools, and terminology

## Screenshots

The dashboard provides an at-a-glance view of tasks, deadlines, and Jira ticket status.

## Quick Start

### Prerequisites

- Python 3.9+
- A `TASKS.md` file (create your own or use the example structure)

### Installation

```bash
# Clone the repo
git clone https://github.com/steve-balalis-pm/chief-of-staff.git
cd chief-of-staff

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python run.py
```

Open http://localhost:8000 in your browser.

### Configuration

1. **Create TASKS.md** - The task system reads from a `TASKS.md` file. Use this structure:

```markdown
# My Task List

## 🔴 Active — Today
### HIGH PRIORITY
- [ ] Task 1
- [ ] Task 2

## 🟡 This Week
- [ ] Task 3

## 🟢 Ongoing
- [ ] Recurring task

## ✅ Completed This Week
- [x] Done task
```

2. **Jira Integration** (Optional) - Place JSON exports in `jira_data/` folder, or configure MCP integration for live queries.

3. **Customize CLAUDE.md** - Edit the context file to match your role, team, and workflow.

## Project Structure

```
chief_of_staff/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── database.py          # SQLite setup
│   ├── models/              # SQLAlchemy models
│   ├── routers/             # API routes (dashboard, tasks, jira, etc.)
│   ├── services/            # Business logic
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS styles
├── TASKS.md                 # Your task list (not tracked in git)
├── jira_data/               # Jira JSON exports (not tracked)
├── requirements.txt
├── run.py
└── CLAUDE.md                # AI context configuration
```

## Usage with Claude

This project is designed to work with Claude AI (via Cursor, Claude Desktop, etc.). The `CLAUDE.md` file provides context about your workflow, team, and preferences.

Example prompts:
- "Add a task to my list for today"
- "What should I focus on?"
- "Prep for my 1:1 meeting"

## Standalone Generators

For static HTML output (useful for sharing or offline viewing):

```bash
# Generate tasks.html from TASKS.md
python generate_tasks_html.py

# Generate morning-brief.html from Jira data
python generate_jira_dashboard.py
```

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy, SQLite
- **Frontend:** Jinja2 templates, HTMX, vanilla CSS
- **AI Integration:** Designed for Claude with MCP support

## License

MIT License - feel free to fork and customize for your own workflow.

## Contributing

This is a personal productivity tool, but PRs for bug fixes or generic improvements are welcome.

---

Built by [Steven Balalis](https://github.com/steve-balalis-pm) - TPM tools for TPMs.
