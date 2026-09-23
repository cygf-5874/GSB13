import tarfile
import tempfile
import unittest
from pathlib import Path

from repropack import pack, sha256_file

EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def make_tree(root, files):
    for rel, content in files.items():
        path = Path(root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))


class Sha256Test(unittest.TestCase):
    def test_matches_known_value_for_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.bin"
            path.write_bytes(b"")
            self.assertEqual(sha256_file(path), EMPTY_SHA256)


class PackTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.root = self.home / "proj"
        self.root.mkdir()
        self.output = self.home / "out.tar.gz"
        make_tree(
            self.root,
            {
                "main.py": "print('hi')\n",
                "pkg/util.py": "VALUE = 1\n",
                "docs/readme.md": "# doc\n",
            },
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _names(self, output=None):
        with tarfile.open(output or self.output, "r:gz") as archive:
            return set(archive.getnames())

    def test_returns_lowercase_hex_digest(self):
        digest = pack(self.root, self.output)
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, digest.lower())
        int(digest, 16)

    def test_digest_matches_the_written_file(self):
        digest = pack(self.root, self.output)
        self.assertEqual(digest, sha256_file(self.output))

    def test_default_output_sits_next_to_source(self):
        pack(self.root)
        self.assertTrue(self.root.with_name("proj.tar.gz").is_file())

    def test_archive_lists_expected_members(self):
        pack(self.root, self.output)
        self.assertEqual(
            self._names(), {"main.py", "pkg/util.py", "docs/readme.md"}
        )

    def test_member_content_round_trips(self):
        pack(self.root, self.output)
        with tarfile.open(self.output, "r:gz") as archive:
            handle = archive.extractfile("pkg/util.py")
            self.assertEqual(handle.read(), b"VALUE = 1\n")

    def test_dot_git_is_ignored(self):
        make_tree(self.root, {".git/config": "[core]\n", ".git/HEAD": "ref\n"})
        pack(self.root, self.output)
        names = self._names()
        self.assertNotIn(".git/config", names)
        self.assertNotIn(".git/HEAD", names)

    def test_pycache_and_pyc_are_ignored(self):
        make_tree(
            self.root,
            {"__pycache__/x.pyc": "junk", "pkg/__pycache__/y.pyc": "junk"},
        )
        pack(self.root, self.output)
        self.assertFalse([name for name in self._names() if name.endswith(".pyc")])

    def test_extra_ignores_are_applied(self):
        make_tree(self.root, {"notes.log": "x\n"})
        pack(self.root, self.output, extra_ignores=["*.log"])
        self.assertNotIn("notes.log", self._names())

    def test_repropackignore_file_is_honoured(self):
        make_tree(self.root, {"secret.env": "K=1\n", ".repropackignore": "*.env\n"})
        pack(self.root, self.output)
        names = self._names()
        self.assertNotIn("secret.env", names)
        self.assertIn(".repropackignore", names)

    def test_missing_directory_raises(self):
        with self.assertRaises(NotADirectoryError):
            pack(self.root / "nope", self.output)

    def test_empty_directory_produces_an_empty_archive(self):
        empty = self.home / "empty"
        empty.mkdir()
        target = self.home / "empty.tar.gz"
        digest = pack(empty, target)
        self.assertEqual(len(digest), 64)
        with tarfile.open(target, "r:gz") as archive:
            self.assertEqual(archive.getnames(), [])

    def test_symlinks_are_skipped(self):
        target = self.root / "real.txt"
        target.write_text("real\n", encoding="utf-8")
        link = self.root / "link.txt"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("当前系统不支持创建符号链接")
        pack(self.root, self.output)
        self.assertNotIn("link.txt", self._names())


if __name__ == "__main__":
    unittest.main()
