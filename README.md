# repropack

把目录打成 tar.gz，用于发布产物和构建缓存。

**核心要求：同样的目录内容，无论在什么机器、什么时间、按什么顺序写的文件，
打出来的归档必须逐字节相同。** 只有这样才能靠 SHA256 证明「你手上的包和我这边
构建出来的是同一份」。

零第三方依赖，Python 3.9 以上直接跑：

```bash
python3 -m unittest discover -s tests -v
python3 repro.py
python3 -m repropack <目录> [-o 输出.tar.gz]
```

## 公开 API

```python
from repropack import pack, sha256_file

digest = pack("build/out")          # -> 64 位小写 hex
```

| 接口 | 说明 |
| --- | --- |
| `pack(source, output=None, extra_ignores=())` | 把 `source` 目录打包成 tar.gz，返回归档的 sha256。`output` 省略时写到 `source` 同级的 `<目录名>.tar.gz`。`source` 不是目录抛 `NotADirectoryError`。 |
| `sha256_file(path)` | 算单个文件的 sha256。 |
| `iter_entries(root, rules)` | 按归档顺序产出要收进包里的文件路径。 |
| `IgnoreRules(patterns)`、`load_patterns(root, extra=())` | 忽略规则。 |

命令行：`python3 -m repropack <目录> [-o 输出]`，把 sha256 打到 stdout。

## 忽略规则

默认忽略 `.git/`、`__pycache__/`、`*.pyc`、`*.pyo`、`.venv/`、`venv/`、`*.egg-info/`，
另外读项目根下的 `.repropackignore`（`#` 开头是注释，空行忽略）。

单条模式的语义：

| 写法 | 匹配 |
| --- | --- |
| 以 `/` 结尾（如 `build/`） | 只匹配**目录名**，任意层级 |
| 含 `/` 但不以 `/` 结尾（如 `docs/draft.md`） | 按**相对根目录的路径**匹配 |
| 其他（如 `*.log`） | 匹配任意层级的文件名或目录名 |

符号链接不跟随、不进包。

## 目录

```
repropack/
  archive.py   pack / sha256_file / iter_entries
  ignores.py   忽略规则
  __main__.py  命令行入口
tests/         既有用例
repro.py       可复现性复现脚本
```
