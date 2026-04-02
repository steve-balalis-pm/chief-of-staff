#!/usr/bin/env python3
"""
generate_tasks_html.py
Reads TASKS.md and generates tasks.html using markdown parsing.
Run: python3 generate_tasks_html.py

Usage from Claude: "Regenerate my tasks HTML" → run this script
"""

import re
import os
from datetime import datetime

TASKS_MD = os.path.join(os.path.dirname(__file__), "TASKS.md")
OUTPUT_HTML = os.path.join(os.path.dirname(__file__), "tasks.html")


def parse_tasks(md_content):
    """Parse TASKS.md and return structured sections."""
    sections = []
    current_section = None
    current_subsection = None

    for line in md_content.splitlines():
        # Top-level section headers (##)
        if line.startswith("## "):
            if current_section:
                sections.append(current_section)
            current_section = {
                "title": line[3:].strip(),
                "items": [],
                "subsections": [],
            }
            current_subsection = None
            continue

        if current_section is None:
            continue

        # Subsection headers (###)
        if line.startswith("### "):
            current_subsection = {"label": line[4:].strip(), "items": []}
            current_section["subsections"].append(current_subsection)
            continue

        # Task items
        if line.strip().startswith("- [ ]") or line.strip().startswith("- [x]"):
            done = line.strip().startswith("- [x]")
            text = re.sub(r"^- \[.\] ", "", line.strip())
            # Strip strikethrough markdown ~~text~~
            text = re.sub(r"~~(.+?)~~", r"\1", text)
            item = {"type": "task", "done": done, "text": text, "sub": []}
            target = current_subsection["items"] if current_subsection else current_section["items"]
            target.append(item)
            continue

        # Sub-bullet items (indented)
        if re.match(r"^\s{2,}- ", line):
            text = re.sub(r"^\s+-\s+", "", line)
            target = current_subsection["items"] if current_subsection else current_section["items"]
            if target and target[-1].get("type") == "task":
                target[-1]["sub"].append(text)
            continue

        # Plain text lines (notes)
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
            target = current_subsection["items"] if current_subsection else current_section["items"]
            target.append({"type": "note", "text": stripped})

    if current_section:
        sections.append(current_section)

    return sections


def linkify(text):
    """Convert markdown links and bold to HTML."""
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic / em
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Markdown links
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    # Inline code
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    # Strikethrough
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)
    return text


def section_color(title):
    t = title.lower()
    if "high priority" in t or "🔴" in t:
        return "red"
    if "medium" in t or "🟡" in t:
        return "yellow"
    if "this week" in t or "🟠" in t:
        return "orange"
    if "ongoing" in t or "background" in t or "🟢" in t:
        return "green"
    if "completed" in t or "✅" in t:
        return "gray"
    if "question" in t or "❓" in t:
        return "blue"
    if "draft" in t or "📋" in t:
        return "purple"
    if "note" in t or "📝" in t:
        return "gray"
    return "blue"


def count_tasks(sections):
    open_count = done_count = 0
    for s in sections:
        all_items = s["items"] + [i for sub in s.get("subsections", []) for i in sub["items"]]
        for item in all_items:
            if item["type"] == "task":
                if item["done"]:
                    done_count += 1
                else:
                    open_count += 1
    return open_count, done_count


def render_items(items):
    html = ""
    for item in items:
        if item["type"] == "task":
            done_class = " done" if item["done"] else ""
            check_class = ' class="checkbox checked"' if item["done"] else ' class="checkbox"'
            check_inner = "✓" if item["done"] else ""
            html += f'<div class="task-item{done_class}">\n'
            html += f'  <div{check_class}>{check_inner}</div>\n'
            html += f'  <div class="task-text">{linkify(item["text"])}</div>\n'
            if item.get("sub"):
                html += '  <div class="task-sub">\n'
                for sub in item["sub"]:
                    html += f'    <li>{linkify(sub)}</li>\n'
                html += '  </div>\n'
            html += '</div>\n'
        elif item["type"] == "note":
            text = item["text"]
            if text.startswith(">"):
                text = text[1:].strip()
                html += f'<blockquote>{linkify(text)}</blockquote>\n'
            else:
                html += f'<div class="note-item">{linkify(text)}</div>\n'
    return html


