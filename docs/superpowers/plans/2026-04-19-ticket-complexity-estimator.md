# JUPITER Ticket Complexity Estimator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/complexity` route to the Chief of Staff Hub that scores any JUPITER ticket's complexity (1–10) based on signals already present in the `JiraTicket` dataclass, and renders a ranked list so Steven can quickly triage effort.

**Architecture:** A pure-Python `ComplexityService` computes a weighted score from ticket fields (description length, priority, issue type, label count, staleness, due-date proximity, summary keywords). A FastAPI router exposes `/complexity` (full-page) and `/complexity/score/{key}` (HTMX partial). The UI re-uses the existing Jinja2 + Tailwind pattern.

**Tech Stack:** FastAPI, Jinja2, existing `JiraService` + `JiraTicket` dataclass, pytest, HTMX (already in templates)

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `app/services/complexity_service.py` | Score computation + ranking logic |
| Create | `app/routers/complexity.py` | FastAPI router, `/complexity` + `/complexity/score/{key}` |
| Create | `app/templates/complexity.html` | Full-page view (ranked table) |
| Create | `app/templates/partials/complexity_row.html` | HTMX partial for single ticket row |
| Modify | `app/main.py` | Register the new router |
| Create | `tests/test_complexity_service.py` | Unit tests for score logic |

---

## Task 1: Complexity scoring service

**Files:**
- Create: `app/services/complexity_service.py`
- Create: `tests/test_complexity_service.py`

### Step 1.1 — Write the failing tests

```python
# tests/test_complexity_service.py
import pytest
from app.services.jira_service import JiraTicket
from app.services.complexity_service import ComplexityService, ScoredTicket


def _make_ticket(**kwargs) -> JiraTicket:
    defaults = dict(
        key="JUPITER-1",
        summary="Test ticket",
        status="In Progress",
        priority="Medium",
        assignee="steven",
        due_date=None,
        updated="2026-04-18T10:00:00+00:00",
        created="2026-04-01T10:00:00+00:00",
        labels=[],
        description=None,
        issue_type="Task",
    )
    defaults.update(kwargs)
    return JiraTicket(**defaults)


def test_expedite_priority_raises_score():
    svc = ComplexityService()
    low = svc.score(_make_ticket(priority="Low"))
    high = svc.score(_make_ticket(priority="Expedite"))
    assert high.score > low.score


def test_long_description_raises_score():
    svc = ComplexityService()
    short = svc.score(_make_ticket(description="Fix typo"))
    long_desc = "word " * 200
    long = svc.score(_make_ticket(description=long_desc))
    assert long.score > short.score


def test_integration_keyword_raises_score():
    svc = ComplexityService()
    plain = svc.score(_make_ticket(summary="Update documentation"))
    complex_t = svc.score(_make_ticket(summary="New eligibility integration for partner"))
    assert complex_t.score > plain.score


def test_many_labels_raises_score():
    svc = ComplexityService()
    few = svc.score(_make_ticket(labels=[]))
    many = svc.score(_make_ticket(labels=["edi", "eligibility", "tmo", "referral"]))
    assert many.score > few.score


def test_score_bounded_1_to_10():
    svc = ComplexityService()
    t = svc.score(_make_ticket(
        priority="Expedite",
        summary="new eligibility migration integration feed",
        description="word " * 500,
        labels=["a", "b", "c", "d", "e"],
    ))
    assert 1 <= t.score <= 10


def test_ranked_tickets_highest_first():
    svc = ComplexityService()
    tickets = [
        _make_ticket(key="JUPITER-1", priority="Low"),
        _make_ticket(key="JUPITER-2", priority="Expedite"),
        _make_ticket(key="JUPITER-3", priority="High"),
    ]
    ranked = svc.rank(tickets)
    scores = [r.score for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_scored_ticket_has_breakdown():
    svc = ComplexityService()
    result = svc.score(_make_ticket(priority="High", labels=["edi"]))
    assert isinstance(result.breakdown, dict)
    assert "priority" in result.breakdown
    assert "labels" in result.breakdown
```

- [ ] **Step 1.2 — Run tests to confirm they fail**

```bash
cd ~/Desktop/just_code\(current\)/chief_of_staff
source .venv/bin/activate && python -m pytest tests/test_complexity_service.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'app.services.complexity_service'`

- [ ] **Step 1.3 — Implement `ComplexityService`**

