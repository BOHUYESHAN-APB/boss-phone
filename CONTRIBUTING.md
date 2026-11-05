# 贡献指南（CONTRIBUTING）

BOSS PHONE（领导电话）是一个 monorepo：ESP32-C3 固件（C + Rust 业务层）+ PC 总机房 hub（Python）+ 协议 SSOT（JSON Schema + 四端生成）+ 参考 demo。感谢你愿意参与——请先读完本文再提 PR。

> 仓库内的 agent 约定见 [`AGENTS.md`](AGENTS.md)；设计背景见 [`docs/BOSS_PHONE_DESIGN_OVERVIEW.md`](docs/BOSS_PHONE_DESIGN_OVERVIEW.md)。

## 1. 环境要求

| 工具链 | 版本 | 用途 |
|---|---|---|
| ESP-IDF | **5.5.x**（已知开发环境 5.5.3） | 固件 / 参考 demo 编译 |
| Python | **3.11+** | hub、协议向量生成器 |
| Node.js | **20+**（CI 用 20） | 协议绑定生成器 `tools/gen-protocol` |
| Rust | **stable**（edition 2021） | `protocol/rust` 绑定、`tools/stt-validate` |
| Git | 任意较新版本 | 见 `.gitattributes`（文本 LF 入库，Windows 脚本 CRLF） |

安装（在仓库根目录）：

```bash
# 协议生成器：纯 Node 内置模块（node:fs / node:path），无需 npm install
node --version

# hub 运行 + 开发依赖（在 hub/ 下）
cd hub
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# 固件（ESP-IDF 5.5.x）
source $HOME/esp/esp-idf-v5.5.3/export.sh   # 或使用本机快捷命令 get_idf553（非仓库文件）
```

## 2. 仓库布局与改动落点

| 路径 | 改这里的情况 |
|---|---|
| `firmware/components/bsp/` | 共享硬件层（显示/按键/音频/电池/I2C）。**公共 API 与引脚事实来源是 `bsp_pins.h`** |
| `firmware/`（整体） | ESP-IDF 工程；`firmware/main/`（`boss_app`：LVGL UI 薄层 + 业务层）**尚未创建**，因此当前 `firmware/` 不产出可烧录固件。新增前先读 [`docs/BOSS_PHONE_DESIGN_FIRMWARE.md`](docs/BOSS_PHONE_DESIGN_FIRMWARE.md) |
| `reference/folotoy-card-demo/` | **上游只读基线 demo**：只作参考，不在其上迭代；行为改动一律进 `firmware/`。它是当前唯一可构建、可烧录的固件工程 |
| `hub/` | PC 总机房（gateway/core/operator/input）及其测试 |
| `protocol/schema/` | 协议 **SSOT**：只改 JSON Schema，然后重新生成四端产物 |
| `protocol/{c,rust,kotlin,python}/`、`protocol/vectors/` | **生成物**，不要手改；由 `tools/gen-protocol` 输出 |
| `tools/` | 生成器、STT 评测脚本、PDF 导出 |
| `docs/` | 设计文档（新增设计请按 `BOSS_PHONE_*.md` 命名） |

**协议改动铁律**：Schema 变更必须同一次提交带齐四端生成物与黄金向量，否则 CI 必红。

## 3. 分支与 PR 流程

- `main` 为唯一长期分支，保持随时可构建、CI 全绿。
- 开发走**短期分支**，命名建议 `feat/<scope>-<short>`、`fix/<scope>-<short>`、`docs/<short>`，例如 `feat/hub-ws-token`。
- 提交 PR → 等 CI 三 job（protocol / hub / firmware）全绿 → 至少一位维护者 review → squash 或按子系统拆分合并。
- 不要 force-push `main`；不要提交任何 git 历史重写类操作（见 §8）。

## 4. 提交信息规范（Conventional Commits）

```
<type>(<scope>): <祈使句摘要，英文，≤ 72 字符>

<可选正文：为什么改、影响面>
<可选脚注：Closes #123 / BREAKING CHANGE: ...>
```

- **type**：`feat` / `fix` / `docs` / `chore` / `refactor` / `test` / `perf` / `ci` / `build`
- **scope**：`bsp` / `firmware` / `hub` / `protocol` / `docs` / `ci` / `tools` / `reference`（按改动的主子系统，优先单一 scope）
- 示例：`feat(hub): add golden-vector byte check`、`fix(bsp): correct display rotation for rev-B board`、`docs: add security threat model`、`chore(ci): add ruff steps to hub job`
- 一次提交只做一件事；把格式化和逻辑改动分开，方便 review。

## 5. 本地验证清单（提交 PR 前必跑）

按改动的影响面挑子集，**但 `protocol`/`hub`/`firmware` 三块至少覆盖你动过的**：

