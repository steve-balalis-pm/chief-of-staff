#!/usr/bin/env python3
"""
generate_jira_dashboard.py
Reads Jira data from JSON files and generates a morning brief HTML dashboard.
Run: python3 generate_jira_dashboard.py

To refresh data: Ask Claude to "refresh Jira data" which will re-query and save new JSON files.
"""

import json
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "jira_data")
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "morning-brief.html")

JIRA_BASE = "https://accoladeinc.atlassian.net/browse"
ZENDESK_QUEUE = "https://accolade.zendesk.com/agent/filters/39191042664211"

CATEGORY_KEYWORDS = {
    "Contract Service / Migration": ["contract", "rostra", "migration", "databricks", "redshift"],
    "Feed Delivery / Partner Work": ["feed", "partner", "eligibility", "tmo", "file", "delivery"],
    "Referrals": ["referral", "refer"],
    "Incidents": ["error", "failure", "incident", "fix", "download", "issue", "bug", "broken"],
    "Offboarding / Terminations": ["offboard", "terminate", "termination", "remove", "decommission"],
    "Infrastructure / Tooling": ["infrastructure", "tool", "stored procedure", "script", "automation"],
}


def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return {"issues": []}
    with open(path, "r") as f:
        return json.load(f)


def parse_date(date_str):
    if not date_str:
        return None
    try:
        if "T" in date_str:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00").split(".")[0])
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None


def days_since(date_str):
    d = parse_date(date_str)
    if not d:
        return None
    now = datetime.now()
    if d.tzinfo:
        d = d.replace(tzinfo=None)
    return (now - d).days


def categorize_ticket(summary):
    summary_lower = summary.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in summary_lower for kw in keywords):
            return category
    return "Other"


def get_assignee_name(assignee):
    if not assignee:
        return "Unassigned"
    return assignee.get("displayName", "Unknown")


def get_status_badge(status_name):
    status_lower = status_name.lower()
    if "done" in status_lower or "closed" in status_lower:
        return ("Done", "green")
    elif "progress" in status_lower or "review" in status_lower or "qa" in status_lower:
        return ("In Progress", "yellow")
    elif "blocked" in status_lower:
        return ("Blocked", "red")
    elif "backlog" in status_lower:
        return ("Backlog", "gray")
    else:
        return ("To Do", "blue")


def process_issues(data):
    issues = []
    for item in data.get("issues", []):
        fields = item.get("fields", {})
        assignee = fields.get("assignee")
        status = fields.get("status", {})
        
        issue = {
            "key": item.get("key", ""),
            "summary": fields.get("summary", ""),
            "assignee": get_assignee_name(assignee),
            "status": status.get("name", "Unknown"),
            "status_category": status.get("statusCategory", {}).get("name", ""),
            "duedate": fields.get("duedate"),
            "updated": fields.get("updated"),
            "labels": fields.get("labels", []),
            "priority": fields.get("priority", {}).get("name", "Medium"),
            "category": categorize_ticket(fields.get("summary", "")),
            "days_stale": days_since(fields.get("updated")),
        }
        issues.append(issue)
    return issues


def group_by_category(issues):
    groups = defaultdict(list)
    for issue in issues:
        groups[issue["category"]].append(issue)
    return dict(groups)


def group_by_assignee(issues):
    groups = defaultdict(list)
    for issue in issues:
        groups[issue["assignee"]].append(issue)
    return dict(groups)


def workload_label(count):
    if count == 0:
        return "No tickets"
    elif count <= 3:
        return "Light"
    elif count <= 6:
        return "Normal"
    elif count <= 10:
        return "High load"
    elif count <= 20:
        return "⚠️ OVERLOADED"
    else:
        return "🚨 SEVERELY OVERLOADED"


