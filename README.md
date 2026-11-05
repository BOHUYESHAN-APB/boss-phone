# BOSS PHONE（领导电话）

> English version: [README.zh_CN.md](README.zh_CN.md)

给非技术决策者用的 AI 指挥终端：一块 ESP32-C3 哑终端 + PC 总机房（Hub）。语音指令经 Hub 变成对本地 AI Agent（claude-code / codex / opencode 等）的操作，Agent 的状态、权限请求、关键结果再回传到板子屏幕上。

仓库当前是**PC 侧已可运行、板端入口尚未创建**的状态。本文只写能在仓库里指到文件和能复现命令的事实。

## 当前状态

### 已完成（每条都有对应文件与命令）

| 模块 | 内容 | 证据 |
|---|---|---|
| 协议 SSOT | 9 条消息的 JSON Schema + C / Rust / Kotlin / Python 四端生成绑定 | `protocol/schema/`（9 个 `.json`）、`protocol/{c,rust,kotlin,python}/`；`node tools/gen-protocol/generate.mjs --check` 输出 `OK` 四端产物 |
| 协议黄金向量 | 14 条控制帧 + 5 条媒体帧 + 1 条混排流，四端共同字节基准 | `protocol/vectors/golden.json`；`python tools/gen-protocol/vectors.py --check` 通过 |
| Hub 网关与核心 | CDC 串口 / WebSocket 双入口、分帧、设备会话、路由决策、事件总线 | `hub/hub/gateway/{cdc,ws,framing,handler}.py`、`hub/hub/core/{session,router,eventbus}.py` |
| Hub 语音输入法链路 | 三引擎 STT（windows / whisper / cloud）+ 词表纠错 + Windows 光标注入 | `hub/hub/operator/{stt,correct,provider}.py`、`hub/hub/input/inject.py`、`hub/hub/dictation.py`；`python hub-lite.py --selftest` → `✓ 前台窗口` / `✓ SendInput API 可用`，exit 0 |
| Hub 自动化测试 | 7 个测试文件、71 个用例全绿（约 2s） | `cd hub && python -m pytest tests -q` → `71 passed` |
| 代码风格门禁 | ruff lint + format 全过（配置在 `hub/pyproject.toml`，`ruff` 随 `requirements-dev.txt` 安装） | `cd hub && ruff check hub tests && ruff format --check hub tests` → `All checks passed!` |
| CI | protocol / hub / firmware 三个 job | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |

### 进行中

| 项 | 现状 |
|---|---|
| windows-native STT 准确率评测 | 脚本与样本已就绪（`tools/stt-samples/`），需在用户自己的终端跑 `eval-windows.ps1`：SAPI 要写 `%LOCALAPPDATA%\Microsoft\Speech` 适配缓存，受限环境里识别返回空 |
| Hub ↔ 真板 CDC 联调 | Hub 侧入口已实装（`hub/hub/gateway/cdc.py`），无实机可验证 |

### 未开始

| 项 | 说明 |
|---|---|
| `firmware/main/`（板端 LVGL UI 薄层 + boss_app） | `firmware/` 目前只有共享硬件层 `components/bsp/`，**没有 `main/`、没有 `app_main`**，不产出可烧录固件；这是 M1 的任务（见 [DESIGN_FIRMWARE](docs/BOSS_PHONE_DESIGN_FIRMWARE.md)） |
| `plugins/`（CLI 插件桥） | 目录尚未创建，设计见 [DESIGN_PLUGIN](docs/BOSS_PHONE_DESIGN_PLUGIN.md) |
| Android App | 目录尚未创建，设计见 [DESIGN_ANDROID](docs/BOSS_PHONE_DESIGN_ANDROID.md) |

### 已知限制

- ESP32-C3 **没有 PSRAM**：LVGL 缓冲与音频缓冲都吃内部 RAM，改动前先看 `firmware/sdkconfig.defaults` 与 `docs/AI_HARDWARE_DEVELOPMENT_GUIDE.md` 的内存约束。
- `windows-native` STT 与光标注入是 **Windows 专属**，CI 的 Linux runner 不跑这两条路径。
- 协议 Schema 与四端绑定必须同步提交，否则 CI 的 protocol job 失败。

## 系统架构

