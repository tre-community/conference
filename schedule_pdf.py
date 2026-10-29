"""PDF schedule generator for TRE Communities Conference."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import yaml
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):
    """Canvas that performs a two-pass calculation of the total page count."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, num_pages: int) -> None:
        self.saveState()
        page_w, page_h = landscape(A4)
        margin = 36

        # Running header
        self.setFont("Helvetica-Bold", 8.5)
        self.setFillColor(colors.HexColor("#1E293B"))
        self.drawString(
            margin, page_h - 28, "TRE Communities Conference 2026 — Schedule"
        )

        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawRightString(
            page_w - margin,
            page_h - 28,
            "DoubleTree by Hilton, Edinburgh | 16–18 November 2026",
        )

        # Header rule
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.75)
        self.line(margin, page_h - 34, page_w - margin, page_h - 34)

        # Footer rule
        self.line(margin, 30, page_w - margin, 30)

        # Running footer
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#2563EB"))
        self.drawString(margin, 18, "https://tre-conference.readthedocs.io/")

        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawRightString(
            page_w - margin,
            18,
            f"Page {self._pageNumber} of {num_pages}",
        )
        self.restoreState()


def _format_speakers(speakers: list[Any]) -> str:
    """Format speakers list as HTML escaped string."""
    names = []
    for s in speakers:
        if isinstance(s, dict):
            name = s.get("name", "")
            affil = s.get("affiliation", "")
            names.append(f"{name} ({affil})" if affil else name)
        else:
            names.append(str(s))
    return html.escape(", ".join(names))


def _build_cell_flowable(
    session: dict[str, Any],
    stype: str,
    base_style: ParagraphStyle,
) -> Paragraph:
    """Constructs a formatted Paragraph flowable for a table session cell."""
    if not session:
        return Paragraph("", base_style)

    title = html.escape(str(session.get("title", "")))
    room = session.get("room")
    speakers = session.get("speakers", [])

    badges = []
    if room:
        room_esc = html.escape(str(room))
        badges.append(f'<font color="#B45309"><b>[{room_esc}]</b></font>')
    if stype and stype not in ("break", "plenary"):
        stype_esc = html.escape(stype.capitalize())
        badges.append(f'<font color="#4338CA"><b>[{stype_esc}]</b></font>')

    badge_html = f" {' '.join(badges)}" if badges else ""
    sp_str = _format_speakers(speakers)
    sp_html = (
        f'<br/><font color="#334155" size="7.5"><i>{sp_str}</i></font>'
        if sp_str
        else ""
    )

    text = f"<b>{title}</b>{badge_html}{sp_html}"
    return Paragraph(text, base_style)


