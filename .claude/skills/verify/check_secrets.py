#!/usr/bin/env python3
"""Scan tracked files for credentials before they reach a public repo.

This repo is public and holds two Worker sources. Until now the only thing
standing between a pasted token and GitHub was someone remembering to look at
the diff. That is not a control, it is a habit — and habits fail at 2am.

Scans what git tracks, so untracked scratch files are ignored and anything
staged for commit is covered.

Usage: python3 .claude/skills/verify/check_secrets.py
Exit 0 = clean, 1 = something that looks like a credential.
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

# Binary or vendored files that cannot hold a pasted secret in reviewable form.
SKIP_DIRS = ("fonts/", ".git/")
SKIP_SUFFIX = (".woff2", ".png", ".jpg", ".jpeg", ".webp", ".avif", ".ico")

# (name, pattern, note). Ordered most-specific first so messages stay useful.
PATTERNS = [
    ("private key", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", ""),
    ("AWS access key id", r"\bAKIA[0-9A-Z]{16}\b", ""),
    ("OpenAI key", r"\bsk-[A-Za-z0-9]{20,}\b", ""),
    ("GitHub token", r"\bgh[pousr]_[A-Za-z0-9]{30,}\b", ""),
    ("Slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b", ""),
    ("Cloudflare API token", r"\bv1\.0-[A-Za-z0-9_-]{40,}\b", ""),
    ("Google API key", r"\bAIza[0-9A-Za-z_-]{35}\b", ""),
    ("JWT", r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b", ""),
    # A literal bearer token, as opposed to the $ADMIN_TOKEN placeholder that
    # appears all over the docs.
    ("literal Bearer token", r"Bearer\s+(?!\$|\{)[A-Za-z0-9_\-\.=+/]{24,}", ""),
    # secret = "……" with a long literal value. Placeholders using $VAR, ${VAR},
    # <PLACEHOLDER> or an env lookup are not matched.
    ("assigned credential",
     r"""(?i)\b(?:secret|token|passwd|password|api[_-]?key|access[_-]?key|"""
     r"""client[_-]?secret)\b\s*[:=]\s*["'](?!\$|\{|<|env\.|process\.)"""
     r"""[A-Za-z0-9_\-\.=+/]{20,}["']""",
     "if this is a placeholder, write it as $VAR so it reads as one"),
]

# Values that look secret-shaped but are public identifiers. Each needs a reason.
ALLOWED = {
    # KV namespace id — an account-scoped identifier, not a credential. It is in
    # wrangler.toml, SETUP.md and the vault already, and is useless without the
    # account's own OAuth.
    "6c7174d740cc4cb99315a913dec80746",
}


def tracked_files():
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("not a git repo, or git failed: " + out.stderr.strip())
    for rel in out.stdout.splitlines():
        if rel.startswith(SKIP_DIRS) or rel.endswith(SKIP_SUFFIX):
            continue
        yield rel


def main():
    findings = []
    scanned = 0

    for rel in tracked_files():
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        scanned += 1

        for lineno, line in enumerate(text.splitlines(), 1):
            for name, pattern, note in PATTERNS:
                m = re.search(pattern, line)
                if not m:
                    continue
                hit = m.group(0)
                if any(a in hit for a in ALLOWED):
                    continue
                # Never print the match itself — that would copy a suspected
                # secret into terminal scrollback and CI logs.
                findings.append((rel, lineno, name, len(hit), note))
                break

    print("files scanned: %d" % scanned)
    if not findings:
        print("no credentials found in tracked files")
        return 0

    print("\nPossible credentials — the repo is PUBLIC, check before committing:\n")
    for rel, lineno, name, length, note in findings:
        print("  %s:%d" % (rel, lineno))
        print("      looks like a %s (%d chars, value not printed)" % (name, length))
        if note:
            print("      %s" % note)
    print("\nIf one is a false positive, add it to ALLOWED in %s"
          % pathlib.Path(__file__).name)
    print("with a comment saying why it is safe to publish.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
