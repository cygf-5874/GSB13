import gzip
import os
import tarfile
import tempfile
import unittest
from pathlib import Path

from repropack import pack, sha256_file


FILES = {
    "main.py": b"print('hello')\n",
    "pkg/core.py": b"VALUE = 42\n",
    "pkg/sub/deep.txt": b"deep\n",
    "docs/guide.md": b"# guide\n",
}


def make_tree(root, names, mtime=None, mode=None):
    for rel in names:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(FILES[rel])
        if mode is not None:
            path.chmod(mode)
        if mtime is not None:
            os.utime(path, (mtime, mtime))


class DeterministicPackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_same_content_has_same_bytes_across_paths_and_filesystem_state(self):
        first = self.home / "first"
        second = self.home / "second"
        make_tree(
            first,
            list(FILES),
            mtime=1_600_000_000,
            mode=0o600,
        )
        make_tree(
            second,
            reversed(FILES),
            mtime=1_700_000_000,
            mode=0o755,
        )

        first_output = self.home / "one" / "artifact.tar.gz"
        second_output = self.home / "two" / "release.tar.gz"
        first_output.parent.mkdir()
        second_output.parent.mkdir()

        first_digest = pack(first, first_output)
        second_digest = pack(second, second_output)

        self.assertEqual(first_digest, second_digest)
        self.assertEqual(first_digest, sha256_file(first_output))
        self.assertEqual(first_output.read_bytes(), second_output.read_bytes())

    def test_archive_metadata_is_normalized(self):
        root = self.home / "root"
        make_tree(root, ["main.py", "pkg/core.py"], mtime=1_700_000_000, mode=0o600)
        output = self.home / "artifact.tar.gz"
        pack(root, output)

        raw = output.read_bytes()
        self.assertEqual(raw[4:8], b"\x00\x00\x00\x00")
        self.assertEqual(raw[3] & 0b00001000, 0)

        with tarfile.open(fileobj=gzip.open(output, "rb"), mode="r:") as archive:
            for member in archive.getmembers():
                self.assertEqual(member.mtime, 0)
                self.assertEqual(member.mode, 0o644)
                self.assertEqual(member.uid, 0)
                self.assertEqual(member.gid, 0)
                self.assertEqual(member.uname, "")
                self.assertEqual(member.gname, "")

    def test_output_inside_source_is_not_archived(self):
        root = self.home / "root"
        root.mkdir()
        (root / "main.py").write_bytes(b"print('hello')\n")
        output = root / "release.tar.gz"

        pack(root, output)

        with tarfile.open(output, "r:gz") as archive:
            self.assertEqual(archive.getnames(), ["main.py"])


if __name__ == "__main__":
    unittest.main()
