"""把目录打包成 tar.gz。

归档是确定性的：同一份内容恒定得到逐字节相同的产物，与打包时间、
文件 mtime、属主、权限、写入顺序以及输出路径/文件名都无关。
"""

import gzip
import hashlib
import os
import tarfile
from pathlib import Path

from .ignores import IgnoreRules, load_patterns

#: 读文件算摘要时的块大小。
BLOCK_SIZE = 65536

#: 归档内所有成员统一使用的固定元数据，保证产物可复现。
FIXED_MTIME = 0
FIXED_MODE = 0o644


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
    归档内容不随环境变化：时间、属主、权限、遍历顺序都被归一化。
    """
    source = Path(source)
    if not source.is_dir():
        raise NotADirectoryError("不是目录：%s" % source)

    if output is None:
        output = source.with_name(source.name + ".tar.gz")
    output = Path(output)

    rules = IgnoreRules(load_patterns(source, extra_ignores))

    # gzip 头里的 mtime 和文件名也要固定，否则输出路径/打包时间会影响哈希。
    with open(output, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=FIXED_MTIME) as gz:
            with tarfile.open(fileobj=gz, mode="w") as archive:
                for path in iter_entries(source, rules):
                    arcname = path.relative_to(source).as_posix()
                    info = archive.gettarinfo(str(path), arcname)
                    _normalize(info)
                    if info.isreg():
                        with open(path, "rb") as handle:
                            archive.addfile(info, handle)
                    else:
                        archive.addfile(info)

    return sha256_file(output)


def _normalize(info):
    """把 TarInfo 里随环境变化的字段全部固定下来。"""
    info.mtime = FIXED_MTIME
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mode = FIXED_MODE
    return info


def iter_entries(root, rules):
    """按归档顺序（字典序、确定性）产出要收进包里的文件路径。"""
    root = Path(root)
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        kept = []
        for name in sorted(dirnames):
            child = current_path / name
            if child.is_symlink():
                continue
            rel = child.relative_to(root).as_posix()
            if rules.ignored(rel, is_dir=True):
                continue
            kept.append(name)
        dirnames[:] = kept

        for name in sorted(filenames):
            child = current_path / name
            if child.is_symlink():
                continue
            rel = child.relative_to(root).as_posix()
            if rules.ignored(rel, is_dir=False):
                continue
            yield child
