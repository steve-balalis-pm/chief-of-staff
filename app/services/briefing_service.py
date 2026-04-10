"""Briefing service - Generate daily briefing content combining tasks and Jira data."""
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .jira_service import JiraService, JiraTicket
from .field_checker import FieldChecker


@dataclass
class BriefingSection:
    """A section of the daily briefing."""
    title: str
    icon: str
    items: List[Dict[str, Any]] = field(default_factory=list)
    priority: str = "normal"  # 'critical', 'high', 'normal', 'low'
    

@dataclass 
class DailyBriefing:
    """Complete daily briefing data."""
    date: str
    greeting: str
    sections: List[BriefingSection] = field(default_factory=list)
    focus_recommendations: List[str] = field(default_factory=list)
    summary_stats: Dict[str, int] = field(default_factory=dict)
    

class BriefingService:
    """Generate daily briefing content for the Chief of Staff Hub."""
    
    def __init__(self, jira_service: Optional[JiraService] = None, db_session=None):
        self.jira_service = jira_service or JiraService()
        self.field_checker = FieldChecker(self.jira_service)
        self.db_session = db_session
    
    def _get_greeting(self) -> str:
        """Generate a time-appropriate greeting."""
        hour = datetime.now().hour
        if hour < 12:
            return "Good morning"
        elif hour < 17:
            return "Good afternoon"
        else:
            return "Good evening"
    
    def _get_tasks_data(self) -> Dict[str, Any]:
        """Get tasks from TASKS.md via the sync service."""
        try:
            from .tasks_sync import TasksSyncService
            if self.db_session:
                sync_service = TasksSyncService(self.db_session)
                return sync_service.get_dashboard_data()
        except Exception as e:
            print(f"Error getting tasks: {e}")
        
        return {
            "active_today": [],
            "this_week": [],
            "ongoing": [],
            "completed": [],
        }
    
    def generate_briefing(self) -> DailyBriefing:
        """Generate the complete daily briefing."""
        now = datetime.now()
        
        briefing = DailyBriefing(
            date=now.strftime("%A, %B %d, %Y"),
            greeting=self._get_greeting(),
        )
        
        # Get data
        tasks_data = self._get_tasks_data()
        overdue = self.jira_service.get_overdue()
        upcoming = self.jira_service.get_upcoming_deadlines()
        stale = self.jira_service.get_stale_tickets()
        high_priority = self.jira_service.get_high_priority()
        in_progress = self.jira_service.get_in_progress()
        tpe_tickets = self.jira_service.get_tpe_tickets()
        field_summary = self.field_checker.get_actionable_summary()
        
        # Build sections
        
        # 1. Critical: Overdue items
        if overdue:
            briefing.sections.append(BriefingSection(
                title="Overdue - Needs Immediate Attention",
                icon="🚨",
                priority="critical",
                items=[{
                    "key": t.key,
                    "summary": t.summary,
                    "url": t.url,
                    "due_date": t.due_date,
                    "days_overdue": abs((datetime.now().date() - datetime.fromisoformat(t.due_date.replace('Z', '')).date()).days) if t.due_date else 0,
                    "type": "jira"
                } for t in overdue[:5]]
            ))
        
        # 2. Today's Tasks from TASKS.md
        active_today = tasks_data.get("active_today", [])
        open_today = [t for t in active_today if not t.get("done")]
        if open_today:
            briefing.sections.append(BriefingSection(
                title="Today's Tasks",
                icon="📋",
                priority="high",
                items=[{
                    "content": t.get("content", ""),
                    "jira_key": t.get("jira_key"),
                    "type": "task"
                } for t in open_today[:8]]
            ))
        
        # 3. Upcoming Deadlines
        if upcoming:
            briefing.sections.append(BriefingSection(
                title="Coming Up (Next 7 Days)",
                icon="📅",
                priority="high",
                items=[{
                    "key": t.key,
                    "summary": t.summary,
                    "url": t.url,
                    "due_date": t.due_date,
                    "type": "jira"
                } for t in upcoming[:5]]
            ))
        
        # 4. TPE Focus (priority partner tickets)
        if tpe_tickets:
            briefing.sections.append(BriefingSection(
                title="TPE Partner Focus",
                icon="🎯",
                priority="high",
                items=[{
                    "key": t.key,
                    "summary": t.summary,
                    "url": t.url,
                    "status": t.status,
                    "assignee": t.assignee,
                    "type": "jira"
                } for t in tpe_tickets[:5]]
            ))
        
        # 5. High Priority Items
        if high_priority:
            briefing.sections.append(BriefingSection(
                title="High Priority Tickets",
                icon="🔴",
                priority="normal",
                items=[{
                    "key": t.key,
                    "summary": t.summary,
                    "url": t.url,
                    "priority": t.priority,
                    "status": t.status,
                    "type": "jira"
                } for t in high_priority[:5]]
            ))
        
        # 6. Stale tickets that need attention
        if stale:
            briefing.sections.append(BriefingSection(
                title="Stale Items (5+ days without update)",
                icon="⏰",
                priority="normal",
                items=[{
                    "key": t.key,
                    "summary": t.summary,
                    "url": t.url,
                    "days_since_update": t.days_since_update,
                    "type": "jira"
                } for t in stale[:5]]
            ))
        
        # 7. Field Completeness Issues
        if field_summary.get("tickets_with_issues", 0) > 0:
            top_issues = field_summary.get("top_issues", [])[:3]
            briefing.sections.append(BriefingSection(
                title="TPM Field Attention Needed",
                icon="📝",
                priority="normal",
                items=[{
                    "key": item["key"],
                    "summary": item["summary"],
                    "url": item["url"],
                    "issues": [i["field"] for i in item["issues"]],
                    "type": "field_issue"
                } for item in top_issues]
            ))
        
        # 8. This Week's Tasks
        this_week = tasks_data.get("this_week", [])
        open_this_week = [t for t in this_week if not t.get("done")]
        if open_this_week:
            briefing.sections.append(BriefingSection(
                title="This Week",
                icon="🟡",
                priority="low",
                items=[{
                    "content": t.get("content", ""),
                    "jira_key": t.get("jira_key"),
                    "type": "task"
                } for t in open_this_week[:6]]
            ))
        
        # Generate focus recommendations
        briefing.focus_recommendations = self._generate_focus_recommendations(
            overdue=overdue,
            upcoming=upcoming,
            stale=stale,
            open_today=open_today,
            field_summary=field_summary
        )
        
        # Summary stats
        briefing.summary_stats = {
            "overdue": len(overdue),
            "due_this_week": len(upcoming),
            "stale_tickets": len(stale),
            "high_priority": len(high_priority),
            "tpe_tickets": len(tpe_tickets),
            "in_progress": len(in_progress),
            "tasks_today": len(open_today),
            "tasks_this_week": len(open_this_week),
            "field_issues": field_summary.get("tickets_with_issues", 0),
        }
        
        return briefing
    
    def _generate_focus_recommendations(
        self,
        overdue: List[JiraTicket],
        upcoming: List[JiraTicket],
        stale: List[JiraTicket],
        open_today: List[Dict],
        field_summary: Dict[str, Any]
    ) -> List[str]:
        """Generate smart focus recommendations based on current state."""
        recommendations = []
        
        # Overdue is always top priority
        if overdue:
            if len(overdue) == 1:
                recommendations.append(f"Clear the overdue ticket {overdue[0].key} before anything else")
            else:
                recommendations.append(f"Address {len(overdue)} overdue tickets — they need immediate attention")
        
        # Upcoming deadlines
        tomorrow_due = [t for t in upcoming if self._is_due_tomorrow(t)]
        if tomorrow_due:
            recommendations.append(f"{len(tomorrow_due)} ticket(s) due tomorrow — verify they're on track")
        
        # Today's tasks
        if open_today and len(open_today) <= 3:
            recommendations.append("Focus day: you have a manageable task list — aim to complete all")
        
        # Stale tickets
        if stale and len(stale) >= 3:
            recommendations.append(f"Take 15 min to update or close {len(stale)} stale tickets")
        
        # Field completeness
        if field_summary.get("tickets_with_issues", 0) >= 5:
            recommendations.append("Several tickets missing documentation — schedule time for cleanup")
        
        # Default recommendation
        if not recommendations:
            recommendations.append("Clear day ahead — good time for proactive work or documentation")
        
        return recommendations[:4]  # Max 4 recommendations
    
    def _is_due_tomorrow(self, ticket: JiraTicket) -> bool:
        """Check if a ticket is due tomorrow."""
        if not ticket.due_date:
            return False
        try:
            due = datetime.fromisoformat(ticket.due_date.replace('Z', '')).date()
            tomorrow = datetime.now().date()
            from datetime import timedelta
            tomorrow = tomorrow + timedelta(days=1)
            return due == tomorrow
        except:
            return False
    
    def export_markdown(self) -> str:
        """Export the briefing as markdown for 1:1 prep or sharing."""
        briefing = self.generate_briefing()
        
        lines = [
            f"# Daily Briefing — {briefing.date}",
            "",
            f"*{briefing.greeting}*",
            "",
        ]
        
        # Quick stats
        lines.append("## Quick Stats")
        lines.append("")
        stats = briefing.summary_stats
        lines.append(f"- **Overdue:** {stats.get('overdue', 0)}")
        lines.append(f"- **Due this week:** {stats.get('due_this_week', 0)}")
        lines.append(f"- **Tasks today:** {stats.get('tasks_today', 0)}")
        lines.append(f"- **Stale tickets:** {stats.get('stale_tickets', 0)}")
        lines.append(f"- **Field issues:** {stats.get('field_issues', 0)}")
        lines.append("")
        
        # Focus recommendations
        if briefing.focus_recommendations:
            lines.append("## Focus Recommendations")
            lines.append("")
            for rec in briefing.focus_recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        # Sections
        for section in briefing.sections:
            lines.append(f"## {section.icon} {section.title}")
            lines.append("")
            
            for item in section.items:
                if item.get("type") == "jira":
                    key = item.get("key", "")
                    summary = item.get("summary", "")
                    url = item.get("url", "")
                    extra = ""
                    if item.get("due_date"):
                        extra = f" (Due: {item['due_date']})"
                    elif item.get("days_since_update"):
                        extra = f" ({item['days_since_update']} days since update)"
                    lines.append(f"- [{key}]({url}) — {summary}{extra}")
                elif item.get("type") == "task":
                    content = item.get("content", "")
                    jira = item.get("jira_key", "")
                    if jira:
                        lines.append(f"- {content} `{jira}`")
                    else:
                        lines.append(f"- {content}")
                elif item.get("type") == "field_issue":
                    key = item.get("key", "")
                    url = item.get("url", "")
                    issues = ", ".join(item.get("issues", []))
                    lines.append(f"- [{key}]({url}) — Missing: {issues}")
            
            lines.append("")
        
        lines.append("---")
        lines.append(f"*Generated by Chief of Staff Hub at {datetime.now().strftime('%H:%M')}*")
        
        return "\n".join(lines)
