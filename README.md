# BOSS PHONE（领导电话）

> 远程指挥 AI Agent 的"领导手机" —— 基于 FoloToy AI Passport（ESP32-C3）的开放式硬件与软件体系。

BOSS PHONE 是给**非技术决策者**用的 AI 指挥终端：一块拇指大小的板子 + PC 总机房，把"领导"的语音指令变成对本地 AI Agent（claude-code / codex / opencode 等）的操作，并把执行状态、权限请求、关键结果实时回传到手上这块屏上。

```
┌────────────┐  语音/按键   ┌──────────────┐   本机/局域网   ┌────────────┐
│ 板子(哑终端)│ ◄──────────► │  PC 总机房 Hub │ ◄───────────► │ CLI 插件桥  │
│ ESP32-C3   │  USB CDC/WS  │  Python+asyncio│               │ (Agent)    │
│ LVGL 薄层  │              │  STT/意图/路由 │               │ claude-code│
└────────────┘              └──────────────┘               └────────────┘
      ▲ 显示状态/问答/来电            │ Android App（富终端，可选）
      └──────────────────────────────┘
```

- **板子** = 哑终端：只负责录音（16kHz PCM）、按键、显示状态，**不在板上做 AI**。
- **PC Hub** = 中枢：语音输入法（STT + 词表纠错 → 文字落到光标处）、意图路由、Agent 状态转发、离线队列。Python 生态，可集成本地大模型与用户自定义插件。
- **插件桥** = 让用户自写的 agent / 插件接入 Hub 的标准接口（Python ABC）。
- **协议** = JSON Schema 单一事实来源，自动生成 C/Rust/Kotlin/Python 四端绑定。

## 仓库布局

| 路径 | 内容 |
|---|---|
| [`firmware/`](firmware/) | BOSS PHONE 固件（ESP-IDF 工程）：`components/bsp/` 硬件层；`main/` 待 boss_app 落地 |
| [`reference/folotoy-card-demo/`](reference/folotoy-card-demo/) | 上游 FoloToy-Card 基线 demo（收敛保留，参考硬件逻辑怎么写） |
| [`hub/`](hub/) | PC 总机房（Python + asyncio）：gateway / core / operator / 语音输入法 |
| [`protocol/`](protocol/) | 通讯协议 SSOT + 四端生成绑定 |
| [`tools/`](tools/) | 协议生成器 / STT 评测 / PDF 导出 |
| [`docs/`](docs/) | BOSS PHONE 设计文档（`BOSS_PHONE_*.md`）+ 保留的上游硬件指南 |

## 快速开始

固件（ESP-IDF 5.5.x）：

```bash
cd firmware
get_idf553 && idf.py set-target esp32c3 && idf.py build
```

PC Hub（Python 3.11+）：

```bash
cd hub
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python hub-lite.py ../tools/stt-samples/out/01-daily.wav --engine windows --type   # 语音输入法验证
```

## 文档

- 产品需求：[`docs/BOSS_PHONE_PRD.md`](docs/BOSS_PHONE_PRD.md)
- 总体设计：[`docs/BOSS_PHONE_DESIGN_OVERVIEW.md`](docs/BOSS_PHONE_DESIGN_OVERVIEW.md)（含协议/固件/Hub/插件/部署/测试/安全等分册）
- Agent 仓库约定：见 [`AGENTS.md`](AGENTS.md)

## 许可

MIT —— 见 [LICENSE](LICENSE)。

