# Repository Guidelines

## Project Structure & Module Organization

BOSS PHONE（领导电话）monorepo：ESP32-C3 哑终端 + PC 总机房（Python hub）+ 协议 SSOT + 插件桥。

- `firmware/`: ESP-IDF 固件工程。`firmware/components/bsp/` 为共享硬件层：public BSP APIs 与硬件引脚/配置事实来源（`bsp_pins.h`），src 为 display/button/audio/battery/shared-I2C 实现。BOSS PHONE 固件入口（`firmware/main/` = LVGL UI 薄层 + boss_app）待 DESIGN_FIRMWARE 落地后创建。
- `reference/folotoy-card-demo/`: 上游 FoloToy-Card 基线 demo（原根 `main/`），**收敛保留不删**，是"关键硬件逻辑怎么写"的参考实现，不在其上迭代。demo 页实现 `enter`/`exit`/`key` 接口（`demo.h`）。
- `hub/`: PC 端总机房（Python + asyncio）：gateway（CDC/WS）+ core（会话/路由/事件总线）+ operator（STT/词表纠错）+ 语音输入法（光标注入）。见 DESIGN_HUB。
- `protocol/`: 通讯协议 SSOT（JSON Schema）+ C/Rust/Kotlin/Python 四端生成绑定。生成器在 `tools/gen-protocol/`。
- `tools/`: 协议生成器、STT 评测（stt-samples/stt-validate）、PDF 导出。
- `docs/`: BOSS PHONE 设计文档（`BOSS_PHONE_*.md`）；`AI_HARDWARE_DEVELOPMENT_GUIDE.md` 为保留的上游硬件开发指南。
- `firmware/sdkconfig.defaults`: 固件可复现目标/控制台/LVGL/内存默认值。

Keep reusable hardware logic in `firmware/components/bsp`; keep BOSS PHONE firmware behavior in `firmware/main`（未来）。上游演示代码只读，改动一律进 `firmware/` 产品路径。

## Build, Test, and Development Commands

固件用 ESP-IDF 5.5.x（从 `firmware/` 运行）：

```bash
cd firmware
get_idf553                    # Enter the repository's ESP-IDF 5.5.3 environment
idf.py set-target esp32c3     # Configure a fresh checkout
idf.py build                  # Compile firmware and validate dependencies
idf.py flash monitor          # Flash the connected board and open logs
idf.py fullclean              # Remove generated build state when configuration is stale
```

上游参考 demo（可选，`reference/folotoy-card-demo/`，复用共享 BSP）：

```bash
cd reference/folotoy-card-demo
get_idf553; idf.py set-target esp32c3; idf.py build
```

PC 端 hub（Python 3.11+）：

```bash
cd hub && python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python hub-lite.py tools/stt-samples/out/01-daily.wav --engine windows --type   # 语音输入法验证
```

There is no host-side automated test suite currently. Treat a clean `idf.py build` as the minimum firmware check, then run every applicable item in the README acceptance checklist on real hardware.

## Coding Style & Naming Conventions

Write C using four-space indentation and K&R-style braces, following nearby files. Use `snake_case` for functions and locals, `BSP_*` for public hardware constants, and `s_` for file-local state. Keep BSP APIs prefixed with `bsp_`; name demo entry points `demo_<feature>_<action>`. Prefer `static` for internal symbols. UI text stays English; explanatory comments may be Chinese. Preserve comments documenting hardware-specific register values and memory constraints.

## Testing Guidelines

Before submitting, build from the repository root and inspect warnings. On hardware, verify menu navigation and the affected Display, Button, Audio, or Battery page. For pin, display-rotation, codec-clock, ADC, or DMA changes, explicitly record the observed hardware result in the PR. Do not increase LVGL buffers or audio allocations without checking ESP32-C3 internal RAM usage; the board has no PSRAM.

## Commit & Pull Request Guidelines

History follows Conventional Commit-style subjects such as `feat(bsp): ...`, `feat(demo): ...`, `fix(bsp): ...`, and `docs: ...`. Keep commits focused by subsystem. Pull requests should explain the hardware/revision tested, summarize behavior changes, list build and on-device results, and include photos or screenshots for display changes. Link related issues and call out wiring, pin-map, or compatibility impacts.
