# Chief of Staff — Task Management & Workflow

**Owner:** Steven Balalis
**Last Updated:** March 2026
**Purpose:** Task management system, daily workflow, and skill commands for the Chief of Staff hub. Global context (role, teams, goals, tools) lives in the root `CLAUDE.md` one level up.

---

## 1. Working with Claude — Instructions

### My Goals for Using Claude
I'm a TPM working toward becoming a PM. When helping me:
- **Default to product thinking** — surface the "why" and customer/partner impact, not just the task
- **Be concise and direct** — I prefer tight, actionable outputs over long explanations
- **Push me toward PM habits** — flag where I could add more product framing, stakeholder reasoning, or impact narrative
- **Help me communicate upward** — I often need to translate technical work into clear updates for Chris or cross-functional stakeholders
- **Tie work back to 2026 goals** — when relevant, connect tasks to Chris's stated priorities from the Tech Townhall

### Common Task Types

**Jira / Ticket Work**
- Help draft well-structured Jira tickets (clear acceptance criteria, scope, dependencies)
- Summarize ticket status and identify blockers
- Suggest prioritization logic based on active projects and 2026 goals

**Cross-Team Coordination**
- Help draft Slack messages or emails to align Jupiter and Moneyball
- Summarize initiative status across the alignment tracker
- Surface risks or gaps in cross-team work

**Documentation**
- Help write or improve Confluence documentation for partner feeds
- Translate technical specs into partner-facing or stakeholder-facing language

**PM Skill Building**
- Help me frame operational work in product/outcome terms
- Draft PRD-style summaries or feature briefs when relevant
- Critique my communication for PM maturity and clarity

---

## 2. Skills & Automation

Steven has a suite of custom Claude skills. Invoke these by name when relevant rather than recreating the work from scratch:

| Skill | When to use |
|-------|-------------|
| `daily-chief-of-staff-briefing` | Morning Jira summary across Jupiter & Moneyball |
| `standup-prep-mon-fri` | Pre-standup draft for Monday/Friday 1pm sync |
| `standup-prep-wed` | Pre-standup draft for Wednesday 10:30am sync |
| `jupiter-ticket` | Create or clone a new JUPITER feed request ticket |
| `jupiter-ticket-hygiene` | Monday morning check for stale/incomplete tickets |
| `jupiter-smartsheet-sync` | Sync active JUPITER tickets to Smartsheet |
| `jupiter-jira-tracker-sync` | Sync JUPITER ticket statuses into TPM tracking workbook |
| `moneyball-dashboard-refresh` | Refresh Moneyball (DIT) Jira TPM dashboard |
| `monday-pm-skill-builder` | Weekly PM micro-learning prompt (Monday mornings) |
| `friday-eow-reflection` | End-of-week structured reflection (wins, blockers, next week) |
| `chris-1on1-prep` | Bi-weekly Chris 1:1 prep — current work, Databricks migration, retro projects |
| `weekly-competitive-brief` | Wednesday rotating competitive brief (health navigation space) |
| `cs-inquiry-assistant` | Look up feed info, carrier details, or cadence for CS inquiries |
| `update-tasks` | Add, complete, or update items in TASKS.md — **canonical file: `just_code(current)/chief_of_staff/TASKS.md`** |
| `one-drive-cleanup` | Organize and rename files in OneDrive |

---

## 3. TASKS.md — Task System

The `TASKS.md` file in this folder is the canonical task list.

### Viewing Options

| Interface | Command | Use Case |
|-----------|---------|----------|
| **Web App** (primary) | `python run.py` | Day-to-day interactive task management at `http://localhost:8000` |
| **Static HTML** | `python3 generate_tasks_html.py` | Generate `tasks.html` for offline viewing or sharing |
| **Jira Brief** | `python3 generate_jira_dashboard.py` | Generate `morning-brief.html` for archival or email |

**The web app is the primary interface.** It provides interactive checkboxes, Jira integration, and the daily briefing. Use the standalone scripts only when you need a static HTML snapshot to share or archive.

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
- 🔴 HIGH / 🟡 MEDIUM / 🟢 ONGOING map to red/yellow/green in the dashboard

---

## 4. Workflow Commands

### T-Shirt Estimator
**Trigger:** "Help me estimate this" or "t-shirt this request"

Sizing rubric lives in `/Users/Steven.Balalis/Desktop/Resonance/tshirt-rubric.md` — read it first.

When estimating, collect:
- File type: Eligibility / TMO / Referral
- New partner or existing?
- Schema changes required?
- SFTP setup needed (new credentials, folder, GoAnywhere config)?
- IB dependency (inbound data must exist/change first)?
- Delivery environment: test + prod, or prod only?

