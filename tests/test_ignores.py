import tempfile
import unittest
from pathlib import Path

from repropack import DEFAULT_PATTERNS, IgnoreRules, load_patterns


class DefaultPatternsTest(unittest.TestCase):
    def test_contains_vcs_and_cache_entries(self):
        self.assertIn(".git/", DEFAULT_PATTERNS)
        self.assertIn("__pycache__/", DEFAULT_PATTERNS)
        self.assertIn("*.pyc", DEFAULT_PATTERNS)


class IgnoreRulesTest(unittest.TestCase):
    def setUp(self):
        self.rules = IgnoreRules(
            [".git/", "__pycache__/", "*.pyc", "docs/draft.md", "tmp"]
        )

    def test_directory_pattern_matches_at_any_level(self):
        self.assertTrue(self.rules.ignored(".git", is_dir=True))
        self.assertTrue(self.rules.ignored("src/__pycache__", is_dir=True))
        self.assertTrue(self.rules.ignored("a/b/__pycache__", is_dir=True))

    def test_directory_pattern_does_not_match_a_file(self):
        self.assertFalse(self.rules.ignored("__pycache__", is_dir=False))
        self.assertFalse(self.rules.ignored(".git", is_dir=False))

    def test_suffix_pattern_matches_at_any_level(self):
        self.assertTrue(self.rules.ignored("mod.pyc"))
        self.assertTrue(self.rules.ignored("pkg/mod.pyc"))

    def test_path_pattern_is_anchored_at_root(self):
        self.assertTrue(self.rules.ignored("docs/draft.md"))
        self.assertFalse(self.rules.ignored("other/docs/draft.md"))

    def test_plain_name_matches_at_any_level(self):
        self.assertTrue(self.rules.ignored("tmp", is_dir=True))
        self.assertTrue(self.rules.ignored("x/tmp", is_dir=True))

    def test_ordinary_files_are_kept(self):
        self.assertFalse(self.rules.ignored("main.py"))
        self.assertFalse(self.rules.ignored("src/app/main.py"))

    def test_empty_path_is_kept(self):
        self.assertFalse(self.rules.ignored(""))

    def test_backslashes_are_normalized(self):
        self.assertTrue(self.rules.ignored("src\\__pycache__", is_dir=True))

    def test_patterns_property_returns_a_copy(self):
        patterns = self.rules.patterns
        patterns.append("zzz")
        self.assertNotIn("zzz", self.rules.patterns)


class LoadPatternsTest(unittest.TestCase):
    def test_reads_ignore_file_and_skips_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".repropackignore").write_text(
                "# 注释\n\n*.log\nbuild/\n", encoding="utf-8"
            )
            patterns = load_patterns(root)
            self.assertIn("*.log", patterns)
            self.assertIn("build/", patterns)
            self.assertNotIn("# 注释", patterns)

    def test_extra_patterns_are_appended(self):
        with tempfile.TemporaryDirectory() as tmp:
            patterns = load_patterns(tmp, extra=["*.bak"])
            self.assertIn("*.bak", patterns)
            self.assertIn(".git/", patterns)

    def test_missing_ignore_file_is_fine(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_patterns(tmp), list(DEFAULT_PATTERNS))


if __name__ == "__main__":
    unittest.main()