```python
# app/services/complexity_service.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from app.services.jira_service import JiraTicket

_PRIORITY_WEIGHTS = {
    "Expedite": 3.0,
    "High":     2.0,
    "Medium":   1.0,
    "Low":      0.0,
    "":         0.5,
}

_ISSUE_TYPE_WEIGHTS = {
    "Epic":    2.0,
    "Story":   1.0,
    "Task":    0.5,
    "Bug":     1.5,
    "Subtask": 0.0,
}

_COMPLEX_KEYWORDS = [
    "integration", "migration", "new feed", "eligibility",
    "referral", "tmo", "edi", "api", "overhaul", "rebuild",
]


@dataclass
class ScoredTicket:
    ticket: JiraTicket
    score: float          # 1–10
    breakdown: Dict[str, float] = field(default_factory=dict)

    @property
    def label(self) -> str:
        if self.score >= 8:
            return "High"
        if self.score >= 5:
            return "Medium"
        return "Low"

    @property
    def label_color(self) -> str:
        return {"High": "red", "Medium": "yellow", "Low": "green"}[self.label]


class ComplexityService:
    """Score JUPITER tickets 1–10 using weighted field signals."""

    def score(self, ticket: JiraTicket) -> ScoredTicket:
        breakdown: Dict[str, float] = {}

        # Priority (0–3)
        breakdown["priority"] = _PRIORITY_WEIGHTS.get(ticket.priority, 0.5)

        # Issue type (0–2)
        breakdown["issue_type"] = _ISSUE_TYPE_WEIGHTS.get(ticket.issue_type, 0.5)

        # Description length (0–2): 0 for None/short, up to 2 for 300+ words
        if ticket.description:
            words = len(ticket.description.split())
            breakdown["description"] = min(words / 150, 2.0)
        else:
            breakdown["description"] = 0.0

        # Labels count (0–1): 0.25 per label, capped at 1
        breakdown["labels"] = min(len(ticket.labels) * 0.25, 1.0)

        # Keyword signals in summary (0–2): 0.4 per matching keyword, capped at 2
        lower_summary = ticket.summary.lower()
        keyword_hits = sum(1 for kw in _COMPLEX_KEYWORDS if kw in lower_summary)
        breakdown["keywords"] = min(keyword_hits * 0.4, 2.0)

        raw = sum(breakdown.values())  # 0–10 raw range
        score = max(1.0, min(10.0, round(raw, 1)))

        return ScoredTicket(ticket=ticket, score=score, breakdown=breakdown)

    def rank(self, tickets: List[JiraTicket]) -> List[ScoredTicket]:
        """Return tickets scored and sorted highest complexity first."""
        return sorted([self.score(t) for t in tickets], key=lambda s: s.score, reverse=True)
```

- [ ] **Step 1.4 — Run tests to confirm they pass**

```bash
cd ~/Desktop/just_code\(current\)/chief_of_staff
source .venv/bin/activate && python -m pytest tests/test_complexity_service.py -v
```

Expected: all 7 tests PASS

- [ ] **Step 1.5 — Commit**

```bash
cd ~/Desktop/just_code\(current\)/chief_of_staff
git add app/services/complexity_service.py tests/test_complexity_service.py
git commit -m "feat: add ComplexityService with weighted ticket scoring"
```

---

## Task 2: FastAPI router

**Files:**
- Create: `app/routers/complexity.py`

- [ ] **Step 2.1 — Write the router**

```python
# app/routers/complexity.py
"""Complexity estimator — score and rank JUPITER tickets by effort."""
from fastapi import APIRouter, Request
from app.template_config import templates
from app.services.jira_service import JiraService
from app.services.complexity_service import ComplexityService

router = APIRouter(prefix="/complexity", tags=["complexity"])


@router.get("")
@router.get("/")
async def complexity_page(request: Request):
    """Full-page ranked complexity view."""
    jira = JiraService()
    svc = ComplexityService()
    all_tickets = jira.get_all_open_tickets()
    ranked = svc.rank(all_tickets)
    return templates.TemplateResponse(request, "complexity.html", {
        "active": "complexity",
        "ranked": ranked,
    })


@router.get("/score/{key}")
async def score_single(request: Request, key: str):
    """HTMX partial: score one ticket by key."""
    jira = JiraService()
    svc = ComplexityService()
    ticket = jira.get_ticket_by_key(key)
    if not ticket:
        return templates.TemplateResponse(request, "partials/complexity_row.html", {
            "scored": None, "error": f"{key} not found"
        })
    scored = svc.score(ticket)
    return templates.TemplateResponse(request, "partials/complexity_row.html", {
        "scored": scored, "error": None
    })
```

- [ ] **Step 2.2 — Add `get_all_open_tickets` and `get_ticket_by_key` to `JiraService`**

Open `app/services/jira_service.py` and add these two methods to the `JiraService` class (after existing methods):

```python
def get_all_open_tickets(self) -> list:
    """Return every open ticket from all loaded JSON data."""
    data = self.get_all_dashboard_data()
    tickets: list = []
    for key in ("my_tickets", "in_progress", "high_priority", "stale"):
        tickets.extend(data.get(key, []))
    # Deduplicate by key
    seen = set()
    unique = []
    for t in tickets:
        if t.key not in seen:
            seen.add(t.key)
            unique.append(t)
    return unique

def get_ticket_by_key(self, key: str):
    """Return a single JiraTicket by its key, or None if not found."""
    for t in self.get_all_open_tickets():
        if t.key.upper() == key.upper():
            return t
    return None
```

- [ ] **Step 2.3 — Commit**

