"""同一份内容打两次包，比对 sha256 —— 用来复现「构建不可复现」的问题。

期望：两次的 sha256 完全相同（这样才能靠哈希证明「手上的包和构建产物是同一份」）。
"""

import os
import sys
import tempfile
import time
from pathlib import Path

from repropack import pack

FILES = {
    "main.py": "print('hello')\n",
    "pkg/core.py": "VALUE = 42\n",
    "pkg/sub/deep.txt": "deep\n",
    "docs/guide.md": "# guide\n",
}


def build(root, order, mtime_offset=0.0):
    """按 ``order`` 的顺序写入同样内容，可整体平移 mtime。"""
    root.mkdir(parents=True, exist_ok=True)
    for rel in order:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(FILES[rel].encode("utf-8"))
    if mtime_offset:
        stamp = time.time() + mtime_offset
        for rel in FILES:
            os.utime(root / rel, (stamp, stamp))
    return root


def report(title, first, second):
    same = first == second
    print("%s：%s" % (title, "一致" if same else "不一致"))
    print("  a %s" % first)
    print("  b %s" % second)
    return same


def main():
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        pack_one = home / "one.tar.gz"

        # 场景一：同一个目录连打两次（中间故意跨过一秒）
        base = build(home / "base", list(FILES))
        first = pack(base, pack_one)
        time.sleep(1.1)
        second = pack(base, pack_one)
        ok_one = report("场景一 同一个目录连打两次（中间跨了一秒）", first, second)

        # 场景二：内容相同，只有 mtime 不同
        shifted = build(home / "shifted", list(FILES), mtime_offset=3600)
        ok_two = report(
            "场景二 内容相同、mtime 差一小时",
            pack(base, home / "base.tar.gz"),
            pack(shifted, home / "shifted.tar.gz"),
        )

        # 场景三：内容相同，只有写入顺序不同
        reordered = build(home / "reordered", list(reversed(list(FILES))))
        ok_three = report(
            "场景三 内容相同、写入顺序相反",
            pack(base, home / "base.tar.gz"),
            pack(reordered, home / "reordered.tar.gz"),
        )

    if ok_one and ok_two and ok_three:
        print("\n可复现：同一份内容恒定得到同一个 sha256")
        return 0
    print("\n不可复现：同一份内容得到了不同的 sha256")
    return 1


if __name__ == "__main__":
    sys.exit(main())