def generate_schedule_pdf(
    yaml_path: str | Path = "docs/2026/schedule.yml",
    output_paths: list[str | Path] | str | Path | None = None,
) -> list[Path]:
    """Generates the downloadable PDF schedule from the given YAML file.

    Outputs to docs/2026/schedule.pdf and site/2026/schedule.pdf.
    Fails with an error if parsing or PDF rendering encounters any failure.
    """
    yaml_file = Path(yaml_path).resolve()
    with open(yaml_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if output_paths is None:
        targets = [
            yaml_file.parent / f"{yaml_file.stem}.pdf",
            Path("site") / yaml_file.parent.name / f"{yaml_file.stem}.pdf",
        ]
    elif isinstance(output_paths, (str, Path)):
        targets = [Path(output_paths)]
    else:
        targets = [Path(p) for p in output_paths]

    for p in targets:
        p.parent.mkdir(parents=True, exist_ok=True)

    primary_target = targets[0]

    page_w, _ = landscape(A4)
    margin = 36
    doc = SimpleDocTemplate(
        str(primary_target),
        pagesize=landscape(A4),
        leftMargin=margin,
        rightMargin=margin,
        topMargin=42,
        bottomMargin=38,
    )

    usable_width = page_w - (2 * margin)  # 769.89 pt

    sample_styles = getSampleStyleSheet()

    day_title_style = ParagraphStyle(
        "DayTitle",
        parent=sample_styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=15,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=2,
    )

    day_note_style = ParagraphStyle(
        "DayNote",
        parent=sample_styles["Italic"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
        spaceAfter=5,
    )

    header_cell_style = ParagraphStyle(
        "HeaderCell",
        parent=sample_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    )

    time_cell_style = ParagraphStyle(
        "TimeCell",
        parent=sample_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#1E293B"),
        alignment=1,  # Center
    )

    body_cell_style = ParagraphStyle(
        "BodyCell",
        parent=sample_styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#0F172A"),
    )

    break_cell_style = ParagraphStyle(
        "BreakCell",
        parent=sample_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#475569"),
        alignment=1,  # Center
    )

    days = data.get("days", [])
    story: list[Any] = []

    for day_idx, day in enumerate(days):
        day_title = day.get("title", f"Day {day_idx + 1}")
        story.append(Paragraph(html.escape(day_title), day_title_style))

        if "note" in day:
            story.append(Paragraph(html.escape(day["note"]), day_note_style))
        else:
            story.append(Spacer(1, 4))

        slots = day.get("slots", [])
        tracks = day.get("tracks", [])

        # Calculate max parallel track columns
        parallel_counts = [
            len(s.get("sessions", []))
            for s in slots
            if s.get("type") not in ("break", "plenary", "social")
        ]
        max_tracks = max(max(parallel_counts or [1]), len(tracks))

        time_col_width = 72.0
        track_col_width = (usable_width - time_col_width) / max_tracks
        col_widths = [time_col_width] + [track_col_width] * max_tracks

        # Table Header
        header_row = [Paragraph("Time", header_cell_style)]
        for i in range(max_tracks):
            track_title = tracks[i] if i < len(tracks) else f"Session {i + 1}"
            header_row.append(Paragraph(html.escape(track_title), header_cell_style))

        table_data = [header_row]
        table_style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94A3B8")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]

        for row_idx, slot in enumerate(slots, start=1):
            time_str = str(slot.get("time", ""))
            sessions = slot.get("sessions", [])
            stype = slot.get("type", "")

            time_flowable = Paragraph(html.escape(time_str), time_cell_style)

            # Slot background colors
            if stype == "plenary":
                bg_color = colors.HexColor("#FEF3C7")  # Amber-100
            elif stype == "break":
                bg_color = colors.HexColor("#F1F5F9")  # Slate-100
            elif stype == "social":
                bg_color = colors.HexColor("#ECFDF5")  # Emerald-50
            elif stype == "satellite":
                bg_color = colors.HexColor("#F5F3FF")  # Purple-50
            else:
                bg_color = (
                    colors.HexColor("#FFFFFF")
                    if row_idx % 2 == 1
                    else colors.HexColor("#F8FAFC")
                )

            table_style_commands.append(
                ("BACKGROUND", (0, row_idx), (-1, row_idx), bg_color)
            )

            # Cell spanning for full-width slots
            if (
                stype in ("break", "plenary", "social", "satellite")
                or len(sessions) <= 1
            ):
                sess = sessions[0] if sessions else {}
                cell_style = break_cell_style if stype == "break" else body_cell_style
                session_cell = _build_cell_flowable(sess, stype, cell_style)
                row_cells = [time_flowable, session_cell] + [""] * (max_tracks - 1)
                if max_tracks > 1:
                    table_style_commands.append(
                        ("SPAN", (1, row_idx), (max_tracks, row_idx))
                    )
                if stype == "break":
                    table_style_commands.append(
                        ("VALIGN", (0, row_idx), (-1, row_idx), "MIDDLE")
                    )
            else:
                row_cells = [time_flowable]
                for i in range(max_tracks):
                    sess = sessions[i] if i < len(sessions) else {}
                    row_cells.append(_build_cell_flowable(sess, stype, body_cell_style))

            table_data.append(row_cells)

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle(table_style_commands))
        story.append(table)

        # Page break between conference days (except after the final day)
        if day_idx < len(days) - 1:
            story.append(PageBreak())

    doc.build(story, canvasmaker=NumberedCanvas)

    # Copy to remaining targets
    content = primary_target.read_bytes()
    for sec in targets[1:]:
        sec.write_bytes(content)

    return targets


if __name__ == "__main__":
    generated = generate_schedule_pdf()
    for p in generated:
        print(f"Generated schedule PDF at: {p} ({p.stat().st_size} bytes)")
