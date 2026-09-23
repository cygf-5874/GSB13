"""确定性的目录归档。

只依赖标准库。
"""

from .archive import iter_entries, pack, sha256_file
from .ignores import DEFAULT_PATTERNS, IGNORE_FILE, IgnoreRules, load_patterns

__all__ = [
    "pack",
    "sha256_file",
    "iter_entries",
    "IgnoreRules",
    "load_patterns",
    "DEFAULT_PATTERNS",
    "IGNORE_FILE",
]

__version__ = "0.2.4"
