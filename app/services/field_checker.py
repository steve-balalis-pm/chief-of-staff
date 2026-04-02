"""Field checker service - Identify Jira tickets missing required TPM fields."""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from .jira_service import JiraService, JiraTicket


@dataclass
class FieldIssue:
    """Represents a missing or incomplete field on a ticket."""
    field_name: str
    description: str
    severity: str  # 'high', 'medium', 'low'


@dataclass
class TicketFieldReport:
    """Report on a single ticket's field completeness."""
    ticket: JiraTicket
    issues: List[FieldIssue] = field(default_factory=list)
    
    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0
    
    @property
    def issue_count(self) -> int:
        return len(self.issues)
    
    @property
    def high_severity_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == 'high')


@dataclass
class FieldCompletnessSummary:
    """Summary of field completeness across all checked tickets."""
    total_tickets: int = 0
    tickets_with_issues: int = 0
    missing_confluence: int = 0
    missing_acceptance_criteria: int = 0
    missing_due_date: int = 0
    stale_tickets: int = 0
    reports: List[TicketFieldReport] = field(default_factory=list)
    
    @property
    def health_score(self) -> int:
        """Calculate a health score from 0-100."""
        if self.total_tickets == 0:
            return 100
        
        issues_per_ticket = sum(r.issue_count for r in self.reports) / self.total_tickets
        # Lower issues = higher score
        # 0 issues = 100, 4+ issues avg = 0
        return max(0, int(100 - (issues_per_ticket * 25)))
    
    def get_tickets_with_issue(self, issue_type: str) -> List[TicketFieldReport]:
        """Get all tickets with a specific issue type."""
        return [
            r for r in self.reports 
            if any(i.field_name == issue_type for i in r.issues)
        ]


class FieldChecker:
    """Check Jira tickets for missing TPM-required fields."""
    
    def __init__(self, jira_service: Optional[JiraService] = None):
        self.jira_service = jira_service or JiraService()
    
    def check_ticket(self, ticket: JiraTicket) -> TicketFieldReport:
        """Check a single ticket for missing fields."""
        report = TicketFieldReport(ticket=ticket)
        
        # Check for Confluence documentation link
        if not ticket.has_confluence_link:
            report.issues.append(FieldIssue(
                field_name="confluence_link",
                description="Missing Confluence documentation link in description",
                severity="high" if ticket.status == "In Progress" else "medium"
            ))
        
        # Check for acceptance criteria (in description for now - could be custom field)
        if not self._has_acceptance_criteria(ticket):
            report.issues.append(FieldIssue(
                field_name="acceptance_criteria",
                description="Missing acceptance criteria",
                severity="high" if self._is_priority_ticket(ticket) else "medium"
            ))
        
        # Check for due date on tickets that require it
        if ticket.requires_due_date and not ticket.due_date:
            report.issues.append(FieldIssue(
                field_name="due_date",
                description=f"Missing due date (required for {', '.join(ticket.labels)} tickets)",
                severity="high"
            ))
        
        # Check for staleness (not updated in 14+ days)
        if ticket.days_since_update >= 14:
            report.issues.append(FieldIssue(
                field_name="stale",
                description=f"Not updated in {ticket.days_since_update} days",
                severity="high" if ticket.days_since_update >= 30 else "medium"
            ))
        
        # Check for overdue
        if ticket.is_overdue:
            report.issues.append(FieldIssue(
                field_name="overdue",
                description=f"Past due date: {ticket.due_date}",
                severity="high"
            ))
        
        return report
    
    def _has_acceptance_criteria(self, ticket: JiraTicket) -> bool:
        """Check if ticket has acceptance criteria."""
        if not ticket.description:
            return False
        
        desc_lower = ticket.description.lower()
        indicators = [
            'acceptance criteria',
            'ac:',
            'criteria:',
            'definition of done',
            'dod:',
            '✅',  # Common AC checkbox indicator
            '- [ ]',  # Markdown checklist
        ]
        
        return any(indicator in desc_lower for indicator in indicators)
    
    def _is_priority_ticket(self, ticket: JiraTicket) -> bool:
        """Check if this is a priority ticket requiring extra attention."""
        priority_labels = {'tpe', 'top5', 'expedite', '2026-launch'}
        return (
            ticket.priority in ('Highest', 'High') or
            bool(set(l.lower() for l in ticket.labels) & priority_labels)
        )
    
    def check_tickets(self, tickets: List[JiraTicket]) -> FieldCompletnessSummary:
        """Check multiple tickets and generate summary."""
        summary = FieldCompletnessSummary()
        summary.total_tickets = len(tickets)
        
        for ticket in tickets:
            report = self.check_ticket(ticket)
            summary.reports.append(report)
            
            if report.has_issues:
                summary.tickets_with_issues += 1
            
            # Count specific issues
            for issue in report.issues:
                if issue.field_name == "confluence_link":
                    summary.missing_confluence += 1
                elif issue.field_name == "acceptance_criteria":
                    summary.missing_acceptance_criteria += 1
                elif issue.field_name == "due_date":
                    summary.missing_due_date += 1
                elif issue.field_name == "stale":
                    summary.stale_tickets += 1
        
        # Sort reports by issue count (most issues first)
        summary.reports.sort(key=lambda r: (-r.high_severity_count, -r.issue_count))
        
        return summary
    
    def check_project(self, project: str = "JUPITER") -> FieldCompletnessSummary:
        """Check all open tickets in a project."""
        jql = f'project = {project} AND statusCategory != Done ORDER BY updated DESC'
        tickets = self.jira_service.search_jql_sync(jql, max_results=100)
        return self.check_tickets(tickets)
    
    def get_actionable_summary(self, project: str = "JUPITER") -> Dict[str, Any]:
        """Get a summary optimized for display in the dashboard."""
        summary = self.check_project(project)
        
        # Get top issues to show
        top_issues = [
            r for r in summary.reports 
            if r.high_severity_count > 0
        ][:5]
        
        return {
            "total_tickets": summary.total_tickets,
            "tickets_with_issues": summary.tickets_with_issues,
            "health_score": summary.health_score,
            "breakdown": {
                "missing_confluence": summary.missing_confluence,
                "missing_acceptance_criteria": summary.missing_acceptance_criteria,
                "missing_due_date": summary.missing_due_date,
                "stale": summary.stale_tickets,
            },
            "top_issues": [
                {
                    "key": r.ticket.key,
                    "summary": r.ticket.summary,
                    "url": r.ticket.url,
                    "issues": [
                        {"field": i.field_name, "description": i.description, "severity": i.severity}
                        for i in r.issues
                    ]
                }
                for r in top_issues
            ],
            "all_reports": summary.reports,
        }
