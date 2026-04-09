"""Jira service - Load Jira data from MCP-refreshed JSON files."""
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

# Configuration
# Configure this for your Jira instance
JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "https://your-org.atlassian.net")
JIRA_DATA_DIR = Path(__file__).parent.parent.parent / "jira_data"


@dataclass
class JiraTicket:
    """Represents a Jira ticket."""
    key: str
    summary: str
    status: str
    priority: str
    assignee: Optional[str]
    due_date: Optional[str]
    updated: str
    created: str
    labels: List[str] = field(default_factory=list)
    description: Optional[str] = None
    issue_type: str = "Task"
    url: str = ""
    
    def __post_init__(self):
        self.url = f"{JIRA_BASE_URL}/browse/{self.key}"
    
    @property
    def is_overdue(self) -> bool:
        if not self.due_date:
            return False
        try:
            due = datetime.fromisoformat(self.due_date.replace('Z', '+00:00'))
            return due.date() < datetime.now().date()
        except:
            return False
    
    @property
    def days_since_update(self) -> int:
        try:
            updated = datetime.fromisoformat(self.updated.replace('Z', '+00:00'))
            return (datetime.now(updated.tzinfo) - updated).days
        except:
            return 0
    
    @property
    def is_stale(self) -> bool:
        return self.days_since_update >= 5
    
    @property
    def has_confluence_link(self) -> bool:
        if not self.description:
            return False
        return 'atlassian.net/wiki' in self.description.lower()
    
    @property
    def requires_due_date(self) -> bool:
        """Check if ticket has labels that require a due date."""
        required_labels = {'tpe', 'top5', 'expedite', '2026-launch'}
        return bool(set(l.lower() for l in self.labels) & required_labels)


