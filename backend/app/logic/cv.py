"""The standard CV (Word .docx) used for EVERY application, and the cover letter .docx.

German/EU layout ("Lebenslauf" style): A4, personal details as label/value rows (no visa line: user, 2026-10-19), dates in a left column
(MM/YYYY), reverse-chronological experience, no photo / date of birth / signature.
Everything comes from the profile (your real CV). Nothing is added, nothing is tailored per job.
"""
import io
import re

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from fastapi.responses import Response

ACCENT, GREY = RGBColor(0x1F, 0x3A, 0x5F), RGBColor(0x5F, 0x63, 0x68)
LEFT = Cm(3.4)  # width of the left (dates / labels) column

# Skill groups for the "Technical skills" section; a skill not listed here goes to "Other".
SKILL_GROUPS = {
    "Programming": ["Python", "TypeScript", "JavaScript", "FastAPI", "Django", "Node.js", "Express.js", "Angular", "React"],
    "Industrial & OT": ["SCADA", "WebSCADA", "OPC", "OPC UA", "Modbus", "FINS", "PLC", "IIoT", "21 CFR Part 11", "LabVIEW"],
    "Databases & cloud": ["MySQL", "PostgreSQL", "MongoDB", "AWS"],
    "Tools & practices": ["REST APIs", "JWT", "RBAC", "PyInstaller", "Windows Services", "Docker", "Git", "Postman", "Agile"],
}
MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                         "august", "september", "october", "november", "december"])}


def eu_dates(text: str) -> str:
    """'April 2026 – Present' → '04/2026 – present' (the usual format on German CVs)."""
    text = re.sub(r"\b([A-Za-z]+) (\d{4})\b", lambda m: f"{MONTHS[m[1].lower()]:02d}/{m[2]}" if m[1].lower() in MONTHS else m[0], text)
    return re.sub(r"\bPresent\b", "present", text)


def _run(par, text: str, size: float = 10, bold=False, italic=False, color=None):
    run = par.add_run(text)
    run.font.size, run.bold, run.italic = Pt(size), bold, italic
    if color is not None:
        run.font.color.rgb = color
    return run


def _heading(doc, text: str):
    par = doc.add_paragraph()
    par.paragraph_format.space_before, par.paragraph_format.space_after = Pt(8), Pt(3)
    par.paragraph_format.keep_with_next = True  # never a heading alone at the bottom of a page
    _run(par, text.upper(), 11, bold=True, color=ACCENT)
    border = OxmlElement("w:pBdr")  # thin line under the heading
    bottom = OxmlElement("w:bottom")
    for key, value in (("val", "single"), ("sz", "6"), ("space", "1"), ("color", "1F3A5F")):
        bottom.set(qn(f"w:{key}"), value)
    border.append(bottom)
    par._p.get_or_add_pPr().append(border)


def _row(doc, left: str):
    """A line with grey text in the left column (tab stop) and a hanging indent: wrapped text stays in the right column.
    Plain paragraphs, not a table: Word and Pages both break them across pages normally."""
    par = doc.add_paragraph()
    fmt = par.paragraph_format
    fmt.left_indent, fmt.first_line_indent, fmt.space_after = LEFT, -LEFT, Pt(1)
    fmt.tab_stops.add_tab_stop(LEFT)
    _run(par, left, 9.5, color=GREY)
    par.add_run("\t")
    return par


def _indented(doc):
    par = doc.add_paragraph()
    par.paragraph_format.left_indent = LEFT
    return par


def _bullet(doc, text: str, indent=Cm(0)):
    par = doc.add_paragraph(style="List Bullet")
    fmt = par.paragraph_format
    fmt.left_indent, fmt.first_line_indent, fmt.space_after = indent + Cm(0.5), -Cm(0.5), Pt(1)
    _run(par, text, 9.2)
    return par


def education_parts(line: str) -> tuple[str, str, str]:
    """'MSc Computer Science | Greenwich University, London | January 2022 – January 2023' → (degree, school, dates).
    Parts may be missing; the one with a year is the dates."""
    parts = [p.strip() for p in line.split("|") if p.strip()]
    dates = next((p for p in parts if re.search(r"\d{4}", p)), "")
    rest = [p for p in parts if p != dates] + ["", ""]
    return rest[0], rest[1], dates


def degree_text(line: str) -> str:
    """One education line as plain text: 'MSc Computer Science, Greenwich University, London'."""
    degree, school, _ = education_parts(line)
    return f"{degree}, {school}" if school else degree


