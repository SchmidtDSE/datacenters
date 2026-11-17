#!/usr/bin/env python3
"""Fill report.md's {{value}} and {{table:name}} placeholders from build/ into build/report.md."""
import json
import re
from pathlib import Path

here = Path(__file__).resolve().parent
build = here / "build"
values = json.loads((build / "values.json").read_text())


def fill(m):
    key = m.group(1)
    if key.startswith("table:"):
        return (build / f"{key[6:]}.md").read_text()
    if key not in values:
        raise SystemExit(f"report.md names {{{{{key}}}}}, which analysis.py does not write")
    return str(values[key])


text = re.sub(r"\{\{([\w:]+)\}\}", fill, (here / "report.md").read_text())
(build / "report.md").write_text(text)
