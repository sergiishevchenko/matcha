"""Tag names: canonical storage (no #), optional # in user input, # prefix in UI."""

import re

# Commas, semicolons, pipes, or any run of whitespace between tags.
_SPLIT_PATTERN = re.compile(r"[,;\s|]+")


def split_tags_input(raw):
    """Split a single user input line into tag fragments (before canonical_tag_name)."""
    if raw is None or not str(raw).strip():
        return []
    return [p for p in _SPLIT_PATTERN.split(str(raw).strip()) if p.strip()]


def canonical_tag_name(fragment):
    """
    Strip leading '#' characters, whitespace, then keep only [a-z0-9_-] lowercase.
    Returns '' if nothing usable remains.
    """
    if fragment is None:
        return ""
    s = str(fragment).strip()
    while s.startswith("#"):
        s = s[1:].strip()
    s = re.sub(r"[^a-z0-9_-]", "", s.lower())
    return s


def tags_display_form_value(tags):
    """Comma-separated string for profile edit input: #vegan, #geek (DB stores without #)."""
    if not tags:
        return ""
    parts = []
    for t in tags:
        if not t:
            continue
        name = str(t).strip().lstrip("#")
        if name:
            parts.append("#" + name)
    return ", ".join(parts)