def phone_text(phone: str | None) -> str | None:
    """'+919812345678' → '+91 98123 45678' (easier to read; other formats stay as typed)."""
    digits = re.sub(r"\D", "", phone or "")
    return f"+91 {digits[2:7]} {digits[7:]}" if (phone or "").startswith("+91") and len(digits) == 12 else phone


def skill_groups(skills: list[str]) -> list[tuple[str, list[str]]]:
    groups = [(name, [s for s in members if s in skills]) for name, members in SKILL_GROUPS.items()]
    known = {s for members in SKILL_GROUPS.values() for s in members}
    groups.append(("Other", [s for s in skills if s not in known]))
    return [(name, members) for name, members in groups if members]


def standard_cv_docx(profile) -> bytes:
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.left_margin = section.right_margin = Cm(1.5)
    section.top_margin = section.bottom_margin = Cm(1.2)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Calibri", Pt(10)
    normal.paragraph_format.space_after = Pt(0)

    par = doc.add_paragraph()
    _run(par, profile.name, 22, bold=True, color=ACCENT)
    if profile.headline:
        par = doc.add_paragraph()
        par.paragraph_format.space_after = Pt(2)
        _run(par, profile.headline, 12, color=ACCENT)

    _heading(doc, "Personal details")
    languages = ", ".join(f"{x['language']} ({x['level']})" if x.get("level") else x["language"] for x in profile.languages or [])
    for label, value in (("Location", profile.location), ("Phone", phone_text(profile.phone)), ("Email", profile.email),
                         ("Online", " · ".join(u.removeprefix("https://") for u in (profile.linkedin_url, profile.github_url) if u)),
                         ("Languages", languages)):
        if value:
            _run(_row(doc, label), value, 10)

    if profile.summary:
        _heading(doc, "Profile")
        _run(doc.add_paragraph(), profile.summary, 10)

    _heading(doc, "Professional experience")
    for entry in profile.experience or []:
        par = _row(doc, eu_dates(entry.get("dates", "")))
        par.paragraph_format.space_before, par.paragraph_format.keep_with_next = Pt(4), True
        _run(par, entry["role"], 10.5, bold=True)
        par = _indented(doc)
        par.paragraph_format.keep_with_next = True
        _run(par, " · ".join(x for x in (entry.get("company"), entry.get("location")) if x), 10, italic=True, color=GREY)
        for bullet in entry.get("bullets", []):
            _bullet(doc, bullet, LEFT)

    if profile.education:  # right after experience: the usual order on German CVs
        _heading(doc, "Education")
        for line in profile.education:  # "degree | school | dates", newest first
            degree, school, dates = education_parts(line)
            par = _row(doc, eu_dates(dates))
            _run(par, degree, 10.5, bold=True)
            if school:
                _run(par, f" — {school}", 10, color=GREY)

    if profile.projects:
        _heading(doc, "Key projects")
        for project in profile.projects:
            par = doc.add_paragraph()
            par.paragraph_format.space_before, par.paragraph_format.keep_with_next = Pt(4), True
            _run(par, project["name"], 10.5, bold=True)
            if project.get("tech"):
                par = doc.add_paragraph()
                par.paragraph_format.keep_with_next = True
                _run(par, project["tech"], 9, italic=True, color=GREY)
            for bullet in project.get("bullets", []):
                _bullet(doc, bullet)

    groups = skill_groups([s["name"] for s in profile.skills or []])
    if groups:
        _heading(doc, "Technical skills")
        for name, members in groups:
            _run(_row(doc, name), ", ".join(members), 10)

    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def text_docx(text: str) -> bytes:
    """A simple .docx for the cover letter."""
    doc = Document()
    doc.styles["Normal"].font.size = Pt(11)
    for block in text.split("\n"):
        doc.add_paragraph(block)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def docx_response(data: bytes, profile, job, kind: str) -> Response:
    """Send a .docx as a download: 'Arpita_Chaudhari_CV.docx', or 'Arpita_Chaudhari_Cover_Letter_Celonis.docx' with a job."""
    company = "_" + "".join(c if c.isalnum() else "_" for c in job.company)[:40] if job is not None else ""
    name = f"{profile.name.replace(' ', '_')}_{kind}{company}.docx"
    return Response(data, media_type=DOCX, headers={"Content-Disposition": f'attachment; filename="{name}"'})
