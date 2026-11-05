# Repository Guidelines

## Project Structure & Module Organization

BOSS PHONE（领导电话）monorepo：ESP32-C3 哑终端 + PC 总机房（Python hub）+ 协议 SSOT + 插件桥。

- `firmware/`: ESP-IDF 固件工程。`firmware/components/bsp/` 为共享硬件层：public BSP APIs 与硬件引脚/配置事实来源（`bsp_pins.h`），src 为 display/button/audio/battery/shared-I2C 实现。**`firmware/main/` 尚不存在**——BOSS PHONE 固件入口（LVGL UI 薄层 + boss_app）未落地，本工程当前不产出可烧录固件，也没有 `app_main`。
- `reference/folotoy-card-demo/`: 上游 FoloToy-Card 基线 demo（原根 `main/`），**收敛保留不删**，是"关键硬件逻辑怎么写"的参考实现，不在其上迭代。demo 页实现 `enter`/`exit`/`key` 接口（`demo.h`）；它是**当前唯一可构建的固件工程**。主机单测见 `tests/test_ui_pixel_math.c`。
- `hub/`: PC 端总机房（Python 3.11+，asyncio）：gateway（CDC/WS + 分帧 + 握手）+ core（会话/路由/事件总线）+ operator（STT/词表纠错）+ 语音输入法（光标注入）。入口 `hub-lite.py` 与 `python -m hub serve|link|telemetry|sim`。测试在 `hub/tests/`（7 文件 71 用例）。见 DESIGN_HUB。
- `protocol/`: 通讯协议 SSOT。`schema/` 9 条消息（hello/hello_ack/presence/state/ask/answer/ring/ring_ack/hangup）+ `vectors/golden.json` 黄金向量（14 控制帧 + 5 媒体帧 + 1 混排流）+ C/Rust/Kotlin/Python 四端生成绑定。生成器在 `tools/gen-protocol/`，**生成物禁止手改**。
- `tools/`: `gen-protocol`（`generate.mjs` 四端生成 + `vectors.py` 黄金向量）、`stt-samples/stt-validate`（STT 评测）、`pdf-export`（Node，导出 `docs/pdf/` 文档集）。
- `docs/`: BOSS PHONE 设计文档（`BOSS_PHONE_*.md` 11 篇）+ `AI_HARDWARE_DEVELOPMENT_GUIDE.md`（保留的上游硬件开发指南）。
- `firmware/sdkconfig.defaults`: 固件可复现目标/控制台/LVGL/内存默认值（esp32c3、8MB Flash、USB-Serial-JTAG 控制台、LVGL 16bit、LVGL 池 24KB）。
- 尚未创建：`plugins/`（CLI 插件桥）、`android/`（安卓 App）。设计见 DESIGN_PLUGIN / DESIGN_ANDROID。
- 仓库基建：`.github/`（CI 工作流、PR 模板、Issue 表单、Dependabot）、`CONTRIBUTING.md`（环境与 PR 清单）、`SECURITY.md`（漏洞报告）、`CHANGELOG.md`（变更记录）、`.gitattributes`（文本 LF / Windows 脚本 CRLF）、`.editorconfig`、根 `Cargo.toml` workspace（members = `tools/stt-validate`、`protocol/rust`）。

Keep reusable hardware logic in `firmware/components/bsp`; keep BOSS PHONE firmware behavior in `firmware/main`（尚未创建）。上游演示代码只读，改动一律进 `firmware/` 产品路径。

## Build, Test, and Development Commands

### 固件（ESP-IDF 5.5.x）

`firmware/` 没有 `main/`，`idf.py build` 目前无法产出固件。当前可构建的是上游参考 demo（复用共享 BSP）：

```bash
cd reference/folotoy-card-demo
idf.py set-target esp32c3     # 新 checkout / 换目标时执行一次
idf.py build                  # 编译固件，验证 BSP 与依赖
idf.py flash monitor          # 烧录并看日志（需要板子）
idf.py fullclean              # 配置陈旧时清理
```

`get_idf553` 只是可选的 shell 快捷函数（等价于 `source <idf>/export.sh`），**不是仓库文件**，不能假设存在；没有就按 `docs/AI_HARDWARE_DEVELOPMENT_GUIDE.md` §12 激活 ESP-IDF。

像素 UI 数学的主机单测（不需要 ESP-IDF）：

```bash
cd reference/folotoy-card-demo
mkdir -p build
cc -I main tests/test_ui_pixel_math.c main/ui_pixel_math.c -o build/ui_pixel_math_test
./build/ui_pixel_math_test
```

### Hub（Python 3.11+）

命令在 `hub/` 目录下执行（`hub` 是本地包，仓库根目录直接 `python -m hub` 会失败）：

