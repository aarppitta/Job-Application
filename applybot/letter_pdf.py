"""Cover letter text -> a clean one-page A4 PDF (recruiters see the same layout on every computer).

Used by apply.py for every application, and by hand:
    backend/venv/bin/python applybot/letter_pdf.py letter.txt "~/Desktop/Resume/Job Applications/X/Cover_Letter.pdf"
"""
import html
import sys
from datetime import date
from pathlib import Path

STYLE = """
body { font-family: Helvetica, Arial, sans-serif; color: #222; font-size: 10.8pt; line-height: 1.5; margin: 0; }
.date { text-align: right; color: #555; margin-bottom: 22px; }
p { margin: 0 0 11px; }
"""


def letter_html(text: str, today: date | None = None) -> str:
    paragraphs = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
    body = "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paragraphs)
    when = (today or date.today()).strftime("%d %B %Y").lstrip("0")
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{STYLE}</style></head><body><div class="date">{when}</div>{body}</body></html>'


def write_letter_pdf(text: str, out: Path, browser_type=None) -> Path:
    """Render with a headless Chromium (page.pdf only works headless). browser_type: reuse apply.py's Playwright."""
    out = Path(out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    def render(bt):
        browser = bt.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content(letter_html(text))
            page.pdf(path=str(out), format="A4", print_background=True,
                     margin={"top": "22mm", "bottom": "20mm", "left": "22mm", "right": "22mm"})
        finally:
            browser.close()

    if browser_type is not None:
        render(browser_type)
    else:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            render(p.chromium)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    print(write_letter_pdf(Path(sys.argv[1]).expanduser().read_text(), Path(sys.argv[2])))
