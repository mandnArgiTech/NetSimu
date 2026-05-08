"""Loads concept markdown files for /api/concept/{id}.

Files live at netops_sim/web/content/concepts/<id>.md. Optional frontmatter
is a single `title:` line at the top:

    title: Spine switch
    ---
    # Spine switch
    ...

We keep the parser deliberately tiny — no PyYAML dep — because the only
metadata we need is a display title. Body is whatever follows.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_CONCEPTS_DIR = Path(__file__).resolve().parent / "content" / "concepts"
_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")


@dataclass(frozen=True)
class Concept:
    id: str
    title: str
    body: str


def _is_safe_id(concept_id: str) -> bool:
    return bool(_ID_PATTERN.match(concept_id))


def list_concept_ids() -> list[str]:
    if not _CONCEPTS_DIR.is_dir():
        return []
    return sorted(p.stem for p in _CONCEPTS_DIR.glob("*.md"))


def load_concept(concept_id: str) -> Concept | None:
    """Return the concept, or None if missing / id is unsafe."""
    if not _is_safe_id(concept_id):
        return None
    path = _CONCEPTS_DIR / f"{concept_id}.md"
    if not path.is_file():
        return None
    text = path.read_text()
    title, body = _split_frontmatter(text, fallback_title=concept_id)
    return Concept(id=concept_id, title=title, body=body)


def _split_frontmatter(text: str, fallback_title: str) -> tuple[str, str]:
    """Pull a `title:` line from a leading frontmatter block.

    Frontmatter shape (optional):
        title: Display Title
        ---
        body...

    If no frontmatter, returns (fallback_title, text).
    """
    lines = text.splitlines()
    if not lines or not lines[0].startswith("title:"):
        return fallback_title, text
    title = lines[0].split(":", 1)[1].strip()
    # Skip the title line and an optional `---` separator.
    rest = lines[1:]
    if rest and rest[0].strip() == "---":
        rest = rest[1:]
    return title, "\n".join(rest).lstrip("\n")