```bash
cd hub
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

python -m pytest tests -q     # 71 passed；L1 单元 + L2 黄金向量 + L3 WS 集成
python -m compileall -q hub tests
ruff check hub tests          # ruff 随 requirements-dev.txt 安装
ruff format --check hub tests
python -m hub telemetry       # 遥测快照
python -m hub serve           # 常驻进程（未配置串口时纯 WS 模式）
python hub-lite.py ..\tools\stt-samples\out\01-daily.wav --engine windows   # WAV → STT → 纠错
python hub-lite.py --selftest                                              # 只自检光标注入能力，不发字
```

`windows` 引擎与光标注入仅 Windows 可用；`whisper` 需 `pip install "faster-whisper>=1.0"` 与模型文件；`cloud` 目前是 stub。

> 无板时 `python -m hub serve` 以纯 WS 模式起在 `0.0.0.0:8765`（默认 `ws.token = "change-me"`，本地 `hub.toml` 覆盖，`hub.toml` 已 gitignore）。`python -m hub link|sim` 目前是占位实现，别当成已实装能力引用。

### 协议 SSOT（仓库根目录）

```bash
node tools/gen-protocol/generate.mjs --check    # 四端产物与 schema 同步
python tools/gen-protocol/vectors.py --check    # 黄金向量 wire_hex 与信封同步
cargo test -p boss-protocol                     # Rust 信封往返 + 黄金向量语义校验
```

改消息的流程：改 `protocol/schema/` → `node tools/gen-protocol/generate.mjs` 重新生成 → 在 `tools/gen-protocol/vectors.py` 补向量 → `python tools/gen-protocol/vectors.py` 重算 → 四端产物与 `golden.json` 一并提交。

### CI（`.github/workflows/ci.yml`，push 到 `main` 与 PR 触发）

| job | 命令 |
|---|---|
| `protocol` | `node tools/gen-protocol/generate.mjs --check` + `python tools/gen-protocol/vectors.py --check` + `cargo test -p boss-protocol` |
| `hub` | `python -m compileall -q hub tests` + `ruff check hub tests` + `ruff format --check hub tests` + `python -m pytest tests -q`（`working-directory: hub`） |
| `firmware` | `espressif/esp-idf-ci-action@v1`，ESP-IDF v5.5 / target esp32c3，构建 `reference/folotoy-card-demo` |

## Coding Style & Naming Conventions

Write C using four-space indentation and K&R-style braces, following nearby files. Use `snake_case` for functions and locals, `BSP_*` for public hardware constants, and `s_` for file-local state. Keep BSP APIs prefixed with `bsp_`; name demo entry points `demo_<feature>_<action>`. Prefer `static` for internal symbols. UI text stays English; explanatory comments may be Chinese. Preserve comments documenting hardware-specific register values and memory constraints.

Python：4 空格缩进，模块/函数 `snake_case`，类型注解与 `from __future__ import annotations` 保持与 `hub/hub/` 现有文件一致；协议绑定（`protocol/python/boss_protocol.py`）由生成器输出，不要手改。生成器（`tools/gen-protocol/generate.mjs`、`tools/pdf-export/export.mjs`）是 Node ESM 脚本。

## Testing Guidelines

- 提交前至少跑通 `cd hub && python -m pytest tests -q` 与上面两条 `--check`；新增协议消息必须同时补 Schema、四端生成物与黄金向量。
- 固件改动：先确认 `idf.py build` 零新增 warning；真机验证菜单导航与受影响的 Display、Button、Audio 或 Battery 页。pin、显示旋转、codec 时钟、ADC、DMA 改动必须在 PR 记录实测结果。
- 不要在没核对 ESP32-C3 内部 RAM 占用的情况下加大 LVGL 缓冲或音频分配；板子**没有 PSRAM**。
- 真机验收清单与测试矩阵见 `docs/BOSS_PHONE_DESIGN_TEST.md`；CI 不覆盖真机验收与 STT 准确率评测（后者只出报告，不做门禁）。

## Commit & Pull Request Guidelines

History follows Conventional Commit-style subjects such as `feat(bsp): ...`, `feat(hub): ...`, `feat(protocol): ...`, `fix(bsp): ...`, and `docs: ...`. Keep commits focused by subsystem. Pull requests should explain the hardware/revision tested, summarize behavior changes, list build and on-device results, and include photos or screenshots for display changes. Link related issues and call out wiring, pin-map, or compatibility impacts.

构建 / 评测产物不要入库：`build/`、`sdkconfig`、`managed_components/`、`hub/.venv/`、`__pycache__/`、`.pytest_cache/`、`.ruff_cache/`、`tools/stt-samples/out/`、`tools/pdf-export/_out/`、`node_modules/`、`hub.toml` 已在 `.gitignore` 内；`docs/pdf/*.pdf`、`Cargo.lock`、`reference/folotoy-card-demo/dependencies.lock` **是要入库的**（后两者是依赖锁，删掉会让 CI 在依赖求解阶段解析到新版本并失败）。
