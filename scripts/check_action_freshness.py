"""Check that third-party GitHub Actions are SHA-pinned, current-runtime, and maintained.

Scans every `uses:` reference in .github/workflows/** and .github/actions/**
and reports on each non-local reference.

HARD failures (exit 1):
  (a) the reference is not pinned to a full 40-char commit SHA
  (b) the pinned SHA's action.yml declares a retired Node runtime
      (see RETIRED_NODE_RUNTIMES)
  (c) the action's repository is archived

REPORT-ONLY (never fails the run):
  - a newer release exists than the `# vX.Y.Z` comment next to the pin

`--only-unpinned` runs just check (a); it needs no network or `gh`, so it is
cheap enough to run on every PR.

Exit codes: 0 ok, 1 hard failure, 2 tool error (gh unavailable / API failure).

Usage:
  python scripts/check_action_freshness.py [--root .] [--only-unpinned]

Environment:
  GITHUB_STEP_SUMMARY  optional; a Markdown report is appended when set
  GH_TOKEN             used by the `gh` CLI (set automatically in Actions)
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# Node runtimes GitHub has retired for JavaScript actions. UPDATE THIS LIST as
# GitHub retires further runtimes (e.g. add "node24" once it is retired).
RETIRED_NODE_RUNTIMES = frozenset({"node12", "node16", "node20"})

SCAN_GLOBS = (".github/workflows/**/*.yml", ".github/workflows/**/*.yaml",
              ".github/actions/**/*.yml", ".github/actions/**/*.yaml")

USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<ref>[^\s#]+)\s*(?:#\s*(?P<comment>.*?))?\s*$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_RE = re.compile(r"v?(\d+(?:\.\d+)*)")


class GhError(RuntimeError):
    """The gh CLI failed or is unavailable."""


def parse_uses_lines(text):
    """Return [(lineno, ref, comment_or_None)] for each `uses:` line in text."""
    found = []
    for lineno, line in enumerate(text.splitlines(), 1):
        m = USES_RE.match(line)
        if m:
            found.append((lineno, m.group("ref").strip("'\""), m.group("comment")))
    return found


def is_local(ref):
    return ref.startswith("./") or ref.startswith("../")


def is_sha(value):
    return bool(SHA_RE.match(value or ""))


def split_ref(ref):
    """'owner/repo/sub/path@ref' -> (owner/repo, 'sub/path', ref). ref may be ''."""
    name, _, version = ref.partition("@")
    parts = name.split("/")
    repo = "/".join(parts[:2])
    path = "/".join(parts[2:])
    return repo, path, version


def collect(root):
    """Scan root and return [{file, line, ref, comment}] for every non-local uses."""
    root = Path(root)
    seen, entries = set(), []
    for pattern in SCAN_GLOBS:
        for path in sorted(root.glob(pattern)):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            text = path.read_text(encoding="utf-8")
            for lineno, ref, comment in parse_uses_lines(text):
                if is_local(ref):
                    continue
                entries.append({"file": path.relative_to(root).as_posix(),
                                "line": lineno, "ref": ref, "comment": comment})
    return entries


def pin_problem(ref):
    """Return a message if ref is not SHA-pinned, else None."""
    if ref.startswith("docker://"):
        return None if "@sha256:" in ref else "docker image not pinned to a digest"
    _, _, version = split_ref(ref)
    if not is_sha(version):
        return "not pinned to a 40-char commit SHA (found %r)" % (version or "no ref")
    return None


def gh(args):
    try:
        proc = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GhError("gh invocation failed: %s" % exc)
    if proc.returncode != 0:
        raise GhError("gh %s failed: %s" % (" ".join(args), proc.stderr.strip()))
    return proc.stdout


def runtime_of(action_yml_text):
    """Extract `runs.using` from action.yml text (stdlib only, no YAML parser)."""
    in_runs = False
    for line in action_yml_text.splitlines():
        if re.match(r"^runs:\s*(#.*)?$", line):
            in_runs = True
            continue
        if in_runs:
            if re.match(r"^\S", line):
                break
            m = re.match(r"^\s+using:\s*['\"]?([\w.-]+)", line)
            if m:
                return m.group(1)
    return None


def fetch_action_yml(repo, path, sha):
    base = path + "/" if path else ""
    last = None
    for name in ("action.yml", "action.yaml"):
        try:
            return gh(["api", "-H", "Accept: application/vnd.github.raw",
                       "repos/%s/contents/%s%s?ref=%s" % (repo, base, name, sha)])
        except GhError as exc:
            last = exc
    raise last


def is_archived(repo):
    return gh(["api", "repos/%s" % repo, "--jq", ".archived"]).strip() == "true"


def latest_release(repo):
    """Latest release tag, or None if the repo has no releases."""
    try:
        return gh(["api", "repos/%s/releases/latest" % repo, "--jq", ".tag_name"]).strip()
    except GhError as exc:
        if "404" in str(exc):
            return None
        raise


def version_tuple(text):
    m = VERSION_RE.search(text or "")
    return tuple(int(p) for p in m.group(1).split(".")) if m else None


def newer_available(pinned_comment, latest):
    """True if `latest` is a strictly newer version than the pin's comment."""
    cur, new = version_tuple(pinned_comment), version_tuple(latest)
    return bool(cur and new and new > cur)


def check(entries, only_unpinned=False):
    """Return (failures, notices) as lists of strings."""
    failures, notices = [], []
    cache = {}

    def cached(key, fn):
        if key not in cache:
            cache[key] = fn()
        return cache[key]

    for e in entries:
        where = "%s:%d %s" % (e["file"], e["line"], e["ref"])
        problem = pin_problem(e["ref"])
        if problem:
            failures.append("%s: %s" % (where, problem))
            continue
        if only_unpinned or e["ref"].startswith("docker://"):
            continue
        repo, path, sha = split_ref(e["ref"])
        using = cached(("rt", repo, path, sha),
                       lambda: runtime_of(fetch_action_yml(repo, path, sha)))
        if using in RETIRED_NODE_RUNTIMES:
            failures.append("%s: uses retired runtime %s" % (where, using))
        if cached(("arch", repo), lambda: is_archived(repo)):
            failures.append("%s: repository %s is archived" % (where, repo))
        latest = cached(("rel", repo), lambda: latest_release(repo))
        if latest and newer_available(e["comment"], latest):
            notices.append("%s: newer release %s available (pinned %s)"
                           % (where, latest, (e["comment"] or "").strip()))
    return failures, notices


def render_summary(failures, notices, total):
    lines = ["## GitHub Actions freshness", "",
             "Checked %d non-local `uses:` references." % total, ""]
    lines.append("### Failures" if failures else "### No failures")
    lines += ["- " + f for f in failures]
    lines += ["", "### Newer releases available (informational)"]
    lines += ["- " + n for n in notices] or ["- none"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    parser.add_argument("--only-unpinned", action="store_true",
                        help="only check SHA pinning (no network/gh needed)")
    args = parser.parse_args(argv)

    entries = collect(args.root)
    try:
        failures, notices = check(entries, only_unpinned=args.only_unpinned)
    except GhError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    print("Checked %d non-local uses: references" % len(entries))
    for f in failures:
        print("FAIL: " + f)
    for n in notices:
        print("INFO: " + n)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(render_summary(failures, notices, len(entries)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
