"""把目录打包成 tar.gz。"""

import hashlib
import os
import tarfile
from pathlib import Path

from .ignores import IgnoreRules, load_patterns

#: 读文件算摘要时的块大小。
BLOCK_SIZE = 65536


def sha256_file(path):
    """算文件的 sha256，返回小写十六进制字符串。"""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(BLOCK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def pack(source, output=None, extra_ignores=()):
    """把 ``source`` 目录打包成 tar.gz，返回归档文件的 sha256。

    ``output`` 省略时写在 ``source`` 同级的 ``<目录名>.tar.gz``。
    """
    source = Path(source)
    if not source.is_dir():
        raise NotADirectoryError("不是目录：%s" % source)

    if output is None:
        output = source.with_name(source.name + ".tar.gz")
    output = Path(output)

    rules = IgnoreRules(load_patterns(source, extra_ignores))

    with tarfile.open(output, "w:gz") as archive:
        for path in iter_entries(source, rules):
            arcname = path.relative_to(source).as_posix()
            archive.add(path, arcname=arcname)

    return sha256_file(output)


def iter_entries(root, rules):
    """按归档顺序产出要收进包里的文件路径。"""
    root = Path(root)
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        kept = []
        for name in dirnames:
            child = current_path / name
            if child.is_symlink():
                continue
            rel = child.relative_to(root).as_posix()
            if rules.ignored(rel, is_dir=True):
                continue
            kept.append(name)
        dirnames[:] = kept

        for name in filenames:
            child = current_path / name
            if child.is_symlink():
                continue
            rel = child.relative_to(root).as_posix()
            if rules.ignored(rel, is_dir=False):
                continue
            yield child
