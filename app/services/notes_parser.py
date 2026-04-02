"""Meeting notes parser service - extract action items."""
import os
import re
from typing import List, Tuple, Optional
from pathlib import Path

# Configure your name for action item extraction
# Set via environment variable or edit directly
MY_NAME = os.environ.get("MY_NAME", "User")
MY_NAME_VARIANTS = os.environ.get("MY_NAME_VARIANTS", MY_NAME).split(",")

class NotesParserService:
    """Service for parsing meeting notes and extracting action items."""
    
    def __init__(self):
        # Build patterns dynamically based on configured name
        name_pattern = "|".join(MY_NAME_VARIANTS)
        self.ACTION_PATTERNS = [
            r'(?:action item|todo|follow up|follow-up|AI)[\s:]+(.+)',
            rf'(?:{name_pattern})[\s:]+(.+)',
            rf'(?:owner)[\s:]+(?:{name_pattern})[\s,]+(.+)',
            r'- \[ \]\s*(.+)',
            r'action:\s*(.+)',
        ]
        
        # Customize these for your team members
        self.ASSIGNEE_PATTERNS = [
            (rf'\b({name_pattern})\b', MY_NAME),
            # Add more team members as needed:
            # (r'\b(TeammateName)\b', 'Teammate'),
        ]
        
        self.my_name_pattern = name_pattern
    
    def extract_text(self, file_content: bytes, filename: str) -> str:
        """Extract text from file content based on file type."""
        ext = Path(filename).suffix.lower()
        
        if ext == '.txt' or ext == '.md':
            return file_content.decode('utf-8', errors='ignore')
        
        elif ext == '.docx':
            try:
                from docx import Document
                from io import BytesIO
                doc = Document(BytesIO(file_content))
                return '\n'.join([para.text for para in doc.paragraphs])
            except Exception as e:
                return f"Error parsing .docx: {e}"
        
        else:
            return file_content.decode('utf-8', errors='ignore')
    
    def extract_action_items(self, content: str) -> List[Tuple[str, Optional[str]]]:
        """
        Extract action items from note content.
        Returns list of (action_text, assignee) tuples.
        """
        items = []
        seen = set()
        
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            
            for pattern in self.ACTION_PATTERNS:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    action_text = match.group(1).strip()
                    if action_text and action_text not in seen:
                        assignee = self._extract_assignee(line)
                        items.append((action_text, assignee))
                        seen.add(action_text)
                    break
        
        # Also look for table rows with Owner column containing my name
        table_items = self._extract_from_tables(content)
        for item, assignee in table_items:
            if item not in seen:
                items.append((item, assignee))
                seen.add(item)
        
        return items
    
    def _extract_assignee(self, text: str) -> Optional[str]:
        """Extract assignee from text."""
        for pattern, name in self.ASSIGNEE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return name
        return None
    
    def _extract_from_tables(self, content: str) -> List[Tuple[str, Optional[str]]]:
        """Extract action items from markdown tables."""
        items = []
        lines = content.splitlines()
        
        in_table = False
        owner_col = -1
        action_col = -1
        
        for line in lines:
            if '|' in line:
                cells = [c.strip() for c in line.split('|')]
                
                # Check if this is a header row
                if any(c.lower() in ['owner', 'assignee'] for c in cells):
                    in_table = True
                    for i, c in enumerate(cells):
                        if c.lower() in ['owner', 'assignee']:
                            owner_col = i
                        if c.lower() in ['action', 'item', 'task', 'description']:
                            action_col = i
                    continue
                
                # Check if separator row
                if all(c.replace('-', '').replace(':', '').strip() == '' for c in cells if c):
                    continue
                
                # Data row
                if in_table and owner_col >= 0:
                    if len(cells) > owner_col:
                        owner = cells[owner_col]
                        if re.search(rf'\b({self.my_name_pattern})\b', owner, re.IGNORECASE):
                            action_text = cells[action_col] if action_col >= 0 and len(cells) > action_col else ' '.join(cells)
                            if action_text:
                                items.append((action_text, MY_NAME))
            else:
                in_table = False
                owner_col = -1
                action_col = -1
        
        return items
