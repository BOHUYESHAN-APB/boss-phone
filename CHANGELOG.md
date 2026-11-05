# Changelog（变更记录）

本文件记录 BOSS PHONE 的重要变更，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。
变更按 `新增 / 变更 / 修复 / 移除 / 安全` 分类，面向用户与集成方，不逐条罗列内部重构。

## [Unreleased]

### 新增

- **仓库结构重排**：固件收敛到 `firmware/`（ESP-IDF 根工程 + 共享硬件层 `components/bsp`）；
  上游 FoloToy-Card 基线 demo 收敛到 `reference/folotoy-card-demo/`（保留不删，复用共享 BSP）。
- **协议 SSOT 落地**：`protocol/schema/*.json` 为唯一事实来源，`tools/gen-protocol/` 生成
  C / Rust / Kotlin / Python 四端绑定（`protocol/c/boss_protocol.h`、`protocol/rust/src/messages.rs`、
  `protocol/kotlin/BossProtocol.kt`、`protocol/python/boss_protocol.py`）。
- **协议黄金向量**：新增 `protocol/vectors/golden.json`（人工审定的信封语义 + 工具计算的线上字节），
  四端以同一向量做字节级一致性校验；配套 Rust 端 `protocol/rust/tests/` roundtrip 测试。
- **Python hub 首次实现**：`hub/`（Python 3.11+ / asyncio）——gateway（CDC + 局域网 WS）、
  core（会话 / 路由 / 事件总线）、operator（STT / 词表纠错）、语音输入法（光标注入），
  并在无板环境下以 WAV 仿真跑通；配套 71 项 pytest（L1 单元 / L2 黄金向量 / L3 WS 集成）。
- **CI 三 job**：protocol（生成物 `--check` + 黄金向量 `--check` + Rust 语义校验）、
  hub（compileall + ruff lint/format + pytest）、firmware（ESP-IDF 5.5 编译 `reference/folotoy-card-demo`，ESP32-C3）。
- **设计文档集**：`docs/BOSS_PHONE_*.md` 分册（PRD / 总体设计 / 协议 / 固件 / Hub / 插件 / Android /
  部署 / 测试 / 安全）与导出的 `docs/pdf/BOSS_PHONE_设计文档集.pdf`。
- **仓库规范化基建**：`.gitattributes`（换行与二进制规则、生成物 linguist 标注）、`.editorconfig`、
  本 CHANGELOG、`CONTRIBUTING.md`、`SECURITY.md`、PR 模板、Issue 表单与 Dependabot 配置。

### 变更

- 固件默认目标固定为 **ESP32-C3**（8MB Flash，无 PSRAM），控制台改用 USB-Serial-JTAG
  （避免 UART0 TX 与背光引脚冲突），LVGL 颜色深度 16 位、内置内存池 24KB。
- hub 配置统一走 `hub.toml`（`tomllib`），缺省配置即以纯 WS 模式启动。
- `.gitignore` 收敛构建与评测产物（`build/`、`target/`、模型、录音样例输出、PDF 导出产物），
  **`Cargo.lock` 改为入库**（存在可执行产物 `tools/stt-validate`，需锁定依赖版本）。

### 修复

- 协议生成物与 schema 不同步的问题由 CI `--check` 永久拦截（禁止手改生成物）。
- hub 测试与语音输入法链路的路径/编码问题修正（WAV 输入读取、Windows 控制台输出）。

### 安全

- 明确凭据零入库策略：`hub.toml`（`ws.token` / `operator.api_key` / `relay.token`）已被 gitignore；
  设备凭据仅存 nvs；录音默认不留存（详见 `SECURITY.md` 与 `docs/BOSS_PHONE_DESIGN_SECURITY.md`）。

## [0.1.0] - 2026-08-31（待打 tag）

首个里程碑 **M0**：板子到货前完成 PC 侧全链路与协议冻结。

### 新增

- 协议 SSOT + 四端生成绑定，CI 校验生成物同步。
- hub：gateway / core / operator / 语音输入法，配套单元与集成测试。
- STT 评测工具链：`tools/stt-samples/`（WAV 样例与评测脚本）、`tools/stt-validate/`（Rust，
  whisper.cpp / windows-native / cloud-api 三种引擎适配，M0 以 WAV 仿真）。
- 固件共享硬件层 `firmware/components/bsp/`（display / button / audio / battery / I2C）。
- 上游基线 demo `reference/folotoy-card-demo/`（可构建、可烧录的真实硬件参考）。
- 文档集与 PDF 导出工具 `tools/pdf-export/`。

### 变更

- 仓库从上游 `FoloToy/ai-passport` fork 收敛为 BOSS PHONE 的 monorepo；删除历史中的 whisper 模型二进制（141MB）。

### 已知限制

- `firmware/main/`（`boss_app`：LVGL UI 薄层 + 业务层）尚未落地，固件侧当前只有 BSP 与参考 demo。
- Android App、BLE、云中继、OTA 为后续里程碑（M2–M4），尚未实现。

[Unreleased]: https://github.com/BOHUYESHAN-APB/boss-phone/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/BOHUYESHAN-APB/boss-phone/releases/tag/v0.1.0
