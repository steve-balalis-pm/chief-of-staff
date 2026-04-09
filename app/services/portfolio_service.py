"""Portfolio service - accomplishments management."""
import logging
from datetime import date, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.accomplishment import Accomplishment
from app.models.initiative import Initiative

logger = logging.getLogger("chief_of_staff.portfolio")

# Seed data — only used once to populate the DB on first run
_SEED_INITIATIVES = [
    {
        "name": "Databricks Migration",
        "status": "In Progress",
        "target": "Q3 2026",
        "description": "Migrate outbound feeds from RedShift to Databricks",
        "owner": "Tech Lead, Ops Lead, TPM",
        "sort_order": 0,
    },
    {
        "name": "Jupiter Acceptance Criteria / QA Validation",
        "status": "In Progress",
        "target": "Q2 2026",
        "description": "Python script to validate outbound files against acceptance criteria; demoed at Data Integrations team meeting 3/26",
        "owner": "Caroline Sullivan (with Cara oversight)",
        "sort_order": 1,
    },
    {
        "name": "IM Ticketing Process",
        "status": "In Progress",
        "target": "Ongoing",
        "description": "Improve ticket management workflow with Jeff & Ellen",
        "owner": "TPM",
        "sort_order": 2,
    },
    {
        "name": "Moneyball Feed Handoff",
        "status": "In Progress",
        "target": "Q2 2026",
        "description": "Jupiter Ops taking over GABI feeds from Moneyball",
        "owner": "Robert/Alexis (MB), Cara (Jupiter)",
        "sort_order": 3,
    },
    {
        "name": "GitHub Data Governance",
        "status": "In Progress",
        "target": "Q2 2026",
        "description": "Scripting library governance for GitHub repos; governance doc shared for review",
        "next_steps": "Review Jeffrey's Claude-generated governance doc; Steven adding outbound requirements",
        "owner": "Jeffrey Mullen, Steven Balalis",
        "sort_order": 4,
    },
    {
        "name": "Databricks Data Governance",
        "status": "Planning",
        "target": "TBD",
        "description": "Data governance standards for Databricks platform",
        "next_steps": "Not yet kicked off — pending GitHub governance completion",
        "owner": "TBD",
        "sort_order": 5,
    },
]


class PortfolioService:
    """Service for managing accomplishments and portfolio export."""

    def __init__(self, db: Session):
        self.db = db
        self._seed_initiatives_if_empty()

    def _seed_initiatives_if_empty(self):
        """Populate initiatives table from seed data if it's empty."""
        count = self.db.query(Initiative).count()
        if count == 0:
            logger.info("Seeding initiatives table from defaults")
            for data in _SEED_INITIATIVES:
                self.db.add(Initiative(**data))
            self.db.commit()

    def get_by_week(self, weeks: int = 4) -> List[Dict]:
        """Get accomplishments grouped by week."""
        today = date.today()
        start_date = self._get_week_start(today) - timedelta(weeks=weeks - 1)

        accomplishments = self.db.query(Accomplishment).filter(
            Accomplishment.week_of >= start_date
        ).order_by(desc(Accomplishment.completed_date)).all()

        weeks_data = []
        current_week = self._get_week_start(today)

        for i in range(weeks):
            week_start = current_week - timedelta(weeks=i)
            week_end = week_start + timedelta(days=6)

            week_accomplishments = [
                {
                    "id": a.id,
                    "title": a.title,
                    "description": a.description,
                    "impact": a.impact,
                    "category": a.category,
                    "completed_date": a.completed_date.isoformat() if a.completed_date else None,
                    "source_jira_key": a.source_jira_key,
                }
                for a in accomplishments
                if a.week_of == week_start
            ]

            weeks_data.append({
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "week_label": f"Week of {week_start.strftime('%b %d')}",
                "is_current_week": i == 0,
                "accomplishments": week_accomplishments,
                "count": len(week_accomplishments),
            })

        return weeks_data

    def get_initiatives(self) -> List[Dict]:
        """Get initiatives from DB, ordered by sort_order."""
        rows = self.db.query(Initiative).order_by(Initiative.sort_order, Initiative.id).all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "status": r.status,
                "target": r.target,
                "description": r.description,
                "next_steps": r.next_steps,
                "owner": r.owner,
                "confluence_link": r.confluence_link,
                "document_links": r.get_document_links(),
            }
            for r in rows
        ]

    def export_markdown(self, weeks: int = 2) -> str:
        """Export portfolio as markdown for Chris 1:1."""
        weeks_data = self.get_by_week(weeks=weeks)
        initiatives = self.get_initiatives()

        lines = [
            f"# Portfolio Update — {date.today().strftime('%B %d, %Y')}",
            "",
            "## Completed Work",
            "",
        ]

        for week in weeks_data:
            if week["accomplishments"]:
                lines.append(f"### {week['week_label']}")
                lines.append("")
                for item in week["accomplishments"]:
                    lines.append(f"- **{item['title'][:100]}**")
                    if item.get("impact"):
                        lines.append(f"  - Impact: {item['impact']}")
                    if item.get("source_jira_key"):
                        lines.append(f"  - Jira: {item['source_jira_key']}")
                lines.append("")

        lines.extend(["## In-Flight Initiatives", ""])

        for initiative in initiatives:
            lines.append(f"### {initiative['name']}")
            lines.append(f"- **Status:** {initiative['status']}")
            lines.append(f"- **Target:** {initiative['target']}")
            lines.append(f"- **Owner:** {initiative['owner']}")
            lines.append(f"- {initiative['description']}")
            lines.append("")

        return "\n".join(lines)

    def _get_week_start(self, d: date) -> date:
        """Get Monday of the week containing date d."""
        return d - timedelta(days=d.weekday())
