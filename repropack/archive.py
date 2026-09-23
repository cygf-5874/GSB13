"""把目录打包成 tar.gz。"""

import gzip
import hashlib
import os
import tarfile
from pathlib import Path

from .ignores import IgnoreRules, load_patterns

#: 读文件算摘要时的块大小。
BLOCK_SIZE = 65536

#: 固定归档中的文件时间，避免读取源文件的 mtime。
FIXED_MTIME = 0

#: 固定归档中的文件权限，避免读取源文件的权限位。
FIXED_MODE = 0o644

#: 固定 gzip 压缩级别，避免不同调用使用不同默认值。
COMPRESS_LEVEL = 9


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

    with output.open("wb") as compressed:
        with gzip.GzipFile(
            filename="",
            fileobj=compressed,
            mode="wb",
            compresslevel=COMPRESS_LEVEL,
            mtime=FIXED_MTIME,
        ) as gzipped:
            with tarfile.open(fileobj=gzipped, mode="w") as archive:
                for path in iter_entries(source, rules):
                    if os.path.abspath(path) == os.path.abspath(output):
                        continue

                    arcname = path.relative_to(source).as_posix()
                    info = archive.gettarinfo(path, arcname=arcname)
                    if info is None:
                        continue

                    if info.type == tarfile.LNKTYPE:
                        info.type = tarfile.REGTYPE
                        info.linkname = ""
                        info.size = path.stat().st_size

                    info.mtime = FIXED_MTIME
                    info.mode = FIXED_MODE
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.pax_headers = {}

                    if info.type in (tarfile.CHRTYPE, tarfile.BLKTYPE):
                        info.devmajor = 0
                        info.devminor = 0

                    if info.isreg():
                        with path.open("rb") as handle:
                            archive.addfile(info, handle)
                    else:
                        archive.addfile(info)

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
        dirnames[:] = sorted(kept)

        for name in sorted(filenames):
            child = current_path / name
            if child.is_symlink():
                continue
            rel = child.relative_to(root).as_posix()
            if rules.ignored(rel, is_dir=False):
                continue
            yield child
