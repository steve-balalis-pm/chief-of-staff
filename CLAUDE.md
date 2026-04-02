# Chief of Staff — Task Management & Workflow

**Purpose:** Task management system, daily workflow, and AI assistant context for the Chief of Staff hub. Customize this file for your own role, team, and goals.

---

## 1. Working with Claude — Instructions

### My Goals for Using Claude
I'm a TPM working toward becoming a PM. When helping me:
- **Default to product thinking** — surface the "why" and customer/partner impact, not just the task
- **Be concise and direct** — I prefer tight, actionable outputs over long explanations
- **Push me toward PM habits** — flag where I could add more product framing, stakeholder reasoning, or impact narrative
- **Help me communicate upward** — I often need to translate technical work into clear updates for stakeholders
- **Tie work back to goals** — when relevant, connect tasks to stated team priorities

### Common Task Types

**Jira / Ticket Work**
- Help draft well-structured Jira tickets (clear acceptance criteria, scope, dependencies)
- Summarize ticket status and identify blockers
- Suggest prioritization logic based on active projects and goals

**Cross-Team Coordination**
- Help draft Slack messages or emails for alignment
- Summarize initiative status across the alignment tracker
- Surface risks or gaps in cross-team work

**Documentation**
- Help write or improve Confluence documentation
- Translate technical specs into stakeholder-facing language

**PM Skill Building**
- Help me frame operational work in product/outcome terms
- Draft PRD-style summaries or feature briefs when relevant
- Critique my communication for PM maturity and clarity

---

## 2. Skills & Automation

Custom Claude skills can be invoked by name. Example skills to set up:

| Skill | When to use |
|-------|-------------|
| `daily-briefing` | Morning Jira summary across projects |
| `standup-prep` | Pre-standup draft for team syncs |
| `ticket-hygiene` | Check for stale/incomplete tickets |
| `1on1-prep` | Manager 1:1 prep with current work summary |
| `update-tasks` | Add, complete, or update items in TASKS.md |

---

## 3. TASKS.md — Task System

The `TASKS.md` file in this folder is the canonical task list.

### Viewing Options

| Interface | Command | Use Case |
|-----------|---------|----------|
| **Web App** (primary) | `python run.py` | Day-to-day interactive task management at `http://localhost:8000` |
| **Static HTML** | `python3 generate_tasks_html.py` | Generate `tasks.html` for offline viewing or sharing |
| **Jira Brief** | `python3 generate_jira_dashboard.py` | Generate `morning-brief.html` for archival or email |

**The web app is the primary interface.** It provides interactive checkboxes, Jira integration, and the daily briefing.

**Task section structure:**
- 🔴 Active — Today (HIGH PRIORITY)
- 🟡 Medium Priority / This Week
- ⏳ Waiting On / Blocked
- 🟢 Ongoing / Background
- ✅ Completed This Week
- ❓ Questions Log (by person)
- 📝 Project Notes

**Priority conventions:**
- `- [ ]` = open task
- `- [x]` = completed task
- ~~strikethrough~~ = cancelled/no longer relevant

---

## 4. Workflow Commands

### Morning Brief
**Trigger:** "Morning brief" or "What should I work on today"

Query your Jira projects for:
1. Recently updated tickets
2. Time-sensitive items (due dates, priority labels)

Output a prioritized list of 3-5 items to focus on.

### 1:1 Prep
**Trigger:** "Prep for 1:1" or "manager meeting prep"

Prepare status update covering:
1. What I've been working on (completed items from TASKS.md)
2. Current projects status
3. Blockers or risks to escalate

---

## 5. Tooling Notes

### Task Sync Behavior
The web app parses `TASKS.md` on each request. **TASKS.md is the source of truth.** The SQLite database caches task state for checkbox toggling, but if you edit TASKS.md directly, those changes take precedence on the next page load.

### Jira Data
The dashboard loads Jira data from JSON files in `jira_data/`. You can populate these by:
1. Exporting from Jira directly
2. Using Jira API scripts
3. Using MCP tools (like the Atlassian MCP) for live queries

---

## 6. Customization

To customize for your workflow:
1. Update the "Goals" section with your role and preferences
2. Add your team's Jira project keys
3. Define your own skills and trigger phrases
4. Add team member references for context

---

*This file is designed to be edited. Make it your own.*
