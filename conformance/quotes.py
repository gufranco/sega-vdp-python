import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from conformance import manual

RECORDS = Path(__file__).resolve().parent

KEPT = ("hardware.json", "divergences.json")

Quote = tuple[str, str]


def _quoted(key: str, value: Any, where: str) -> list[Quote]:
    if key.endswith("quote") and isinstance(value, str):
        return [(where, value)]
    if key.endswith("quotes") and isinstance(value, list):
        return [(f"{where}[{index}]", one) for index, one in enumerate(value)]
    return []


def passages(node: Any, where: str) -> list[Quote]:
    if isinstance(node, list):
        return [
            found for index, one in enumerate(node) for found in passages(one, f"{where}[{index}]")
        ]
    if not isinstance(node, dict):
        return []
    found: list[Quote] = []
    for key, value in node.items():
        held = _quoted(key, value, where)
        found += held if held else passages(value, f"{where}.{key}")
    return found


def collected() -> list[Quote]:
    return [
        found for name in KEPT for found in passages(json.loads((RECORDS / name).read_text()), name)
    ]


def absent(held: Sequence[Quote], text: str) -> list[Quote]:
    flat = manual.flatten(text)
    return [(where, quote) for where, quote in held if manual.flatten(quote) not in flat]


def main(text: str | None = None) -> int:
    held = collected()
    documents = manual.held() if text is None else {"given": text} if text else {}
    if not documents:
        print(
            f"{len(held)} quotes checked against 0 documents: none is on this machine, so "
            "none was checked. None is redistributable, and each is named in the References "
            "section of README.md"
        )
        return 0
    missing = absent(held, "".join(documents.values()))
    print(
        f"{len(held)} quotes against {len(documents)} documents, "
        f"{len(held) - len(missing)} located, {len(missing)} not"
    )
    for where, quote in missing:
        print(f"  {where}: {quote}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
