#!/usr/bin/env python3
"""
PreToolUse hook: blocks Read/Edit/Write calls for files that
match .agentignore patterns (gitignore syntax). No external dependencies.
"""

import json
import os
import re
import sys


# ── pattern matching ──────────────────────────────────────────────────────────

def _compile(raw: str) -> tuple:
    """Return (compiled_regex, negated) for a single gitignore-style line."""
    pat = raw

    negated = pat.startswith('!')
    if negated:
        pat = pat[1:]

    # Leading / anchors the pattern to the root of the ignore file's directory
    anchored = pat.startswith('/')
    if anchored:
        pat = pat[1:]

    # Trailing / means directory-only; drop it — we match prefix anyway
    if pat.endswith('/'):
        pat = pat[:-1]

    # A pattern with an interior slash is always anchored implicitly
    has_interior_slash = '/' in pat

    # Escape regex metacharacters, then convert glob wildcards.
    # Order matters: handle ** before *.
    s = re.escape(pat)
    s = s.replace(r'\*\*/', r'(?:[^/]+/)*')   # **/ → zero-or-more path segments
    s = s.replace(r'/\*\*', r'(?:/[^/]+)*')   # /** → nothing or /seg/seg…
    s = s.replace(r'\*\*', r'.*')             # ** (bare)
    s = s.replace(r'\*', r'[^/]*')            # *  → anything except /
    s = s.replace(r'\?', r'[^/]')             # ?  → single non-/ char

    if anchored or has_interior_slash:
        s = '^' + s
    else:
        # No path component → match the name anywhere in the tree
        s = r'(?:^|/)' + s

    s += r'(?:/|$)'

    return re.compile(s), negated


def _is_ignored(rel: str, patterns: list) -> bool:
    """
    Return True if *rel* (forward-slash path, relative to the ignore root)
    is blocked by the accumulated pattern list.  Later patterns win; negation
    un-ignores.
    """
    ignored = False
    for raw in patterns:
        try:
            regex, negated = _compile(raw)
        except re.error:
            continue  # skip malformed patterns rather than crashing
        if regex.search(rel):
            ignored = not negated
    return ignored


# ── .agentignore discovery ────────────────────────────────────────────────────

def _find_agentignore(start_dir: str):
    """Walk up the directory tree and return the first .agentignore found."""
    d = start_dir
    while True:
        candidate = os.path.join(d, '.agentignore')
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:       # filesystem root
            return None
        d = parent


def _load_patterns(path: str) -> list:
    with open(path, encoding='utf-8') as fh:
        return [
            line.rstrip('\n').strip()
            for line in fh
            if line.strip() and not line.strip().startswith('#')
        ]


# ── hook entry point ──────────────────────────────────────────────────────────

_FILE_TOOLS = {'Read', 'Edit', 'Write'}


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if payload.get('tool_name') not in _FILE_TOOLS:
        sys.exit(0)

    file_path = payload.get('tool_input', {}).get('file_path', '')
    if not file_path:
        sys.exit(0)

    # Resolve to absolute path using the session's working directory when available
    cwd = payload.get('cwd') or os.getcwd()
    abs_path = os.path.normpath(os.path.join(cwd, file_path))

    ignore_file = _find_agentignore(os.path.dirname(abs_path))
    if not ignore_file:
        sys.exit(0)

    try:
        patterns = _load_patterns(ignore_file)
    except Exception:
        sys.exit(0)

    if not patterns:
        sys.exit(0)

    ignore_dir = os.path.dirname(ignore_file)
    rel = os.path.relpath(abs_path, ignore_dir).replace(os.sep, '/')

    # File is outside the ignore root — don't block
    if rel.startswith('..'):
        sys.exit(0)

    if _is_ignored(rel, patterns):
        print(
            f'Blocked by .agentignore: {file_path}',
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
