import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_action_freshness as caf  # noqa: E402

SHA = "a" * 40
PINNED = "actions/checkout@%s" % SHA


def entry(ref, comment="v1.0.0"):
    return {"file": "w.yml", "line": 1, "ref": ref, "comment": comment}


class ParsingTests(unittest.TestCase):
    def test_parse_uses_lines(self):
        text = ("steps:\n"
                "  - uses: actions/checkout@%s # v6.1.0\n"
                "    with: {}\n"
                "  - name: x\n"
                "    uses: ./.github/actions/foo\n"
                "    # uses: commented/out@v1\n" % SHA)
        got = caf.parse_uses_lines(text)
        self.assertEqual(got, [(2, "actions/checkout@" + SHA, "v6.1.0"),
                               (5, "./.github/actions/foo", None)])

    def test_split_ref_with_subpath(self):
        self.assertEqual(caf.split_ref("a/b/sub/dir@" + SHA), ("a/b", "sub/dir", SHA))

    def test_collect_skips_local(self):
        with tempfile.TemporaryDirectory() as d:
            wf = Path(d, ".github", "workflows")
            wf.mkdir(parents=True)
            (wf / "x.yml").write_text(
                "steps:\n  - uses: ./.github/actions/a\n  - uses: o/r@v1\n")
            got = caf.collect(d)
        self.assertEqual([e["ref"] for e in got], ["o/r@v1"])


class ShaTests(unittest.TestCase):
    def test_is_sha(self):
        self.assertTrue(caf.is_sha(SHA))
        self.assertFalse(caf.is_sha("v6"))
        self.assertFalse(caf.is_sha("a" * 39))
        self.assertFalse(caf.is_sha("A" * 40))
        self.assertFalse(caf.is_sha(None))

    def test_pin_problem(self):
        self.assertIsNone(caf.pin_problem(PINNED))
        self.assertIn("not pinned", caf.pin_problem("actions/checkout@v6"))
        self.assertIn("not pinned", caf.pin_problem("actions/checkout"))
        self.assertIsNone(caf.pin_problem("docker://x@sha256:" + "b" * 64))
        self.assertIsNotNone(caf.pin_problem("docker://x:latest"))


class RuntimeTests(unittest.TestCase):
    def test_runtime_of(self):
        self.assertEqual(caf.runtime_of("name: x\nruns:\n  using: 'node20'\n  main: a.js\n"), "node20")
        self.assertEqual(caf.runtime_of("runs:\n  using: composite\n"), "composite")
        self.assertIsNone(caf.runtime_of("name: x\n"))

    def test_newer_available(self):
        self.assertTrue(caf.newer_available("v6.1.0", "v7.0.1"))
        self.assertFalse(caf.newer_available("v7.0.1", "v7.0.1"))
        self.assertFalse(caf.newer_available(None, "v7.0.1"))


class CheckTests(unittest.TestCase):
    def run_check(self, entries, using="node24", archived=False, latest="v1.0.0", **kw):
        with mock.patch.object(caf, "fetch_action_yml", return_value="runs:\n  using: %s\n" % using), \
             mock.patch.object(caf, "is_archived", return_value=archived), \
             mock.patch.object(caf, "latest_release", return_value=latest):
            return caf.check(entries, **kw)

    def test_clean(self):
        self.assertEqual(self.run_check([entry(PINNED)]), ([], []))

    def test_unpinned_fails_without_network(self):
        with mock.patch.object(caf, "gh", side_effect=AssertionError("no gh")):
            failures, _ = caf.check([entry("actions/checkout@v6")], only_unpinned=True)
        self.assertEqual(len(failures), 1)

    def test_only_unpinned_skips_network_for_pinned(self):
        with mock.patch.object(caf, "gh", side_effect=AssertionError("no gh")):
            self.assertEqual(caf.check([entry(PINNED)], only_unpinned=True), ([], []))

    def test_retired_runtime_fails(self):
        for rt in ("node12", "node16", "node20"):
            failures, _ = self.run_check([entry(PINNED)], using=rt)
            self.assertTrue(any("retired runtime " + rt in f for f in failures))

    def test_archived_fails(self):
        failures, _ = self.run_check([entry(PINNED)], archived=True)
        self.assertTrue(any("archived" in f for f in failures))

    def test_newer_release_is_notice_only(self):
        failures, notices = self.run_check([entry(PINNED)], latest="v2.0.0")
        self.assertEqual(failures, [])
        self.assertEqual(len(notices), 1)

    def test_gh_error_propagates(self):
        with mock.patch.object(caf, "fetch_action_yml", side_effect=caf.GhError("boom")):
            with self.assertRaises(caf.GhError):
                caf.check([entry(PINNED)])

    def test_main_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            wf = Path(d, ".github", "workflows")
            wf.mkdir(parents=True)
            (wf / "x.yml").write_text("steps:\n  - uses: o/r@v1\n")
            self.assertEqual(caf.main(["--root", d, "--only-unpinned"]), 1)
            (wf / "x.yml").write_text("steps:\n  - uses: o/r@%s # v1.0.0\n" % SHA)
            self.assertEqual(caf.main(["--root", d, "--only-unpinned"]), 0)


if __name__ == "__main__":
    unittest.main()