```
┌──────────────┐   语音/按键   ┌────────────────┐   本机/局域网   ┌──────────────┐
│ 板子（哑终端）│ ◄──────────► │ PC 总机房 Hub   │ ◄────────────► │ CLI 插件桥    │
│ ESP32-C3     │  USB CDC/WS  │ Python+asyncio │                │ （未实装）    │
│ LVGL 薄层     │              │ STT/纠错/注入   │                │ claude-code  │
└──────────────┘              └────────────────┘                └──────────────┘
      ▲ 显示状态/问答/来电              │ Android App（富终端，未实装）
      └────────────────────────────────┘
```

- **板子 = 哑终端**：只负责录音（16kHz / 16bit / mono PCM）、按键、显示，不在板上做 AI。
- **Hub = 中枢**：语音输入法（STT + 词表纠错 → 文字落到当前光标处）、Agent 状态转发、离线路由；Python + asyncio。
- **插件桥 = 各 CLI 的适配层**：把 Agent 事件转成协议消息（设计已定，代码未落地）。
- **协议 = JSON Schema 单一事实来源**：改消息只改 `protocol/schema/`，四端绑定由生成器输出。

## 仓库布局

| 路径 | 真实内容与状态 |
|---|---|
| [`firmware/`](firmware/) | ESP-IDF 工程外壳：`CMakeLists.txt`、`sdkconfig.defaults`（目标 esp32c3 / 8MB Flash / USB-Serial-JTAG 控制台 / LVGL 16bit）、`components/bsp/`（6 个头文件 + 6 个 `.c`：display / button / audio / battery / shared-I2C，引脚事实来源 `bsp_pins.h`）。**无 `main/`** |
| [`reference/folotoy-card-demo/`](reference/folotoy-card-demo/) | 上游 FoloToy-Card 基线 demo：`main/`（`main.c` + 4 个硬件验证页 + `demo.h` + 像素 UI 库）、`tests/test_ui_pixel_math.c`、`CMakeLists.txt`、`sdkconfig.defaults`。复用 `firmware/components/bsp`，只读参考；**当前唯一可构建的固件工程** |
| [`hub/`](hub/) | PC 总机房（Python 3.11+，asyncio）：入口 `hub-lite.py` 与 `python -m hub`（子命令 `serve` / `link` / `telemetry` / `sim`，其中 `link` 与 `sim` 目前是占位实现）；包体 `hub/hub/`（`audio` `cli` `config` `dictation` `server` `telemetry` + `gateway/` `core/` `operator/` `input/`）；`tests/` 7 文件 71 用例 |
| [`protocol/`](protocol/) | 协议 SSOT：`schema/` 9 条消息；`vectors/golden.json` 黄金向量；`c/` `rust/` `kotlin/` `python/` 四端生成绑定（生成器在 `tools/gen-protocol/`） |
| [`tools/`](tools/) | `gen-protocol/`（`generate.mjs` 四端生成 + `vectors.py` 黄金向量）、`stt-samples/`（SAPI 样本生成与评测脚本）、`stt-validate/`（Rust STT 评测工具）、`pdf-export/`（Node，导出文档集 PDF） |
| [`docs/`](docs/) | 设计文档 12 篇（11 篇 `BOSS_PHONE_*.md` + 上游保留的 `AI_HARDWARE_DEVELOPMENT_GUIDE.md`）+ [`docs/pdf/BOSS_PHONE_设计文档集.pdf`](docs/pdf/BOSS_PHONE_设计文档集.pdf) |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | CI 三 job（见下） |

## 快速开始

### Hub（Windows，Python 3.11+）

命令必须在 `hub/` 目录下执行——`hub` 是本地包，仓库根目录直接 `python -m hub` 会失败。

```bash
cd hub
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

python -m pytest tests -q        # 71 passed
python -m compileall -q hub tests
ruff check hub tests             # ruff 随 requirements-dev.txt 安装
ruff format --check hub tests
python -m hub telemetry          # 打印一次 CPU/内存遥测
python -m hub serve              # 纯 WS 模式常驻（未配置串口时），Ctrl+C 退出
```

语音链路与语音输入法（WAV → PCM → STT → 词表纠错 →（可选）光标注入）：

```bash
cd hub
python hub-lite.py ..\tools\stt-samples\out\01-daily.wav --engine windows   # 转写 + 纠错
python hub-lite.py --selftest                                             # 只自检注入能力，不发字
python hub-lite.py ..\tools\stt-samples\out\02-bio-bwa.wav --engine windows --type   # 纠错后文字打到光标处
```

