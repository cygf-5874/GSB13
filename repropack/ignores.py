"""忽略规则：默认规则 + 项目根下的 ``.repropackignore``。"""

import fnmatch
from pathlib import Path

#: 一定会被忽略的条目。
DEFAULT_PATTERNS = (
    ".git/",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    ".venv/",
    "venv/",
    "*.egg-info/",
)

#: 项目根下用来追加规则的文件的文件名。
IGNORE_FILE = ".repropackignore"


class IgnoreRules:
    """一组忽略模式。

    单条模式的语义：

    - 以 ``/`` 结尾 —— 只匹配**目录名**（任意层级）；
    - 含 ``/``（且不以 ``/`` 结尾）—— 按**相对根目录的路径**匹配；
    - 其他 —— 匹配任意层级的**文件名或目录名**。
    """

    def __init__(self, patterns=()):
        self._patterns = [pattern for pattern in patterns if pattern]

    @property
    def patterns(self):
        return list(self._patterns)

    def ignored(self, relpath, is_dir=False):
        """``relpath`` 用 ``/`` 分隔，相对根目录。"""
        rel = str(relpath).replace("\\", "/").strip("/")
        if not rel:
            return False
        parts = rel.split("/")

        for pattern in self._patterns:
            if pattern.endswith("/"):
                name = pattern[:-1]
                last = len(parts) - 1
                for index, part in enumerate(parts):
                    if index == last and not is_dir:
                        continue
                    if fnmatch.fnmatch(part, name):
                        return True
                continue

            if "/" in pattern:
                if fnmatch.fnmatch(rel, pattern):
                    return True
                continue

            if any(fnmatch.fnmatch(part, pattern) for part in parts):
                return True

        return False

    def __repr__(self):
        return "IgnoreRules(%r)" % (self._patterns,)


def load_patterns(root, extra=()):
    """默认规则 + ``root/.repropackignore`` + ``extra``。"""
    patterns = list(DEFAULT_PATTERNS)
    ignore_file = Path(root) / IGNORE_FILE
    if ignore_file.is_file():
        for line in ignore_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    patterns.extend(extra)
    return patterns