class JiraService:
    """Service for loading Jira tickets from MCP-refreshed JSON files."""
    
    def __init__(self):
        self.base_url = JIRA_BASE_URL
        self._cache = {}
    
    @property
    def is_configured(self) -> bool:
        """Check if JSON data files exist."""
        return (JIRA_DATA_DIR / "jupiter_open.json").exists()
    
    def _load_json(self, filename: str) -> Dict:
        """Load a JSON file from jira_data directory."""
        if filename in self._cache:
            return self._cache[filename]
        
        filepath = JIRA_DATA_DIR / filename
        if not filepath.exists():
            return {"issues": []}
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                self._cache[filename] = data
                return data
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return {"issues": []}
    
    def _parse_ticket(self, issue: Dict) -> JiraTicket:
        """Parse Jira API response into JiraTicket."""
        fields = issue.get('fields', {})
        
        assignee = fields.get('assignee')
        assignee_name = assignee.get('displayName') if assignee else None
        
        priority = fields.get('priority')
        priority_name = priority.get('name') if priority else 'Medium'
        
        status = fields.get('status')
        status_name = status.get('name') if status else 'Unknown'
        
        issue_type = fields.get('issuetype')
        issue_type_name = issue_type.get('name') if issue_type else 'Task'
        
        # Get description text
        description = fields.get('description')
        desc_text = ""
        if description:
            if isinstance(description, dict):
                # ADF format - extract text content
                desc_text = self._extract_adf_text(description)
            else:
                desc_text = str(description)
        
        return JiraTicket(
            key=issue.get('key', ''),
            summary=fields.get('summary', ''),
            status=status_name,
            priority=priority_name,
            assignee=assignee_name,
            due_date=fields.get('duedate'),
            updated=fields.get('updated', ''),
            created=fields.get('created', ''),
            labels=fields.get('labels', []),
            description=desc_text,
            issue_type=issue_type_name
        )
    
    def _extract_adf_text(self, adf: Dict) -> str:
        """Extract plain text from Atlassian Document Format."""
        text_parts = []
        
        def extract_content(node):
            if isinstance(node, dict):
                if node.get('type') == 'text':
                    text_parts.append(node.get('text', ''))
                for child in node.get('content', []):
                    extract_content(child)
            elif isinstance(node, list):
                for item in node:
                    extract_content(item)
        
        extract_content(adf)
        return ' '.join(text_parts)
    
    def _get_issues_from_data(self, data: Dict) -> List[Dict]:
        """Extract issues array from JSON data, handling nested structure."""
        issues = data.get('issues', [])
        if isinstance(issues, dict):
            return issues.get('nodes', [])
        return issues
    
    def _get_all_tickets(self, project: str = None) -> List[JiraTicket]:
        """Load all tickets from JSON files, optionally filtered by project."""
        tickets = []
        
        if project == "JUPITER" or project is None:
            data = self._load_json("jupiter_open.json")
            tickets.extend([self._parse_ticket(issue) for issue in self._get_issues_from_data(data)])
        
        if project == "DIT" or project is None:
            data = self._load_json("dit_open.json")
            tickets.extend([self._parse_ticket(issue) for issue in self._get_issues_from_data(data)])
        
        return tickets
    
    async def search_jql(self, jql: str, max_results: int = 50) -> List[JiraTicket]:
        """Search tickets (loads from JSON files)."""
        return self.search_jql_sync(jql, max_results)
    
    def search_jql_sync(self, jql: str, max_results: int = 50) -> List[JiraTicket]:
        """Search tickets from JSON files with basic filtering."""
        project = "JUPITER" if "JUPITER" in jql else ("DIT" if "DIT" in jql else None)
        tickets = self._get_all_tickets(project)
        return tickets[:max_results]
    
    # Predefined queries - load from JSON files and filter locally
    def get_my_open_tickets(self, project: str = "JUPITER") -> List[JiraTicket]:
        """Get all open tickets for a project."""
        return self._get_all_tickets(project)
    
    def get_in_progress(self, project: str = "JUPITER") -> List[JiraTicket]:
        """Get tickets currently in progress."""
        tickets = self._get_all_tickets(project)
        return [t for t in tickets if t.status.lower() == "in progress"]
    
    def get_high_priority(self, project: str = "JUPITER") -> List[JiraTicket]:
        """Get high/highest priority tickets."""
        tickets = self._get_all_tickets(project)
        return [t for t in tickets if t.priority.lower() in ("highest", "high")]
    
    def get_recently_updated(self, project: str = "JUPITER", days: int = 2) -> List[JiraTicket]:
        """Get tickets updated in the last N days."""
        data = self._load_json("recently_updated.json")
        tickets = [self._parse_ticket(issue) for issue in self._get_issues_from_data(data)]
        if project:
            tickets = [t for t in tickets if t.key.startswith(project)]
        return tickets
    
    def get_stale_tickets(self, project: str = "JUPITER", days: int = 5) -> List[JiraTicket]:
        """Get tickets not updated in N+ days."""
        data = self._load_json("stale.json")
        tickets = [self._parse_ticket(issue) for issue in self._get_issues_from_data(data)]
        if project:
            tickets = [t for t in tickets if t.key.startswith(project)]
        return tickets
    
    def get_upcoming_deadlines(self, project: str = "JUPITER", days: int = 7) -> List[JiraTicket]:
        """Get tickets with upcoming due dates."""
        data = self._load_json("time_sensitive.json")
        tickets = [self._parse_ticket(issue) for issue in self._get_issues_from_data(data)]
        if project:
            tickets = [t for t in tickets if t.key.startswith(project)]
        return [t for t in tickets if t.due_date and not t.is_overdue]
    
    def get_overdue(self, project: str = "JUPITER") -> List[JiraTicket]:
        """Get overdue tickets."""
        tickets = self._get_all_tickets(project)
        return [t for t in tickets if t.is_overdue]
    
    def get_tpe_tickets(self, project: str = "JUPITER") -> List[JiraTicket]:
        """Get TPE-labeled tickets."""
        tickets = self._get_all_tickets(project)
        return [t for t in tickets if "TPE" in [l.upper() for l in t.labels]]
    
    def get_open_ticket_keys(self) -> set:
        """Return the set of all open ticket keys across JUPITER and DIT.

        Used to detect when a task's linked Jira ticket has been resolved:
        if a key is NOT in this set, the ticket is likely closed.
        """
        keys = set()
        for filename in ("jupiter_open.json", "dit_open.json"):
            data = self._load_json(filename)
            for issue in self._get_issues_from_data(data):
                key = issue.get("key", "")
                if key:
                    keys.add(key)
        return keys

    def get_all_dashboard_data(self) -> Dict[str, Any]:
        """Get all data needed for the Jira dashboard."""
        return {
            "my_tickets": self.get_my_open_tickets(),
            "in_progress": self.get_in_progress(),
            "high_priority": self.get_high_priority(),
            "recently_updated": self.get_recently_updated(),
            "stale": self.get_stale_tickets(),
            "upcoming_deadlines": self.get_upcoming_deadlines(),
            "overdue": self.get_overdue(),
            "tpe_tickets": self.get_tpe_tickets(),
            "is_live": self.is_configured,
        }
    
    def get_data_freshness(self) -> str:
        """Get the timestamp of when the JSON data was last refreshed."""
        filepath = JIRA_DATA_DIR / "jupiter_open.json"
        if filepath.exists():
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            return mtime.strftime("%Y-%m-%d %H:%M")
        return "Unknown"
