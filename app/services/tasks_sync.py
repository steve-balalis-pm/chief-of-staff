"""TASKS.md bidirectional sync service."""
import re
import hashlib
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.accomplishment import Accomplishment

TASKS_MD_PATH = Path(__file__).parent.parent.parent / "TASKS.md"

class TasksSyncService:
    """Service for syncing tasks between database and TASKS.md."""
    
    SECTION_MAP = {
        "active_today": "## 🔴 Active — Today",
        "this_week": "## 🟡 This Week",
        "ongoing": "## 🟢 Ongoing / Background",
        "completed": "## ✅ Completed This Week",
        "waiting": "## ⏳ Waiting On",
        "questions": "## ❓ Questions Log",
    }
    
    SUBSECTION_MAP = {
        "high_priority": "### 🔴 HIGH PRIORITY",
        "medium_priority": "### 🟡 MEDIUM PRIORITY",
        "personal_dev": "### 🟢 PERSONAL DEVELOPMENT",
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def _parse_tasks_md(self) -> dict:
        """Parse TASKS.md and return structured data."""
        if not TASKS_MD_PATH.exists():
            return {}
        
        content = TASKS_MD_PATH.read_text()
        sections = {}
        current_section = None
        current_subsection = None
        
        for line in content.splitlines():
            # Check for section headers
            for key, header in self.SECTION_MAP.items():
                if line.startswith(header.split(" ")[0] + " " + header.split(" ")[1]) or header in line:
                    current_section = key
                    current_subsection = None
                    sections[current_section] = []
                    break
            
            # Check for subsection headers
            for key, header in self.SUBSECTION_MAP.items():
                if header in line:
                    current_subsection = key
                    break
            
            # Parse task items
            if current_section and line.strip().startswith("- ["):
                task = self._parse_task_line(line, current_section, current_subsection)
                if task:
                    sections[current_section].append(task)
        
        return sections
    
    def _parse_task_line(self, line: str, section: str, subsection: Optional[str]) -> Optional[dict]:
        """Parse a single task line from markdown."""
        match = re.match(r'^(\s*)- \[([ xX])\]\s*(.+)$', line)
        if not match:
            return None
        
        indent, done_char, content = match.groups()
        done = done_char.lower() == 'x'
        
        # Extract Jira links
        jira_match = re.search(r'\[([A-Z]+-\d+)\]\((https://[^)]+)\)', content)
        jira_link = jira_match.group(2) if jira_match else None
        jira_key = jira_match.group(1) if jira_match else None
        
        # Extract Zendesk links
        zd_match = re.search(r'ZD-(\d+)', content)
        zendesk_id = zd_match.group(1) if zd_match else None
        
        # Clean content - remove strikethrough markers
        clean_content = re.sub(r'~~(.+?)~~', r'\1', content)
        
        # Determine priority based on section/subsection
        priority = "medium"
        if subsection == "high_priority" or "HIGH PRIORITY" in (subsection or ""):
            priority = "high"
        elif "MEDIUM" in (subsection or ""):
            priority = "medium"
        
        return {
            "content": clean_content.strip(),
            "done": done,
            "section": section,
            "subsection": subsection,
            "priority": priority,
            "jira_link": jira_link,
            "jira_key": jira_key,
            "zendesk_id": zendesk_id,
            "line_hash": hashlib.md5(line.encode()).hexdigest()[:16],
            "indent": len(indent),
        }
    
    def sync_from_md(self):
        """Sync tasks from TASKS.md to database."""
        sections = self._parse_tasks_md()
        
        for section_key, tasks in sections.items():
            for task_data in tasks:
                existing = self.db.query(Task).filter(
                    Task.md_line_hash == task_data["line_hash"]
                ).first()
                
                if existing:
                    # Update existing task
                    existing.done = task_data["done"]
                    existing.content = task_data["content"]
                    existing.section = task_data["section"]
                    existing.subsection = task_data["subsection"]
                    existing.priority = task_data["priority"]
                    if task_data["done"] and not existing.completed_at:
                        existing.completed_at = datetime.now()
                else:
                    # Create new task
                    task = Task(
                        content=task_data["content"],
                        section=task_data["section"],
                        subsection=task_data["subsection"],
                        priority=task_data["priority"],
                        done=task_data["done"],
                        jira_link=task_data["jira_link"],
                        md_line_hash=task_data["line_hash"],
                        completed_at=datetime.now() if task_data["done"] else None
                    )
                    self.db.add(task)
        
        self.db.commit()
    
    def _write_tasks_md(self, sections: dict):
        """Write tasks back to TASKS.md."""
        if not TASKS_MD_PATH.exists():
            return
        
        content = TASKS_MD_PATH.read_text()
        # For now, we'll use a simpler approach - just modify specific lines
        # Full rewrite is complex due to preserving formatting
        TASKS_MD_PATH.write_text(content)
    
    def get_dashboard_data(self) -> dict:
        """Get task data for dashboard view with database IDs."""
        self.sync_from_md()
        return self._get_tasks_with_ids()
    
    def get_all_tasks(self) -> dict:
        """Get all tasks grouped by section with database IDs."""
        self.sync_from_md()
        return self._get_tasks_with_ids()
    
    def _get_tasks_with_ids(self) -> dict:
        """Get tasks from MD, enriched with database IDs for persistence."""
        sections = self._parse_tasks_md()
        
        # Enrich each task with its database ID
        for section_key, tasks in sections.items():
            for task in tasks:
                if task.get("line_hash"):
                    db_task = self.db.query(Task).filter(
                        Task.md_line_hash == task["line_hash"]
                    ).first()
                    if db_task:
                        task["id"] = db_task.id
                        task["done"] = db_task.done  # Use DB state as source of truth
        
        return sections
    
    def toggle_task(self, task_id: int) -> Optional[dict]:
        """Toggle a task's done status in both DB and TASKS.md."""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None
        
        task.done = not task.done
        if task.done:
            task.completed_at = datetime.now()
        else:
            task.completed_at = None
        
        self.db.commit()
        
        # Update TASKS.md
        self._update_task_in_md(task)
        
        return {"id": task.id, "done": task.done, "content": task.content}
    
    def toggle_task_by_hash(self, line_hash: str) -> Optional[dict]:
        """Toggle a task by its line hash (for tasks parsed from MD)."""
        task = self.db.query(Task).filter(Task.md_line_hash == line_hash).first()
        if not task:
            return None
        
        return self.toggle_task(task.id)
    
    def _update_task_in_md(self, task: Task):
        """Update a specific task in TASKS.md."""
        if not TASKS_MD_PATH.exists():
            return
        
        content = TASKS_MD_PATH.read_text()
        lines = content.splitlines()
        
        for i, line in enumerate(lines):
            if task.md_line_hash and hashlib.md5(line.encode()).hexdigest()[:16] == task.md_line_hash:
                # Toggle the checkbox
                if task.done:
                    lines[i] = line.replace("- [ ]", "- [x]")
                else:
                    lines[i] = line.replace("- [x]", "- [ ]")
                break
        
        TASKS_MD_PATH.write_text("\n".join(lines))
    
    def add_task(self, content: str, section: str = "this_week", priority: str = "medium") -> dict:
        """Add a new task to both DB and TASKS.md."""
        # Create in database
        task = Task(
            content=content,
            section=section,
            priority=priority,
            done=False
        )
        self.db.add(task)
        self.db.commit()
        
        # Add to TASKS.md
        self._add_task_to_md(content, section, priority)
        
        return {"id": task.id, "content": content, "section": section}
    
    def _add_task_to_md(self, content: str, section: str, priority: str):
        """Add a task to TASKS.md in the appropriate section."""
        if not TASKS_MD_PATH.exists():
            return
        
        md_content = TASKS_MD_PATH.read_text()
        lines = md_content.splitlines()
        
        # Find the section header
        section_header = self.SECTION_MAP.get(section, "## 🟡 This Week")
        insert_index = None
        
        for i, line in enumerate(lines):
            if section_header.split("—")[0].strip() in line:
                # Find the end of this section (next ## or ---)
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("## ") or lines[j].strip() == "---":
                        insert_index = j
                        break
                if insert_index is None:
                    insert_index = len(lines)
                break
        
        if insert_index:
            new_line = f"- [ ] **{content}**"
            lines.insert(insert_index, new_line)
            TASKS_MD_PATH.write_text("\n".join(lines))
    
    def move_task(self, task_id: int, target_section: str) -> bool:
        """Move a task to a different section."""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False
        
        task.section = target_section
        self.db.commit()
        
        # Note: Full markdown rewrite for move is complex, skip for now
        return True
    
    def delete_task(self, task_id: int) -> bool:
        """Delete a task."""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False
        
        self.db.delete(task)
        self.db.commit()
        return True
    
    def sync_completed_to_accomplishments(self):
        """Sync completed tasks to accomplishments table."""
        completed_tasks = self.db.query(Task).filter(
            Task.done == True,
            Task.completed_at != None
        ).all()
        
        for task in completed_tasks:
            # Check if already exists as accomplishment
            existing = self.db.query(Accomplishment).filter(
                Accomplishment.source_task_id == task.id
            ).first()
            
            if not existing:
                week_of = self._get_week_start(task.completed_at.date() if task.completed_at else date.today())
                
                acc = Accomplishment(
                    title=task.content[:200],
                    description=task.content,
                    category="task",
                    source_task_id=task.id,
                    completed_date=task.completed_at.date() if task.completed_at else date.today(),
                    week_of=week_of
                )
                self.db.add(acc)
        
        self.db.commit()
    
    def _get_week_start(self, d: date) -> date:
        """Get Monday of the week containing date d."""
        return d - timedelta(days=d.weekday())