Output format:
```
Size: [XS/S/M/L/XL]
Rationale:
- [factor 1]
- [factor 2]
- [factor 3]
Assumptions/flags: [any IB deps, missing info, or risks]
```

---

### Morning Brief
**Trigger:** "Morning brief" or "What should I work on today"

Use Jira MCP to query all three boards. Run these JQL queries:
1. `project = JUPITER AND updated >= -2d ORDER BY updated DESC` — recently moved
2. `project = DIT AND updated >= -2d ORDER BY updated DESC` — recently moved
3. `project in (JUPITER, DIT) AND statusCategory != Done AND (duedate is not EMPTY OR labels = "Top5" OR labels = "TPE") ORDER BY duedate ASC` — time-sensitive

Output format:
```
## Morning Brief — [date]

### Act on today (top 3-5)
1. [ticket] — [why: launch date / label / stage]

### Recently updated (FYI)
- [ticket] — moved to [status]
```

Prioritization order: launch date → SFTP/test/prod stage → IB dependency → stakeholder urgency

---

### Chris 1:1 Prep
**Trigger:** "Prep for Chris 1:1" or "Chris meeting prep"

**Cadence:** Bi-weekly Tuesdays

**Trackers to review/update before meeting:**
1. **CC Project Tracker** — `OneDrive-Accolade,Inc/cc_project_tracker.xlsx` (your work, Databricks, retros)
2. **Jupiter Tracker** — `OneDrive-Accolade,Inc/DataAndTracking/2025-10-08_JupiterTracker_v1.xlsx` (team work: Expedite, Top5, TPE, 2026 Launches)

Prepare status update covering three areas:

1. **What I've been working on** — pull from TASKS.md completed items, recent Jira activity, Jupiter Tracker updates
2. **Databricks migration** — read CC Project Tracker for current wave status, blockers, next milestones
3. **Retro projects** — list each open retro (Jupiter acceptance criteria, IM ticketing, etc.) with owner/status/next step

Output format:
```
## Chris 1:1 Prep — [date]

### 🔹 What I've been working on
- [completed item 1]
- [completed item 2]
- [in-progress highlight]

### 🔹 Jupiter Tracker Status
- Expedite: [count] tickets
- Top5: [count] tickets
- TPE: [status summary]
- 2026 Launches: [status summary]

### 🔹 Databricks Migration
- **Current wave:** [wave #] — [status]
- **Blockers:** [any blockers or "none"]
- **Next milestone:** [what + target date]

### 🔹 Retro Projects
| Retro | Owner | Status | Next Step |
|-------|-------|--------|-----------|
| [name] | [owner] | [status] | [action] |
```

Before the meeting, refresh both cc_project_tracker.xlsx AND Jupiter Tracker with latest statuses.

---

## 5. Tooling Notes
- **Kapture: NOT available** — no browser automation of any kind (deprecated as of March 2026)
- **Jira MCP** (`mcp__9b936e9b-a318-4cbb-a77b-16c0744c5a1c__*`): use for all Jira queries, ticket reads, and updates
- **Island browser**: operated manually by Steven only — never automate

### Task Sync Behavior
The web app parses `TASKS.md` on each request. **TASKS.md is the source of truth.** The SQLite database caches task state for checkbox toggling, but if you edit TASKS.md directly, those changes take precedence on the next page load. For best results:
1. Use the web app for toggling tasks done/not-done
2. Edit TASKS.md directly for adding/removing/reorganizing tasks
3. The standalone HTML generators always read fresh from TASKS.md

### Jira Data Refresh
**Steven does NOT have Jira API tokens.** The dashboard loads Jira data from JSON files in `jira_data/`. 

**Skill:** `jira-data-refresh` — use this skill to pull fresh data from Jira via the Atlassian MCP.

**When to refresh:**
- Daily (automatically called by `daily-chief-of-staff-briefing`)
- On-demand when data looks stale

**Trigger phrases:** "Refresh Jira data", "Update Jira dashboard", "Pull latest Jira tickets"

**Quick manual refresh:**
1. Authenticate: `CallMcpTool(server="plugin-atlassian-atlassian", toolName="mcp_auth", arguments={})`
2. Query using `searchJiraIssuesUsingJql` with cloudId `5120347d-a66f-4103-aea1-2764f5b3918b`
3. Save results to `jira_data/` folder

---

## 6. Document Maintenance

**Update Triggers:**
- New skills added or renamed
- Workflow commands change
- Task system conventions evolve
- Role evolution (TPM → PM transitions)

*Global context (teams, goals, tools, terminology) is maintained in `just_code(current)/CLAUDE.md` — update there for anything cross-project.*
