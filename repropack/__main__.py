"""命令行入口：``python3 -m repropack <目录> [-o 输出]``。"""

import argparse
import sys

from .archive import pack


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python3 -m repropack",
        description="把目录打包成 tar.gz，并打印归档的 sha256",
    )
    parser.add_argument("source", help="要打包的目录")
    parser.add_argument("-o", "--output", default=None, help="输出文件路径")
    args = parser.parse_args(argv)

    digest = pack(args.source, args.output)
    print(digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