def generate_html(jupiter_issues, dit_issues, recent_issues, stale_issues, time_sensitive):
    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    time_str = now.strftime("%I:%M %p")
    
    jupiter_by_category = group_by_category(jupiter_issues)
    jupiter_by_assignee = group_by_assignee(jupiter_issues)
    dit_by_assignee = group_by_assignee(dit_issues)
    
    jupiter_recent = [i for i in recent_issues if i["key"].startswith("JUPITER")]
    dit_recent = [i for i in recent_issues if i["key"].startswith("DIT")]
    
    overloaded = []
    for name, tickets in {**jupiter_by_assignee, **dit_by_assignee}.items():
        if len(tickets) > 10:
            overloaded.append((name, len(tickets)))

    needs_attention = []
    for issue in time_sensitive[:10]:
        if issue.get("duedate"):
            days_until = -days_since(issue["duedate"]) if days_since(issue["duedate"]) else 0
            if days_until <= 7:
                needs_attention.append(issue)
    for issue in stale_issues[:5]:
        if issue.get("days_stale", 0) > 10:
            needs_attention.append(issue)
    needs_attention = needs_attention[:5]

    def render_ticket_link(issue):
        return f'<a href="{JIRA_BASE}/{issue["key"]}">{issue["key"]}</a>'

    def render_status_badge(status):
        label, color = get_status_badge(status)
        return f'<span class="badge {color}">{label}</span>'

    def render_issue_row(issue, show_updated=False):
        due_warning = ""
        if issue.get("duedate"):
            days = days_since(issue["duedate"])
            if days and days < 0:
                due_warning = f' <span class="due-soon">⚠️ due {issue["duedate"]}</span>'
            elif days and days > 0:
                due_warning = f' <span class="overdue">🚨 OVERDUE ({days}d)</span>'
        
        updated_note = ""
        if show_updated and issue.get("days_stale") == 0:
            updated_note = " <em>(updated today)</em>"
        
        return f'''<div class="issue-row">
            {render_ticket_link(issue)} — {issue["summary"][:60]}{"..." if len(issue["summary"]) > 60 else ""} 
            {render_status_badge(issue["status"])} 
            <span class="assignee">{issue["assignee"]}</span>
            {due_warning}{updated_note}
        </div>'''

    sections_html = ""

    # 1. Needs Attention
    if needs_attention:
        items = ""
        for i, issue in enumerate(needs_attention, 1):
            context = ""
            if issue.get("duedate"):
                days = days_since(issue["duedate"])
                if days and days > 0:
                    context = f"Overdue by {days} days."
                elif days:
                    context = f"Due in {-days} days."
            if issue.get("days_stale", 0) > 5:
                context += f" No update in {issue['days_stale']} days."
            items += f'''<div class="attention-item">
                <strong>{i}. {render_ticket_link(issue)}</strong> — {issue["summary"]} 
                ({issue["status"]} — {issue["assignee"]})
                <p class="context">{context}</p>
            </div>'''
        sections_html += f'''<div class="section">
            <div class="section-header red">🔴 Needs Your Attention</div>
            <div class="section-content">{items}</div>
        </div>'''

    # 2. In Flight Jupiter
    jupiter_html = ""
    category_order = ["Incidents", "Contract Service / Migration", "Feed Delivery / Partner Work", 
                      "Referrals", "Offboarding / Terminations", "Infrastructure / Tooling", "Other"]
    for cat in category_order:
        if cat in jupiter_by_category:
            issues_in_cat = jupiter_by_category[cat][:10]
            rows = "".join(render_issue_row(i, show_updated=True) for i in issues_in_cat)
            if len(jupiter_by_category[cat]) > 10:
                rows += f'<div class="more">...and {len(jupiter_by_category[cat]) - 10} more</div>'
            jupiter_html += f'<div class="category-group"><div class="category-label">{cat}</div>{rows}</div>'
    
    sections_html += f'''<div class="section">
        <div class="section-header blue">⚡ In Flight (Jupiter) — {len(jupiter_issues)} open</div>
        <div class="section-content">{jupiter_html}</div>
    </div>'''

    # 3. In Flight DIT
    dit_html = ""
    for assignee, issues in sorted(dit_by_assignee.items(), key=lambda x: -len(x[1]))[:8]:
        rows = "".join(render_issue_row(i, show_updated=True) for i in issues[:5])
        if len(issues) > 5:
            rows += f'<div class="more">...and {len(issues) - 5} more</div>'
        dit_html += f'<div class="category-group"><div class="category-label">{assignee} ({len(issues)})</div>{rows}</div>'
    
    sections_html += f'''<div class="section">
        <div class="section-header blue">⚡ In Flight (Moneyball / DIT) — {len(dit_issues)} open</div>
        <div class="section-content">{dit_html}</div>
    </div>'''

    # 4. Stale / At Risk
    if stale_issues:
        stale_rows = ""
        for issue in stale_issues[:15]:
            days = issue.get("days_stale", 0)
            updated_date = issue.get("updated", "")[:10] if issue.get("updated") else "—"
            risk = "Drift"
            risk_class = "yellow"
            if issue.get("duedate"):
                due_days = days_since(issue["duedate"])
                if due_days and due_days > 0:
                    risk = f"OVERDUE {due_days}d"
                    risk_class = "red"
                elif due_days and due_days > -7:
                    risk = f"DUE SOON"
                    risk_class = "orange"
            stale_rows += f'''<tr>
                <td>{render_ticket_link(issue)}</td>
                <td>{issue["summary"][:40]}{"..." if len(issue["summary"]) > 40 else ""}</td>
                <td>{updated_date} ({days}d)</td>
                <td>{issue["assignee"]}</td>
                <td class="risk {risk_class}">{risk}</td>
            </tr>'''
        
        sections_html += f'''<div class="section">
            <div class="section-header orange">🟡 Stale / At Risk (5+ days no update)</div>
            <div class="section-content">
                <table class="stale-table">
                    <tr><th>Ticket</th><th>Summary</th><th>Last Updated</th><th>Assignee</th><th>Risk</th></tr>
                    {stale_rows}
                </table>
            </div>
        </div>'''

    # 5. Recently Updated
    recent_jupiter = "".join(f'<div class="recent-item">{render_ticket_link(i)} — {i["summary"][:50]} | {i.get("updated", "")[:10]} | {i["assignee"]}</div>' 
                             for i in jupiter_recent[:10])
    recent_dit = "".join(f'<div class="recent-item">{render_ticket_link(i)} — {i["summary"][:50]} | {i.get("updated", "")[:10]} | {i["assignee"]}</div>' 
                         for i in dit_recent[:10])
    
    sections_html += f'''<div class="section">
        <div class="section-header green">📬 Recently Updated (last 48h)</div>
        <div class="section-content">
            <div class="subsection-label">Jupiter</div>
            {recent_jupiter if recent_jupiter else "<div class='empty'>No recent updates</div>"}
            <div class="subsection-label">Moneyball (DIT)</div>
            {recent_dit if recent_dit else "<div class='empty'>No recent updates</div>"}
        </div>
    </div>'''

    # 6. Team Workload
    jupiter_workload = ""
    for name, tickets in sorted(jupiter_by_assignee.items(), key=lambda x: -len(x[1])):
        count = len(tickets)
        label = workload_label(count)
        has_priority = any("Top5" in t.get("labels", []) or "TPE" in t.get("labels", []) for t in tickets)
        notes = label
        if has_priority:
            notes += " | Has Top5/TPE"
        jupiter_workload += f"<tr><td>{name}</td><td>{count}</td><td>{notes}</td></tr>"
    
    dit_workload = ""
    for name, tickets in sorted(dit_by_assignee.items(), key=lambda x: -len(x[1]))[:10]:
        count = len(tickets)
        label = workload_label(count)
        dit_workload += f"<tr><td>{name}</td><td>{count}</td><td>{label}</td></tr>"

    overloaded_alert = ""
    if overloaded:
        names = ", ".join(f"{n} ({c})" for n, c in overloaded)
        overloaded_alert = f'<blockquote class="alert">⚠️ Overloaded team members: {names}. Consider spot-checking their queues.</blockquote>'

    sections_html += f'''<div class="section">
        <div class="section-header purple">👥 Team Workload Snapshot</div>
        <div class="section-content">
            <div class="workload-grid">
                <div>
                    <div class="subsection-label">Jupiter Team</div>
                    <table class="workload-table"><tr><th>Person</th><th>Open</th><th>Notes</th></tr>{jupiter_workload}</table>
                </div>
                <div>
                    <div class="subsection-label">Moneyball Team</div>
                    <table class="workload-table"><tr><th>Person</th><th>Open</th><th>Notes</th></tr>{dit_workload}</table>
                </div>
            </div>
            {overloaded_alert}
        </div>
    </div>'''

    # 7. Zendesk
    sections_html += f'''<div class="section">
        <div class="section-header gray">📬 Zendesk Queue</div>
        <div class="section-content" style="text-align: center; padding: 20px;">
            <a href="{ZENDESK_QUEUE}" class="zendesk-btn">Open Zendesk Queue →</a>
            <p class="note">Automated access not available — check manually.</p>
        </div>
    </div>'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Morning Brief — {now.strftime("%Y-%m-%d")}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Inter', sans-serif; background: #f0f2f5; color: #1a1a2e; font-size: 14px; line-height: 1.5; }}
.header {{ background: #1e2d4f; color: white; padding: 20px 32px; }}
.header h1 {{ font-size: 20px; font-weight: 700; }}
.header .meta {{ font-size: 12px; opacity: 0.7; margin-top: 4px; }}
.container {{ max-width: 960px; margin: 0 auto; padding: 24px 20px; }}
.section {{ background: white; border-radius: 8px; margin-bottom: 16px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.07); }}
.section-header {{ padding: 12px 20px; font-weight: 600; font-size: 14px; border-bottom: 1px solid #eee; }}
.section-header.red {{ background: #fff5f5; color: #c0392b; border-left: 4px solid #e74c3c; }}
.section-header.orange {{ background: #fffaf0; color: #d35400; border-left: 4px solid #e67e22; }}
.section-header.blue {{ background: #ebf8ff; color: #2b6cb0; border-left: 4px solid #4299e1; }}
.section-header.green {{ background: #f0fff4; color: #276749; border-left: 4px solid #38a169; }}
.section-header.purple {{ background: #faf5ff; color: #553c9a; border-left: 4px solid #805ad5; }}
.section-header.gray {{ background: #f7fafc; color: #4a5568; border-left: 4px solid #a0aec0; }}
.section-content {{ padding: 16px 20px; }}
.issue-row {{ padding: 8px 0; border-bottom: 1px solid #f5f5f5; font-size: 13px; }}
.issue-row:last-child {{ border-bottom: none; }}
.issue-row a {{ color: #4299e1; text-decoration: none; font-weight: 500; }}
.issue-row a:hover {{ text-decoration: underline; }}
.assignee {{ color: #718096; font-size: 12px; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; margin: 0 4px; }}
.badge.green {{ background: #c6f6d5; color: #276749; }}
.badge.yellow {{ background: #fefcbf; color: #975a16; }}
.badge.red {{ background: #fed7d7; color: #c53030; }}
.badge.blue {{ background: #bee3f8; color: #2b6cb0; }}
.badge.gray {{ background: #e2e8f0; color: #4a5568; }}
.badge.orange {{ background: #feebc8; color: #c05621; }}
.due-soon {{ color: #dd6b20; font-size: 12px; }}
.overdue {{ color: #c53030; font-size: 12px; font-weight: 600; }}
.category-group {{ margin-bottom: 16px; }}
.category-label {{ font-weight: 600; color: #4a5568; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #eee; }}
.subsection-label {{ font-weight: 600; color: #4a5568; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; margin: 16px 0 8px 0; }}
.more {{ color: #a0aec0; font-size: 12px; font-style: italic; padding: 4px 0; }}
.stale-table, .workload-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.stale-table th, .workload-table th {{ text-align: left; padding: 8px; background: #f7fafc; font-weight: 600; font-size: 11px; text-transform: uppercase; }}
.stale-table td, .workload-table td {{ padding: 8px; border-bottom: 1px solid #f0f0f0; }}
.stale-table a {{ color: #4299e1; text-decoration: none; }}
.risk {{ font-weight: 600; font-size: 11px; }}
.risk.red {{ color: #c53030; }}
.risk.orange {{ color: #dd6b20; }}
.risk.yellow {{ color: #d69e2e; }}
.workload-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
@media (max-width: 700px) {{ .workload-grid {{ grid-template-columns: 1fr; }} }}
.alert {{ background: #fffaf0; border-left: 4px solid #ed8936; padding: 12px 16px; margin-top: 16px; font-size: 13px; color: #c05621; }}
.attention-item {{ padding: 12px 0; border-bottom: 1px solid #f0f0f0; }}
.attention-item:last-child {{ border-bottom: none; }}
.attention-item a {{ color: #4299e1; text-decoration: none; }}
.context {{ color: #718096; font-size: 12px; margin-top: 4px; }}
.recent-item {{ padding: 6px 0; font-size: 13px; border-bottom: 1px solid #f9f9f9; }}
.recent-item a {{ color: #4299e1; text-decoration: none; }}
.empty {{ color: #a0aec0; font-style: italic; }}
.zendesk-btn {{ display: inline-block; background: #4299e1; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; }}
.zendesk-btn:hover {{ background: #3182ce; }}
.note {{ color: #a0aec0; font-size: 12px; margin-top: 8px; }}
</style>
</head>
<body>
<div class="header">
    <h1>🗓 Daily Briefing — {date_str}</h1>
    <div class="meta">Generated {time_str} · Jupiter: {len(jupiter_issues)} open · DIT: {len(dit_issues)} open</div>
</div>
<div class="container">
{sections_html}
</div>
</body>
</html>'''
    
    return html


if __name__ == "__main__":
    print("Loading Jira data...")
    jupiter_data = load_json("jupiter_open.json")
    dit_data = load_json("dit_open.json")
    recent_data = load_json("recently_updated.json")
    stale_data = load_json("stale.json")
    time_sensitive_data = load_json("time_sensitive.json")
    
    jupiter_issues = process_issues(jupiter_data)
    dit_issues = process_issues(dit_data)
    recent_issues = process_issues(recent_data)
    stale_issues = process_issues(stale_data)
    time_sensitive = process_issues(time_sensitive_data)
    
    print(f"  Jupiter: {len(jupiter_issues)} open tickets")
    print(f"  DIT: {len(dit_issues)} open tickets")
    print(f"  Recently updated: {len(recent_issues)}")
    print(f"  Stale: {len(stale_issues)}")
    
    html = generate_html(jupiter_issues, dit_issues, recent_issues, stale_issues, time_sensitive)
    
    with open(OUTPUT_HTML, "w") as f:
        f.write(html)
    
    print(f"\n✅ morning-brief.html generated")
    print(f"   → {OUTPUT_HTML}")