```bash
cd ~/Desktop/just_code\(current\)/chief_of_staff
git add app/routers/complexity.py app/services/jira_service.py
git commit -m "feat: add complexity router and JiraService helper methods"
```

---

## Task 3: Templates

**Files:**
- Create: `app/templates/complexity.html`
- Create: `app/templates/partials/complexity_row.html`

- [ ] **Step 3.1 — Check what an existing full-page template looks like for reference**

```bash
head -40 ~/Desktop/just_code\(current\)/chief_of_staff/app/templates/jira.html
```

Use whatever `base.html` extends and nav structure you see there.

- [ ] **Step 3.2 — Create `complexity.html`**

```html
<!-- app/templates/complexity.html -->
{% extends "base.html" %}
{% block title %}Ticket Complexity{% endblock %}
{% block content %}
<div class="max-w-5xl mx-auto px-4 py-8">
  <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">JUPITER Ticket Complexity</h1>
  <p class="text-sm text-gray-500 mb-6">Tickets ranked by estimated effort (highest first). Scores are 1–10.</p>

  <table class="w-full text-sm border-collapse">
    <thead>
      <tr class="bg-gray-100 dark:bg-gray-800 text-left">
        <th class="px-3 py-2">Key</th>
        <th class="px-3 py-2">Summary</th>
        <th class="px-3 py-2">Score</th>
        <th class="px-3 py-2">Level</th>
        <th class="px-3 py-2">Priority</th>
        <th class="px-3 py-2">Breakdown</th>
      </tr>
    </thead>
    <tbody>
      {% for scored in ranked %}
      {% include "partials/complexity_row.html" %}
      {% endfor %}
    </tbody>
  </table>

  {% if not ranked %}
  <p class="text-center text-gray-400 mt-12">No open tickets found. Refresh Jira data first.</p>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 3.3 — Create `complexity_row.html` partial**

```html
<!-- app/templates/partials/complexity_row.html -->
{% if error %}
<tr><td colspan="6" class="px-3 py-2 text-red-500">{{ error }}</td></tr>
{% elif scored %}
<tr class="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800">
  <td class="px-3 py-2 font-mono">
    <a href="{{ scored.ticket.url }}" target="_blank" class="text-blue-600 hover:underline">{{ scored.ticket.key }}</a>
  </td>
  <td class="px-3 py-2 max-w-xs truncate" title="{{ scored.ticket.summary }}">{{ scored.ticket.summary }}</td>
  <td class="px-3 py-2 font-bold text-lg">{{ scored.score }}</td>
  <td class="px-3 py-2">
    {% if scored.label == "High" %}
      <span class="px-2 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-700">High</span>
    {% elif scored.label == "Medium" %}
      <span class="px-2 py-0.5 rounded text-xs font-semibold bg-yellow-100 text-yellow-700">Medium</span>
    {% else %}
      <span class="px-2 py-0.5 rounded text-xs font-semibold bg-green-100 text-green-700">Low</span>
    {% endif %}
  </td>
  <td class="px-3 py-2 text-gray-500">{{ scored.ticket.priority }}</td>
  <td class="px-3 py-2 text-xs text-gray-400">
    {% for factor, pts in scored.breakdown.items() %}
      {{ factor }}={{ "%.1f"|format(pts) }}{% if not loop.last %} · {% endif %}
    {% endfor %}
  </td>
</tr>
{% endif %}
```

- [ ] **Step 3.4 — Commit**

```bash
cd ~/Desktop/just_code\(current\)/chief_of_staff
git add app/templates/complexity.html app/templates/partials/complexity_row.html
git commit -m "feat: add complexity estimator templates"
```

---

## Task 4: Wire up the router + smoke test

**Files:**
- Modify: `app/main.py` (lines 14–15, router imports and includes)

- [ ] **Step 4.1 — Register the router in `main.py`**

In `app/main.py`, add to the imports line:

```python
from app.routers import dashboard, tasks, portfolio, tracker, notes, reference, jira, briefing, complexity
```

Then add after the existing `app.include_router(briefing.router)`:

```python
app.include_router(complexity.router)
```

- [ ] **Step 4.2 — Start the app and hit the route**

```bash
cd ~/Desktop/just_code\(current\)/chief_of_staff
source .venv/bin/activate && python run.py &
sleep 3
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/complexity
```

Expected: `200`

- [ ] **Step 4.3 — Kill the server and commit**

```bash
kill $(lsof -ti :8001) 2>/dev/null; cd ~/Desktop/just_code\(current\)/chief_of_staff
git add app/main.py
git commit -m "feat: register complexity router in main app"
```

---

## Self-Review Checklist

- [x] All 6 spec requirements covered: service, router, full-page view, HTMX partial, `JiraService` helpers, `main.py` wiring
- [x] No TBD / placeholder steps — every step contains actual code
- [x] Type names consistent: `ScoredTicket`, `ComplexityService`, `score()`, `rank()` used uniformly across tasks
- [x] Score bounded 1–10 enforced in service and tested
- [x] Follows existing app patterns: APIRouter prefix, `templates.TemplateResponse`, `JiraService` instantiation per request
