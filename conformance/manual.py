import html
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FILES = [
    str(entry["file"])
    for entry in json.loads((ROOT / "conformance" / "documents.json").read_text())["documents"]
]

HELD_DOCUMENTS = ROOT / "docs"

HELD = HELD_DOCUMENTS / FILES[0]


def flatten(laid_out: str) -> str:
    return re.sub(r"[^a-z0-9]", "", laid_out.lower())


def text(pdf: Path = HELD) -> str:
    if not pdf.is_file() or shutil.which("pdftotext") is None:
        return ""
    done = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True
    )
    return flatten(done.stdout)


def plain(path: Path) -> str:
    if not path.is_file():
        return ""
    body = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".html":
        body = html.unescape(re.sub(r"<[^>]+>", " ", body))
    return flatten(body)


def held(where: Path = HELD_DOCUMENTS) -> dict[str, str]:
    found = {name: (text if name.endswith(".pdf") else plain)(where / name) for name in FILES}
    return {name: body for name, body in found.items() if body}
