# AI Sticker Library

一个公开、机器可读的表情包库，供 AI Agent 检索和使用。每张表情都带有情绪、标签、描述和建议使用场景，AI 可以先读 `manifest.json`，再按语义选图。

> 当前状态：v0 骨架，暂无图片。按「添加第一张表情」操作即可开始填充。

## 给 AI 使用

仓库发布后，清单地址为：

```text
https://raw.githubusercontent.com/intonebaby857/ai-sticker-library/main/manifest.json
```

推荐流程：

1. 读取 `manifest.json`；
2. 按 `emotion`、`tags`、`usage` 过滤出候选；
3. 用 `base_url + file` 拼出图片地址；
4. 结合 `description` 和 `usage` 判断是否适合当前语境。

`base_url` 已指向本仓库的 raw 地址，图片地址由它和 `file` 拼接。

更完整的接入说明见 [docs/ai-usage.md](docs/ai-usage.md)。

## 目录结构

```text
.
├── manifest.json          # AI 读取的总清单（由脚本生成）
├── schema/                # 清单的 JSON Schema
├── stickers/              # 按情绪分类的图片与同名 sidecar 元数据
│   ├── happy/
│   ├── sad/
│   └── ...
├── scripts/
│   ├── build_manifest.py  # 扫描图片，生成 manifest.json
│   └── validate_manifest.py
├── examples/              # sidecar 示例
└── docs/                  # 使用说明
```

## 添加第一张表情

1. 把图片放进 `stickers/<情绪>/`。建议：512×512、PNG 或 WebP、透明背景、小于 500 KB；文件名用英文小写加连字符，例如 `happy-001.png`。
2. 在同一目录创建同名 sidecar：`happy-001.png.json`，格式参照 [examples/happy-001.png.json](examples/happy-001.png.json)。
3. 在仓库根目录运行：

```bash
python3 scripts/build_manifest.py
python3 scripts/validate_manifest.py
```

4. 提交并推送。

脚本只依赖 Python 3 标准库，不需要安装额外包。

## 清单字段

| 字段 | 说明 |
| --- | --- |
| `id` | 唯一标识，默认取图片文件名（不含扩展名） |
| `file` | 图片相对仓库根目录的路径 |
| `emotion` | 主要情绪，缺省为所在目录名 |
| `tags` | 检索标签，中英文均可 |
| `description` | 画面描述，供 AI 理解内容 |
| `usage` | 建议使用场景 |
| `format` / `bytes` / `sha256` | 图片格式、大小与校验值 |

## 约定

- 只收录有权使用的图片；本仓库默认采用 CC0。
- 新增或替换图片后必须重新生成 `manifest.json`。
- CI 会在推送时运行 `scripts/validate_manifest.py`，清单与图片不一致会导致检查失败。

## License

- 表情图片与元数据：CC0 1.0 Universal（公共领域贡献）
- 脚本代码：MIT，见 [LICENSE-MIT](LICENSE-MIT)
