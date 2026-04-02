"""Context loader service - parse CLAUDE.md for reference data."""
import re
from pathlib import Path
from typing import Dict, List, Any

CLAUDE_MD_PATH = Path(__file__).parent.parent.parent.parent / "CLAUDE.md"

class ContextLoaderService:
    """Service for loading context from CLAUDE.md."""
    
    def load_all(self) -> Dict[str, Any]:
        """Load all context data from CLAUDE.md."""
        if not CLAUDE_MD_PATH.exists():
            return self._get_defaults()
        
        content = CLAUDE_MD_PATH.read_text()
        
        return {
            "teams": self._parse_teams(content),
            "tools": self._parse_tools(content),
            "goals": self._parse_goals(content),
            "terminology": self._parse_terminology(content),
        }
    
    def _parse_teams(self, content: str) -> Dict[str, List[Dict]]:
        """Parse team member tables from CLAUDE.md."""
        teams = {
            "jupiter": [],
            "moneyball": [],
            "cross_functional": []
        }
        
        # Parse Jupiter team
        jupiter_match = re.search(r'### Jupiter Team\s*\n(.*?)(?=###|\Z)', content, re.DOTALL)
        if jupiter_match:
            teams["jupiter"] = self._parse_table(jupiter_match.group(1))
        
        # Parse Moneyball team
        moneyball_match = re.search(r'### Moneyball Team\s*\n(.*?)(?=###|\Z)', content, re.DOTALL)
        if moneyball_match:
            teams["moneyball"] = self._parse_table(moneyball_match.group(1))
        
        # Parse cross-functional
        cross_match = re.search(r'### Cross-Functional Contacts\s*\n(.*?)(?=###|---|\Z)', content, re.DOTALL)
        if cross_match:
            teams["cross_functional"] = self._parse_table(cross_match.group(1))
        
        return teams
    
    def _parse_table(self, table_text: str) -> List[Dict]:
        """Parse a markdown table into list of dicts."""
        rows = []
        lines = [l.strip() for l in table_text.strip().splitlines() if l.strip() and '|' in l]
        
        if len(lines) < 2:
            return rows
        
        # Parse header
        header = [c.strip() for c in lines[0].split('|') if c.strip()]
        
        # Skip separator line
        data_start = 1
        if lines[1].replace('|', '').replace('-', '').replace(':', '').strip() == '':
            data_start = 2
        
        for line in lines[data_start:]:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) >= len(header):
                row = {}
                for i, h in enumerate(header):
                    key = h.lower().replace(' ', '_').replace('/', '_')
                    row[key] = cells[i] if i < len(cells) else ''
                rows.append(row)
        
        return rows
    
    def _parse_tools(self, content: str) -> List[Dict]:
        """Parse tooling table from CLAUDE.md."""
        tools_match = re.search(r'## 7\. Tooling & Links\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
        if tools_match:
            return self._parse_table(tools_match.group(1))
        return []
    
    def _parse_goals(self, content: str) -> Dict[str, List[str]]:
        """Parse 2026 goals from CLAUDE.md."""
        goals = {"jupiter": [], "moneyball": []}
        
        goals_match = re.search(r'## 3\. 2026 Team Goals.*?\n(.*?)(?=##|\Z)', content, re.DOTALL)
        if not goals_match:
            return goals
        
        goals_text = goals_match.group(1)
        
        # Jupiter goals
        jupiter_match = re.search(r'### Jupiter.*?\n(.*?)(?=###|\Z)', goals_text, re.DOTALL)
        if jupiter_match:
            for line in jupiter_match.group(1).splitlines():
                if line.strip().startswith('-'):
                    goal = line.strip()[1:].strip()
                    if goal.startswith('**'):
                        goal = goal.replace('**', '').strip()
                        goals["jupiter"].insert(0, goal)  # Bold = primary
                    else:
                        goals["jupiter"].append(goal)
        
        # Moneyball goals
        moneyball_match = re.search(r'### Moneyball.*?\n(.*?)(?=###|---|\Z)', goals_text, re.DOTALL)
        if moneyball_match:
            for line in moneyball_match.group(1).splitlines():
                if line.strip().startswith('-'):
                    goal = line.strip()[1:].strip()
                    if goal.startswith('**'):
                        goal = goal.replace('**', '').strip()
                        goals["moneyball"].insert(0, goal)
                    else:
                        goals["moneyball"].append(goal)
        
        return goals
    
    def _parse_terminology(self, content: str) -> List[Dict]:
        """Parse terminology tables from CLAUDE.md."""
        terms = []
        
        # Find terminology section
        term_match = re.search(r'## 6\. Domain Knowledge & Terminology\s*\n(.*?)(?=##|\Z)', content, re.DOTALL)
        if term_match:
            # Parse all tables in this section
            tables = re.findall(r'\|[^\n]+\|(?:\n\|[^\n]+\|)+', term_match.group(1))
            for table in tables:
                terms.extend(self._parse_table(table))
        
        return terms
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Return default context if CLAUDE.md not found."""
        return {
            "teams": {
                "jupiter": [
                    {"name": "Cara Stotz", "role_focus": "Jupiter team lead"},
                    {"name": "Ellen Naroditskiy", "role_focus": "Zendesk, IB change tracking"},
                    {"name": "Ian Sniffen", "role_focus": "SQL, stored procedures"},
                    {"name": "Janet Delage", "role_focus": "Data/tables, Databricks"},
                ],
                "moneyball": [
                    {"name": "Robert", "role_focus": "Docs lead"},
                    {"name": "Alexis", "role_focus": "Feed handoff coordination"},
                ],
                "cross_functional": [
                    {"name": "Chris Capobianco", "role_focus": "Manager"},
                    {"name": "Bill McCloskey", "role_focus": "IB SME"},
                ]
            },
            "tools": [],
            "goals": {"jupiter": [], "moneyball": []},
            "terminology": []
        }