```bash
# ① 协议：四端生成物与 schema 同步 + 黄金向量同步（两条都必须 OK）
node tools/gen-protocol/generate.mjs --check
python tools/gen-protocol/vectors.py --check

# ② hub：lint + 格式 + 测试（71 项：L1 单元 / L2 黄金向量 / L3 WS 集成）
cd hub
python -m ruff check hub tests --output-format=concise
python -m ruff format --check hub tests
python -m pytest tests -q
cd ..

# ③ Rust 协议绑定：黄金向量 roundtrip
cargo test -p boss-protocol --quiet

# ④ 固件编译门禁（当前 CI 构建参考 demo；firmware/main 落地后改为构建 firmware/）
cd reference/folotoy-card-demo
idf.py set-target esp32c3
idf.py build
cd ../..
```

> `firmware/` 目前没有 `main/`，`idf.py build` 不产出可烧录固件；固件侧验证一律走上面的参考 demo。

- 协议生成器输出**必须提交**：`protocol/c/boss_protocol.h`、`protocol/rust/src/messages.rs`、`protocol/kotlin/BossProtocol.kt`、`protocol/python/boss_protocol.py`、`protocol/vectors/golden.json`。
- 依赖锁**必须提交**：`Cargo.lock`、`reference/folotoy-card-demo/dependencies.lock`。后者与 `firmware/components/bsp/idf_component.yml` 的依赖字段配套（`manifest_hash`），单独改一边会触发 CI 重解依赖并失败，详见 `.github/workflows/ci.yml` 的 firmware job 注释。
- 涉及 `tools/pdf-export/` 的改动可额外跑 `cd tools/pdf-export && npm ci && npm run export`（需要本机 Chrome/Edge，产物在 `_out/`，已被 gitignore）。
- 不要在 PR 里提交 `build/`、`target/`、`.venv/`、模型文件、录音样例产物等生成物（见 `.gitignore`）。

## 6. 真机验收（硬件相关改动必做）

`idf.py build` 通过只是**最低门槛**，不能替代真机验证：

- 记录**硬件批次/修订版**、供电方式（USB / 电池）、烧录命令与实际观察到的现象。
- 屏幕、按键、音频、电池相关改动必须在板子上逐项操作一遍（菜单导航 + 受影响的页面）。
- 引脚、显示旋转、codec 时钟、ADC、DMA 相关改动，请在 PR 中显式写出真机结果；无法验证时说明原因。
- ESP32-C3 **没有 PSRAM**：不要为了好看增大 LVGL 缓冲或音频分配，必须先确认内部 RAM 余量。
- 真机验收项参考 [`docs/BOSS_PHONE_DESIGN_TEST.md`](docs/BOSS_PHONE_DESIGN_TEST.md) 的 M1–M4 清单。

## 7. PR 要求

- 使用仓库的 PR 模板（`.github/PULL_REQUEST_TEMPLATE.md`）逐项勾选。
- 说明受影响的范围（固件 / hub / 协议 / 文档 / CI）与兼容性影响（协议字段、引脚、配置项）。
- **构建结果与真机结果分开报告**：CI/本地构建结论一条，真机观察结论一条（含日志片段/照片）。
- UI 或显示类改动附截图/照片；协议变更附 `--check` 输出。
- 关联 issue（`Closes #N`），并在需要时更新 `CHANGELOG.md` 的 `[Unreleased]` 段。

## 8. 代码风格与安全

- **C**：4 空格、K&R 大括号，跟随邻近文件；`snake_case`；公共硬件常量 `BSP_*`；文件内静态状态 `s_`；内部符号尽量 `static`。UI 文案用英文，注释可用中文。
- **Python**：`hub/pyproject.toml` 的 `[tool.ruff]` 是唯一规则来源（py311、line-length 100）；提交前 `ruff check` + `ruff format --check` 必须干净。
- **格式统一**：`.editorconfig`（缩进/换行/尾空格）+ `.gitattributes`（文本 LF、`*.ps1/*.bat/*.cmd` CRLF、二进制不转换）——不要让编辑器配置污染 diff。
- **密钥零入库**：`hub.toml`（含 `ws.token`、`operator.api_key`、`telemetry.github_token`）、设备 nvs 凭据、插件 token、中继 token 一律不得提交；录音数据默认不留存。发现安全问题请按 [`SECURITY.md`](SECURITY.md) 私下报告，**不要开公开 issue**。

## 9. 文档与版本

- 新增设计文档放在 `docs/`，命名 `BOSS_PHONE_DESIGN_<主题>.md`，并在 [`docs/BOSS_PHONE_DESIGN_OVERVIEW.md`](docs/BOSS_PHONE_DESIGN_OVERVIEW.md) 的文档索引中登记。
- 用 `tools/pdf-export` 重新导出文档集 PDF 时，注意 `docs/pdf/*.pdf` 已入库（约 3.2MB），不要提交临时中间产物。
- `CHANGELOG.md` 采用 Keep a Changelog 风格，面向用户的改动写进 `[Unreleased]`。