`--engine` 可选 `windows`（零依赖，质量一般）/ `whisper`（需 `pip install "faster-whisper>=1.0"` 与模型文件）/ `cloud`（M0 为 stub）。`--no-correct` 用于度量词表纠错的收益。`tools/stt-samples/out/` 被 `.gitignore` 忽略，新克隆需要先用自己的终端跑 `powershell -ExecutionPolicy Bypass -File tools/stt-samples/gen-samples.ps1` 生成样本（SAPI TTS，需中文语音包）。`hub-lite.py` 与 `python -m hub` 入口都会把 stdout/stderr 切到 UTF-8，GBK 控制台下也不会因中文或 `✓` 报 `UnicodeEncodeError`。链路能跑通，但 `windows` 引擎在受限终端里可能返回空转写（SAPI 适配缓存写不进去，见「进行中」第一条）；此时换 `whisper` 引擎或在自己的终端跑。`--type` 需要先聚焦一个编辑窗口。

### 协议检查（仓库根目录）

```bash
node tools/gen-protocol/generate.mjs --check    # 四端产物与 schema 同步（消息 9 条 / 嵌套结构 2 个 / 枚举 4 个）
python tools/gen-protocol/vectors.py --check    # 黄金向量 wire_hex 与信封定义同步
cargo test -p boss-protocol                     # Rust 端信封往返 + 黄金向量语义校验
```

改消息的流程：改 `protocol/schema/` → 跑 `node tools/gen-protocol/generate.mjs` 重新生成 → 在 `tools/gen-protocol/vectors.py` 补向量 → 跑 `python tools/gen-protocol/vectors.py` → 四端产物与 `golden.json` 一起提交。

### 固件

`firmware/` 只有 BSP 组件、没有 `main/`，因此**不能单独构建出可烧录固件**；当前的可构建工程是上游参考 demo（同样复用 `firmware/components/bsp`）：

```bash
cd reference/folotoy-card-demo
idf.py set-target esp32c3
idf.py build
idf.py flash monitor
```

需要 ESP-IDF 5.5.x（已知环境 5.5.3）。`bsp_pins.h` 是硬件引脚事实来源，换板先改它。

像素 UI 的数学函数可脱离硬件做主机单测（不需要 ESP-IDF）：

```bash
cd reference/folotoy-card-demo
mkdir -p build
cc -I main tests/test_ui_pixel_math.c main/ui_pixel_math.c -o build/ui_pixel_math_test
./build/ui_pixel_math_test
```

## 协议与黄金向量

九条消息：`hello` / `hello_ack` / `presence` / `state` / `ask` / `answer` / `ring` / `ring_ack` / `hangup`。所有消息套同一信封 `type / from / to / seq / ts / payload`，与链路无关。

两种帧（`hub/hub/gateway/framing.py` 与 `protocol/vectors/` 一致）：

- 控制帧：UTF-8 紧凑 JSON + `\n`（`ensure_ascii=False`、分隔符 `,` `:`）；
- 媒体帧：`AA 55 | TYPE(1B) | FLAGS(1B) | LEN(2B 大端) | PAYLOAD`，TYPE `01` voice / `02` audio / `03` file-data / `04` file-meta。

`protocol/vectors/golden.json` 是四端共同字节基准：14 条控制帧、5 条媒体帧、1 条 CDC 混排流（`cdc-mixed`，控制帧与媒体帧交替）。Python 端做字节级比对（`hub/tests/test_protocol_vectors.py`），Rust 端做信封语义往返（`protocol/rust/tests/vectors.rs`）。

## 测试与 CI

| 套件 | 内容 | 命令 | 现状 |
|---|---|---|---|
| Hub（L1 单元） | 帧解析、词表纠错、语音输入编排 | `cd hub && python -m pytest tests -q` | 71 passed |
| Hub（L3 集成） | 起真实 WS 监听，虚拟设备跑 hello → hello_ack → state → 断连清理 | 同上（`hub/tests/test_integration_ws.py`） | 通过 |
| Hub（L2 向量） | 黄金向量字节级往返 + schema 校验 | 同上（`hub/tests/test_protocol_vectors.py`，48 用例） | 通过 |
| Hub（lint） | ruff check + ruff format --check（配置见 `hub/pyproject.toml`） | `cd hub && ruff check hub tests && ruff format --check hub tests` | 通过 |
| Rust 协议 | 信封与消息结构（6 单元）+ 黄金向量 roundtrip（3） | `cargo test -p boss-protocol` | 在 CI 执行 |
| 生成物同步 | 四端绑定与 schema / 向量一致 | 见「协议检查」两条命令 | 通过 |

