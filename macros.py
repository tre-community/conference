from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any

# Ensure project directory is on sys.path for local module imports
_project_dir = str(Path(__file__).resolve().parent)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

import markdown
import yaml

from schedule_pdf import generate_schedule_pdf


def define_env(env: Any) -> None:
    """Register custom schedule macros for Zensical."""

    @env.macro
    def render_schedule(
        yaml_path: str = "docs/2026/schedule.yml",
        day_index: int | None = None,
    ) -> str:
        """Renders conference schedule from YAML.

        If day_index is None, renders all days in tabs.
        If day_index is an integer, renders that specific day's table.
        """
        root_dir = Path(env.conf.get("root_dir", "."))
        file_path = (root_dir / yaml_path).resolve()

        # Autogenerate PDF to docs/ and site/ output directories
        pdf_name = file_path.with_suffix(".pdf").name
        docs_pdf = file_path.parent / pdf_name
        site_pdf = root_dir / "site" / file_path.parent.name / pdf_name
        targets = [docs_pdf, site_pdf]
        generate_schedule_pdf(yaml_path=file_path, output_paths=targets)

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        days = data.get("days", [])
        if day_index is not None:
            return _render_table(days[day_index])

        # Wrap all days in pymdownx content tabs
        out = []
        for day in days:
            title = day.get("title", "Day")
            note = f"    {day['note']}\n\n" if "note" in day else ""
            table = "\n".join(f"    {line}" for line in _render_table(day).splitlines())
            out.append(f'=== "{title}"\n\n{note}{table}\n')
        return "\n".join(out)

    @env.macro
    def download_schedule_button(
        pdf_href: str = "schedule.pdf",
        label: str = "Download Schedule (PDF)",
    ) -> str:
        """Renders a styled download button linking to the schedule PDF."""
        return (
            f'<div class="schedule-download">\n'
            f'  <a class="md-button md-button--primary" href="{html.escape(pdf_href)}" download>\n'
            f'    <span class="twemoji">'
            f'<svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="lucide lucide-download" viewBox="0 0 24 24"><path d="M12 15V3M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/></svg>'
            f"</span> {html.escape(label)}\n"
            f"  </a>\n"
            f"</div>"
        )


def _render_table(day: dict[str, Any]) -> str:
    """Renders a single day's schedule table."""
    slots = day.get("slots", [])
    tracks = day.get("tracks", [])
    title = day.get("title", "Conference Day")

    # Determine max parallel track columns needed for this day
    parallel_counts = [
        len(s.get("sessions", []))
        for s in slots
        if s.get("type") not in ("break", "plenary", "social")
    ]
    max_tracks = max(max(parallel_counts or [1]), len(tracks))

    # Table header
    headers = "".join(
        f'<th scope="col" class="col-track">{html.escape(tracks[i] if i < len(tracks) else f"Session {i + 1}")}</th>'
        for i in range(max_tracks)
    )

    # Table rows
    rows = []
    for slot in slots:
        time_str = html.escape(str(slot.get("time", "")))
        sessions = slot.get("sessions", [])
        stype = slot.get("type", "")
        row_cls = f' class="row-{stype}"' if stype else ""

        if stype in ("break", "plenary", "social", "satellite") or len(sessions) <= 1:
            cell = _render_cell(sessions[0] if sessions else {}, stype)
            colspan = f' colspan="{max_tracks}"' if max_tracks > 1 else ""
            cells = f'<td{colspan} class="col-session col-span">{cell}</td>'
        else:
            cells = "".join(
                f'<td class="col-session">{_render_cell(sessions[i], stype)}</td>'
                if i < len(sessions)
                else '<td class="col-session col-empty" aria-label="No parallel session"></td>'
                for i in range(max_tracks)
            )

        rows.append(
            f'<tr{row_cls}><th scope="row" class="col-time">{time_str}</th>{cells}</tr>'
        )

    return (
        f'<div class="schedule-table-wrapper" role="region" aria-label="Schedule table for {html.escape(title)}" tabindex="0">\n'
        f'<table class="schedule-table">\n'
        f'<caption class="sr-only">Conference schedule for {html.escape(title)}</caption>\n'
        f'<thead><tr><th scope="col" class="col-time">Time</th>{headers}</tr></thead>\n'
        f"<tbody>\n{'\n'.join(rows)}\n</tbody>\n"
        f"</table>\n</div>"
    )


def _render_cell(session: dict[str, Any], stype: str = "") -> str:
    """Renders a single session cell (expandable if description is present)."""
    title = html.escape(str(session.get("title", "")))
    room = session.get("room")
    speakers = session.get("speakers", [])
    desc = session.get("description", "").strip()

    # Badges for room and event type
    badges = []
    if room:
        badges.append(
            f'<span class="schedule-badge badge-room" aria-label="Location: {html.escape(str(room))}">{html.escape(str(room))}</span>'
        )
    if stype and stype not in ("break", "plenary"):
        badges.append(
            f'<span class="schedule-badge badge-{stype}" aria-label="Event type: {html.escape(stype.capitalize())}">{html.escape(stype.capitalize())}</span>'
        )
    badge_html = (
        f' <span class="schedule-badges">{" ".join(badges)}</span>' if badges else ""
    )

    # Speaker line
    sp_html = ""
    if speakers:
        names = [
            f"{s['name']} ({s['affiliation']})"
            if isinstance(s, dict) and s.get("affiliation")
            else s.get("name", s)
            if isinstance(s, dict)
            else str(s)
            for s in speakers
        ]
        sp_html = f'<div class="schedule-speakers"><span class="sr-only">Speakers: </span>{html.escape(", ".join(names))}</div>'

    header_content = f'<span class="schedule-title">{title}</span>{badge_html}{sp_html}'

    if desc:
        desc_html = markdown.markdown(desc, extensions=["extra", "sane_lists"])
        return f'<details class="schedule-details"><summary class="schedule-summary">{header_content}</summary><div class="schedule-desc">{desc_html}</div></details>'
    return f'<div class="schedule-plain">{header_content}</div>'


if __name__ == "__main__":
    generate_schedule_pdf()
