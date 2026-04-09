"""Notes router - meeting notes inbox."""
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.meeting_note import MeetingNote, ActionItem
from app.template_config import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def notes_inbox(request: Request, db: Session = Depends(get_db)):
    """Meeting notes inbox view."""
    from app.services.notes_parser import NotesParserService
    
    # Get unprocessed notes with their action items
    notes = db.query(MeetingNote).filter(
        MeetingNote.archived == False
    ).order_by(MeetingNote.created_at.desc()).all()
    
    return templates.TemplateResponse(request, "notes.html", {
        "notes": notes
    })

@router.post("/upload")
async def upload_note(
    file: UploadFile = File(None),
    content: str = Form(None),
    title: str = Form(None),
    db: Session = Depends(get_db)
):
    """Upload or paste a meeting note."""
    from app.services.notes_parser import NotesParserService
    
    parser = NotesParserService()
    
    if file:
        file_content = await file.read()
        text_content = parser.extract_text(file_content, file.filename)
        note_title = title or file.filename
    elif content:
        text_content = content
        note_title = title or "Pasted Note"
    else:
        return {"error": "No content provided"}
    
    # Create meeting note
    note = MeetingNote(
        filename=file.filename if file else None,
        title=note_title,
        content=text_content,
        processed=False
    )
    db.add(note)
    db.flush()
    
    # Extract action items
    action_items = parser.extract_action_items(text_content)
    for item_text, assignee in action_items:
        action = ActionItem(
            note_id=note.id,
            text=item_text,
            assignee=assignee
        )
        db.add(action)
    
    db.commit()
    return {"id": note.id, "action_items_count": len(action_items)}

@router.post("/action/{action_id}/push")
async def push_action_to_tasks(
    action_id: int,
    section: str = Form("this_week"),
    db: Session = Depends(get_db)
):
    """Push an action item to TASKS.md."""
    from app.services.tasks_sync import TasksSyncService
    
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        return {"error": "Not found"}
    
    sync_service = TasksSyncService(db)
    task = sync_service.add_task(action.text, section, "medium")
    
    action.pushed_to_tasks = True
    action.task_id = task.get("id")
    db.commit()
    
    return {"pushed": True, "task_id": task.get("id")}

@router.post("/action/{action_id}/dismiss")
async def dismiss_action(action_id: int, db: Session = Depends(get_db)):
    """Dismiss an action item."""
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        return {"error": "Not found"}
    
    action.dismissed = True
    db.commit()
    return {"dismissed": True}

@router.post("/{note_id}/archive")
async def archive_note(note_id: int, db: Session = Depends(get_db)):
    """Archive a processed note."""
    note = db.query(MeetingNote).filter(MeetingNote.id == note_id).first()
    if not note:
        return {"error": "Not found"}
    
    note.archived = True
    note.processed = True
    db.commit()
    return {"archived": True}