CI（[`.github/workflows/ci.yml`](.github/workflows/ci.yml)，push 到 `main` 与 PR 触发）三个 job：

| job | 内容 |
|---|---|
| `protocol` | `node tools/gen-protocol/generate.mjs --check` + `python tools/gen-protocol/vectors.py --check` + `cargo test -p boss-protocol` |
| `hub` | 安装 `requirements.txt` + `requirements-dev.txt`，`python -m compileall -q hub tests`，`ruff check` + `ruff format --check`，`python -m pytest tests -q` |
| `firmware` | `espressif/esp-idf-ci-action@v1`（ESP-IDF v5.5、target esp32c3）编译 `reference/folotoy-card-demo` |

CI 不覆盖：真机验收（屏幕/按键/音频，需人工核对）、STT 准确率评测（只出报告不做门禁）、Windows 专属的 windows-native STT 与光标注入。

## 文档

| 文档 | 内容 |
|---|---|
| [PRD](docs/BOSS_PHONE_PRD.md) | 产品需求（唯一需求事实来源） |
| [DESIGN_OVERVIEW](docs/BOSS_PHONE_DESIGN_OVERVIEW.md) | 总体技术设计：仓库结构、技术栈、模块边界、代码骨架 |
| [DESIGN_PROTOCOL](docs/BOSS_PHONE_DESIGN_PROTOCOL.md) | 协议规范：消息字典、帧格式、seq/sync、错误码、时序图 |
| [DESIGN_FIRMWARE](docs/BOSS_PHONE_DESIGN_FIRMWARE.md) | 板端固件：分区表、任务与内存预算、boss_app / boss_transport |
| [DESIGN_HUB](docs/BOSS_PHONE_DESIGN_HUB.md) | PC 总机房：双入口网关、会话/路由、事件总线、离线队列、遥测 |
| [DESIGN_PLUGIN](docs/BOSS_PHONE_DESIGN_PLUGIN.md) | 插件桥：统一 AgentAdapter 与各 CLI 适配层 |
| [DESIGN_ANDROID](docs/BOSS_PHONE_DESIGN_ANDROID.md) | 安卓 App：BLE 网关、对等富终端、推送 |
| [DESIGN_DEPLOYMENT](docs/BOSS_PHONE_DESIGN_DEPLOYMENT.md) | 部署与运维：配网、配对、升级、故障排查 |
| [DESIGN_TEST](docs/BOSS_PHONE_DESIGN_TEST.md) | 测试与验收：M1–M4 验收清单、真机矩阵、CI 分层 |
| [DESIGN_SECURITY](docs/BOSS_PHONE_DESIGN_SECURITY.md) | 安全设计：威胁模型、鉴权、链路安全、隐私 |
| [GITHUB_STRATEGY](docs/BOSS_PHONE_GITHUB_STRATEGY.md) | GitHub / Git 组织与发布策略 |
| [AI_HARDWARE_DEVELOPMENT_GUIDE](docs/AI_HARDWARE_DEVELOPMENT_GUIDE.md) | 上游保留的硬件开发指南（板级事实、约束、验收） |

全部文档可导出为单份 PDF：[`docs/pdf/BOSS_PHONE_设计文档集.pdf`](docs/pdf/BOSS_PHONE_设计文档集.pdf)（导出脚本 `tools/pdf-export/export.mjs`）。

## 贡献与许可

- 环境要求、改动落点与验证清单见 [`CONTRIBUTING.md`](CONTRIBUTING.md)；仓库约定（目录职责、编码风格、提交流程）见 [`AGENTS.md`](AGENTS.md)，自动化的 Agent 也按该文件行事。
- 提交前至少跑通：`cd hub && python -m pytest tests -q`、`ruff check hub tests`、两条协议 `--check`；动固件的改动按 [DESIGN_TEST](docs/BOSS_PHONE_DESIGN_TEST.md) 在真机逐项验证并记录硬件结果。
- 协议只增不改：新增能力以「老对端可忽略」的方式加入 `protocol/schema/`，四端产物同步提交。
- 安全报告流程见 [`SECURITY.md`](SECURITY.md)，版本变更记录见 [`CHANGELOG.md`](CHANGELOG.md)。

MIT，见 [LICENSE](LICENSE)（版权行沿用上游 FoloToy）。