def generate_html(sections, last_updated):
    open_count, done_count = count_tasks(sections)
    ongoing_count = sum(
        1 for s in sections
        for item in (s["items"] + [i for sub in s.get("subsections", []) for i in sub["items"]])
        if item["type"] == "task" and not item["done"] and "ongoing" in s["title"].lower()
    )

    body = ""
    for s in sections:
        color = section_color(s["title"])
        body += f'<div class="section">\n'
        body += f'  <div class="section-header {color}">{s["title"]}</div>\n'
        body += '  <div class="task-list">\n'
        body += render_items(s["items"])
        for sub in s.get("subsections", []):
            body += f'  <div class="subsection-label">{sub["label"]}</div>\n'
            body += render_items(sub["items"])
        body += '  </div>\n</div>\n\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Steven's Task List</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', sans-serif; background: #f0f2f5; color: #1a1a2e; font-size: 14px; line-height: 1.6; }}
  .header {{ background: #1e2d4f; color: white; padding: 20px 32px; display: flex; justify-content: space-between; align-items: center; }}
  .header h1 {{ font-size: 20px; font-weight: 700; }}
  .header .meta {{ font-size: 12px; opacity: 0.7; margin-top: 4px; }}
  .header .stats {{ display: flex; gap: 20px; font-size: 13px; }}
  .stat {{ text-align: center; }}
  .stat .num {{ font-size: 22px; font-weight: 700; display: block; }}
  .stat .label {{ opacity: 0.7; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 24px 20px; }}
  .section {{ background: white; border-radius: 8px; margin-bottom: 16px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.07); }}
  .section-header {{ padding: 12px 20px; font-weight: 600; font-size: 13px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid #f0f0f0; }}
  .section-header.red {{ background: #fff5f5; color: #c0392b; border-left: 4px solid #e74c3c; }}
  .section-header.orange {{ background: #fffaf0; color: #d35400; border-left: 4px solid #e67e22; }}
  .section-header.yellow {{ background: #fffde7; color: #b7791f; border-left: 4px solid #f6c90e; }}
  .section-header.green {{ background: #f0fff4; color: #276749; border-left: 4px solid #38a169; }}
  .section-header.blue {{ background: #ebf8ff; color: #2b6cb0; border-left: 4px solid #4299e1; }}
  .section-header.gray {{ background: #f7fafc; color: #4a5568; border-left: 4px solid #a0aec0; }}
  .section-header.purple {{ background: #faf5ff; color: #553c9a; border-left: 4px solid #805ad5; }}
  .task-list {{ padding: 4px 0; }}
  .task-item {{ padding: 10px 20px 10px 48px; border-bottom: 1px solid #f9f9f9; position: relative; transition: background 0.1s; }}
  .task-item:last-child {{ border-bottom: none; }}
  .task-item:hover {{ background: #fafafa; }}
  .task-item.done {{ opacity: 0.5; }}
  .task-item.done .task-text {{ text-decoration: line-through; color: #999; }}
  .checkbox {{ position: absolute; left: 20px; top: 12px; width: 16px; height: 16px; border: 2px solid #cbd5e0; border-radius: 4px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}
  .checkbox.checked {{ background: #38a169; border-color: #38a169; color: white; font-size: 10px; }}
  .task-text {{ font-size: 13.5px; color: #2d3748; }}
  .task-text strong {{ color: #1a202c; }}
  .task-text a {{ color: #4299e1; text-decoration: none; }}
  .task-text a:hover {{ text-decoration: underline; }}
  .task-sub {{ margin-top: 4px; padding-left: 12px; border-left: 2px solid #e2e8f0; color: #718096; font-size: 12.5px; }}
  .task-sub li {{ list-style: none; padding: 2px 0; }}
  .subsection-label {{ padding: 8px 20px 4px 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.6px; color: #a0aec0; }}
  .note-item {{ padding: 8px 20px; font-size: 13px; color: #4a5568; border-bottom: 1px solid #f9f9f9; }}
  .note-item:last-child {{ border-bottom: none; }}
  .note-item a {{ color: #4299e1; text-decoration: none; }}
  em {{ color: #718096; font-style: italic; }}
  blockquote {{ border-left: 3px solid #cbd5e0; padding-left: 12px; color: #718096; font-style: italic; margin: 6px 20px; font-size: 13px; }}
  code {{ background: #edf2f7; padding: 1px 5px; border-radius: 3px; font-size: 12px; }}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>📋 Steven's Task List</h1>
    <div class="meta">Last updated: {last_updated} &nbsp;·&nbsp; Source: chief_of_staff/TASKS.md</div>
  </div>
  <div class="stats">
    <div class="stat"><span class="num">{open_count}</span><span class="label">Open</span></div>
    <div class="stat"><span class="num">{done_count}</span><span class="label">Done</span></div>
  </div>
</div>
<div class="container">
{body}
</div>
</body>
</html>"""


if __name__ == "__main__":
    with open(TASKS_MD, "r") as f:
        md = f.read()

    # Extract last updated date from file
    match = re.search(r"_Last updated: (.+?)_", md)
    last_updated = match.group(1) if match else datetime.today().strftime("%Y-%m-%d")

    sections = parse_tasks(md)
    html = generate_html(sections, last_updated)

    with open(OUTPUT_HTML, "w") as f:
        f.write(html)

    open_count, done_count = count_tasks(sections)
    print(f"✅ tasks.html regenerated — {open_count} open, {done_count} done")
    print(f"   → {OUTPUT_HTML}")
