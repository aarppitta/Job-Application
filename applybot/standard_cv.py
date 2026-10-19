"""Save the standard CV (the one CV used for every application) as .docx, .pages and .pdf.

The app builds the .docx from your profile; Pages (installed on the Mac) saves the .pages file and the PDF.
The apply bot uploads the PDF to every application, and rebuilds it by itself when the CV in the app changed.

  backend/venv/bin/python applybot/standard_cv.py              # live app (login from ~/.job-automation/config.json)
  backend/venv/bin/python applybot/standard_cv.py --config X   # another app login
"""
import argparse
import io
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from apply import CONFIG, STANDARD_CV, Api  # noqa: E402

# The .docx is opened with `open -a Pages` (AppleScript's own `open` sometimes never opens it); importing takes a few
# seconds, so wait for the document by name, then save it as .pages and export the PDF.
SCRIPT = """
on run argv
  tell application "Pages"
    repeat 120 times
      try -- while Pages is starting (no documents yet) this query errors instead of returning 0
        if (count of (documents whose name starts with (item 1 of argv))) > 0 then exit repeat
      end try
      delay 0.5
    end repeat
    set d to first document whose name starts with (item 1 of argv)
    save d in POSIX file (item 2 of argv)
    export d to POSIX file (item 3 of argv) as PDF
    close d saving no
  end tell
end run
"""


def docx_text(data: bytes) -> str:
    from docx import Document
    return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)


def build(api: Api, only_if_changed: bool = False) -> bool:
    """Download the CV from the app and save .docx/.pages/.pdf. only_if_changed: skip when the text is the same
    as the saved .docx and the PDF exists (the apply bot calls this before every run). True = files were rebuilt."""
    pdf = STANDARD_CV
    pdf.parent.mkdir(parents=True, exist_ok=True)
    docx, pages = pdf.with_suffix(".docx"), pdf.with_suffix(".pages")
    data = api.call("GET", "/api/cv.docx").content
    if only_if_changed and pdf.exists() and docx.exists() and docx_text(docx.read_bytes()) == docx_text(data):
        return False
    docx.write_bytes(data)
    for attempt in (1, 2):  # a second try if Pages was just quitting or starting
        subprocess.run(["open", "-a", "Pages", str(docx)], check=True)
        if subprocess.run(["osascript", "-e", SCRIPT, docx.stem, str(pages), str(pdf)]).returncode == 0:
            break
        if attempt == 2:
            sys.exit("Pages could not save the files. Open the .docx in Pages once by hand, then run this again.")
        # Pages sometimes hangs on an import (it then can't even list its documents): restart it once.
        # Safe: Pages saves your own documents automatically and reopens them.
        subprocess.run(["osascript", "-e", 'tell application "Pages" to quit'])
        time.sleep(5)
    print(f"Saved:\n  {docx}\n  {pages}\n  {pdf}  (uploaded by the apply bot)")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(CONFIG), help=f"app login (default {CONFIG})")
    args = ap.parse_args()
    build(Api(json.loads(Path(args.config).read_text())))


if __name__ == "__main__":
    main()
