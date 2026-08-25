from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import markdown
import yaml


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
        file_path = (Path(env.conf.get("root_dir", ".")) / yaml_path).resolve()
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
