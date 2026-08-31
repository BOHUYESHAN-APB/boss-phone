# BOSS PHONE 总体技术设计

| 项目 | 内容 |
|---|---|
| 状态 | Draft v0.1（对应 PRD v0.4） |
| 上游文档 | [BOSS_PHONE_PRD.md](BOSS_PHONE_PRD.md) |
| 日期 | 2026-08-24 |

本文档定义整个系统的工程结构：仓库布局、技术栈、模块边界、各 CLI 插件的兼容策略与关键代码骨架。细节设计下沉到各专项文档（见第 1 节）。**当前无实机，所有代码均为设计骨架，进入 M1 后再落地。**

> **硬件时间线（2026-08-29 更新）**：预售板子预计 **2026-09-13 发货**，9 月中旬到手。到货前为"无实机窗口期"——先完成协议 SSOT、Hub/STT 全部 PC 侧开发与 WAV 仿真评测（**M0**，见第 8 节），板子到货后把"WAV 文件输入"换成"串口 PCM 输入"即进入真机联调。

> **固件语言定稿（2026-08-29）**：混合策略——C 保留 BSP 与 LVGL UI 薄层，**业务层（协议/传输/状态机/音频管道）用 Rust（esp-idf-hal，std 环境）**，详见 4.3 节。

---

## 1. 设计文档体系

| 文档 | 范围 | 状态 |
|---|---|---|
| [BOSS_PHONE_PRD.md](BOSS_PHONE_PRD.md) | 产品需求（唯一需求事实来源） | v0.4 |
| 本文 DESIGN_OVERVIEW | 工程结构 / 技术栈 / 模块边界 / 代码骨架 | v0.1 |
| [DESIGN_PROTOCOL](BOSS_PHONE_DESIGN_PROTOCOL.md) | 协议规范：消息字典全量字段、帧格式（JSON 控制帧 + 二进制媒体帧）、seq/sync、错误码、时序图 | v0.1 |
| [DESIGN_FIRMWARE](BOSS_PHONE_DESIGN_FIRMWARE.md) | 板端固件：Flash 分区表、任务/内存预算、boss_transport / boss_protocol / boss_app（LVGL 应用框架）设计 | v0.1 |
| [DESIGN_HUB](BOSS_PHONE_DESIGN_HUB.md) | PC 总机房：CDC+WS 双入口网关、会话/路由、事件总线、离线队列、遥测聚合 | v0.1 |
| [DESIGN_PLUGIN](BOSS_PHONE_DESIGN_PLUGIN.md) | 插件桥：统一 AgentAdapter 协议 + 各 CLI（Claude Code / Codex / OpenCode / Trae）适配层实现 | v0.1 |
| [DESIGN_ANDROID](BOSS_PHONE_DESIGN_ANDROID.md) | 安卓 App：BLE 网关、对等富终端 UI、推送接入、web coding 对话界面 | v0.1 |
| [DESIGN_DEPLOYMENT](BOSS_PHONE_DESIGN_DEPLOYMENT.md) | 部署与运维：Hub/插件/配网/配对/升级/故障排查 | v0.1 |
| [DESIGN_TEST](BOSS_PHONE_DESIGN_TEST.md) | 测试与验收：M1-M4 验收清单、真机测试矩阵、CI 双轨、回归 | v0.1 |
| [DESIGN_SECURITY](BOSS_PHONE_DESIGN_SECURITY.md) | 安全设计：威胁模型、鉴权、链路安全、隐私、最小权限 | v0.1 |

写作顺序建议：PROTOCOL → HUB → PLUGIN → FIRMWARE → ANDROID（协议是全部下游的契约，先冻结），随后 DEPLOYMENT → TEST → SECURITY 收口。文档集可一键导出为汇总 PDF（`tools/pdf-export`）。

---

## 2. 设计原则（工程视角）

1. **协议单一事实来源（SSOT）**：`protocol/` 目录下定义一次，生成 C / Rust / Kotlin / Python 四端代码。禁止任何端手写消息结构。
2. **模块只依赖协议，不依赖彼此**：板子固件、Hub、插件、App 四个模块间**只通过协议交互**，仓库内可独立构建、独立演进。
3. **能力协商代替版本分支**：hello + caps（PRD 3.3），任何端的新能力都要以"老对端可忽略"的方式加入。
4. **哑终端纪律**：固件不做任何语义理解（不含 STT/意图/摘要），显示的一切文字都由 Hub 下发。违反这条 = 固件开始变笨重。
5. **现有 BSP 零破坏**：`firmware/components/bsp` 与 `reference/folotoy-card-demo/`（上游 demo）保持不动（AGENTS.md 契约），Boss Phone 作为新增组件与新增入口并存。

---

## 3. Monorepo 仓库结构

当前仓库为 monorepo：固件是 `firmware/` 子工程（ESP-IDF 根项目），其余子项目（hub / protocol / tools / plugins）为独立构建单元；上游 FoloToy-Card 基线 demo 已收敛到 `reference/folotoy-card-demo/`（保留不删，见 §BOSS_PHONE_GITHUB_STRATEGY）：

```svg
<svg viewBox="0 0 900 900" xmlns="http://www.w3.org/2000/svg" font-family="ui-sans-serif,system-ui,Microsoft YaHei,sans-serif" font-size="11">
  <style>
    .mdir { font-size: 13px; font-weight: 700; fill: #3a2a7a; }
    .mnote { fill: #8a8aa8; }
    .mchild { fill: #4a4a68; }
    .mleaf { fill: #5b5b78; }
  </style>

  <!-- 主干 -->
  <rect x="20" y="345" width="150" height="44" rx="10" fill="#e7e0fb" stroke="#7c5cfc" stroke-width="1.5"/>
  <text x="95" y="372" text-anchor="middle" font-size="14" font-weight="700" fill="#3a2a7a">boss-phone/</text>
  <line x1="170" y1="367" x2="210" y2="367" stroke="#7c5cfc" stroke-width="1.5"/>
  <line x1="210" y1="30" x2="210" y2="870" stroke="#7c5cfc" stroke-width="1.5"/>

  <!-- firmware/ -->
  <rect x="235" y="20" width="545" height="150" rx="10" fill="#f4f4fa" stroke="#c9c9df"/>
  <text x="250" y="44" class="mdir">firmware/</text><text x="320" y="44" class="mnote">— ESP-IDF 固件工程（构建入口在此）</text>
  <text x="260" y="66" class="mchild">components/bsp/</text><text x="375" y="66" class="mleaf">现有硬件 BSP，不动（reference demo 复用）</text>
  <text x="260" y="84" class="mchild">components/boss_transport/</text><text x="420" y="84" class="mleaf">（未来）传输抽象 + usb/ws/ble + 链路监管器</text>
  <text x="260" y="102" class="mchild">components/boss_protocol/</text><text x="420" y="102" class="mleaf">（未来）协议编解码，生成产物在此</text>
  <text x="260" y="120" class="mchild">components/boss_app/</text><text x="380" y="120" class="mleaf">（未来）LVGL 手机系统框架：状态栏/桌面/导航</text>
  <text x="260" y="138" class="mchild">main/</text><text x="300" y="138" class="mleaf">（未来）BOSS PHONE UI 薄层；当前为空</text>
  <text x="260" y="156" class="mchild">sdkconfig.defaults</text><text x="390" y="156" class="mleaf">目标/控制台/LVGL/内存默认值</text>
  <line x1="210" y1="95" x2="235" y2="95" stroke="#7c5cfc" stroke-width="1.5"/>

  <!-- reference/ -->
  <rect x="235" y="185" width="545" height="52" rx="10" fill="#f4f4fa" stroke="#c9c9df"/>
  <text x="250" y="209" class="mdir">reference/folotoy-card-demo/</text><text x="430" y="209" class="mnote">上游基线 demo（收敛保留，原根 main/）</text>
  <text x="260" y="229" class="mleaf">LVGL 菜单 + Display/Button/Audio/Battery 验证页（参考硬件逻辑怎么写）</text>
  <line x1="210" y1="211" x2="235" y2="211" stroke="#7c5cfc" stroke-width="1.5"/>

  <!-- protocol/ -->
  <rect x="235" y="255" width="545" height="82" rx="10" fill="#f4f4fa" stroke="#c9c9df"/>
  <text x="250" y="279" class="mdir">protocol/</text><text x="320" y="279" class="mnote">★ 协议 SSOT（非 ESP-IDF 目录）</text>
  <text x="260" y="301" class="mchild">schema/</text><text x="310" y="301" class="mleaf">每条消息一个 JSON Schema（hello.json / state.json / ...）</text>
  <text x="260" y="319" class="mchild">rust|c|kotlin|python/</text><text x="385" y="319" class="mleaf">四端生成绑定（生成器 tools/gen-protocol 输出，提交入库）</text>
  <line x1="210" y1="296" x2="235" y2="296" stroke="#7c5cfc" stroke-width="1.5"/>

  <!-- hub/ -->
  <rect x="235" y="355" width="545" height="150" rx="10" fill="#f4f4fa" stroke="#c9c9df"/>
  <text x="250" y="379" class="mdir">hub/</text><text x="295" y="379" class="mnote">PC 总机房（Python + asyncio）</text>
  <text x="260" y="401" class="mchild">gateway/</text><text x="335" y="401" class="mleaf">CDC 串口入口 + WebSocket 入口（帧编解码/握手）</text>
  <text x="260" y="419" class="mchild">core/</text><text x="315" y="419" class="mleaf">会话管理 / 路由决策 / 事件总线 / 离线队列</text>
  <text x="260" y="437" class="mchild">operator/</text><text x="340" y="437" class="mleaf">STT 引擎（windows/whisper/cloud）+ 词表纠错层</text>
  <text x="260" y="455" class="mchild">input/ + dictation.py</text><text x="385" y="455" class="mleaf">语音输入法：文字落到光标处（SendInput/剪贴板）</text>
  <text x="260" y="473" class="mchild">telemetry.py</text><text x="340" y="473" class="mleaf">PC 资源采集 / token 聚合 / commit+CI 查询</text>
  <text x="260" y="491" class="mchild">hub-lite.py</text><text x="330" y="491" class="mleaf">语音链路验证 + 语音输入法入口（--type/--selftest）</text>
  <line x1="210" y1="430" x2="235" y2="430" stroke="#7c5cfc" stroke-width="1.5"/>

  <!-- plugins/ -->
  <rect x="235" y="520" width="545" height="82" rx="10" fill="#f4f4fa" stroke="#c9c9df"/>
  <text x="250" y="544" class="mdir">plugins/</text><text x="315" y="544" class="mnote">CLI 插件桥（未来，Python 包，与 Hub 同语言）</text>
  <text x="260" y="566" class="mchild">core/</text><text x="290" y="566" class="mleaf">★ 统一 AgentHandle 接口 + 协议绑定（各插件共用）</text>
  <text x="260" y="584" class="mchild">claude-code|codex|opencode|trae/</text><text x="425" y="584" class="mleaf">各 CLI 适配器（M1 打样 claude-code）</text>
  <line x1="210" y1="561" x2="235" y2="561" stroke="#7c5cfc" stroke-width="1.5"/>

  <!-- tools/ -->
  <rect x="235" y="617" width="545" height="52" rx="10" fill="#f4f4fa" stroke="#c9c9df"/>
  <text x="250" y="641" class="mdir">tools/</text><text x="290" y="641" class="mnote">开发期工具</text>
  <text x="260" y="661" class="mleaf">gen-protocol/（四端生成器）· stt-samples/ + stt-validate/（STT 评测）· pdf-export/（文档集导出）</text>
  <line x1="210" y1="643" x2="235" y2="643" stroke="#7c5cfc" stroke-width="1.5"/>

  <!-- docs/ -->
  <rect x="235" y="684" width="545" height="52" rx="10" fill="#f4f4fa" stroke="#c9c9df"/>
  <text x="250" y="708" class="mdir">docs/</text><text x="290" y="708" class="mnote">设计文档 + 硬件指南</text>
  <text x="260" y="728" class="mleaf">BOSS_PHONE_*.md（PRD/设计/协议/固件/Hub/插件/部署/测试/安全）+ AI_HARDWARE_DEVELOPMENT_GUIDE.md（保留）+ pdf/</text>
  <line x1="210" y1="710" x2="235" y2="710" stroke="#7c5cfc" stroke-width="1.5"/>

  <!-- android/ -->
  <rect x="235" y="751" width="545" height="52" rx="10" fill="#f4f4fa" stroke="#c9c9df"/>
  <text x="250" y="775" class="mdir">android/</text><text x="315" y="775" class="mnote">（未来）安卓 App：Kotlin + Compose + BLE 网关 + 推送</text>
  <text x="260" y="795" class="mleaf">对等富终端（可选项，非 M1 范围）</text>
  <line x1="210" y1="777" x2="235" y2="777" stroke="#7c5cfc" stroke-width="1.5"/>
</svg>
```

**与 ESP-IDF 构建的兼容**：`protocol/`、`hub/`、`tools/`、`docs/`、`reference/` 不是固件工程的组成部分；ESP-IDF 构建入口在 `firmware/`（`idf.py` 从该目录运行，`sdkconfig.defaults` 亦在 `firmware/`）。固件业务层（Rust 组件，未来）依赖 `protocol/rust` crate，UI 薄层 include `protocol/c/boss_protocol.h`。`firmware/CMakeLists.txt` 只需照常列 components。

**Cargo workspace（仅固件侧 Rust）**：固件业务层组件（`firmware/components/boss_protocol` 等，未来）共用 `protocol/rust` crate；`hub/` 与 `plugins/*` 是 Python 包（`hub/` 下 `pyproject.toml` + `python -m hub` 入口），不经 cargo 构建。`tools/gen-protocol` 是独立 Node 脚本（开发期工具），负责输出 C/Rust/Kotlin/Python 四端绑定。

---

## 4. 技术栈选型

| 端 | 选型 | 理由 |
|---|---|---|
| 板子固件 | C（BSP + LVGL UI 薄层）+ Rust（esp-idf-hal，std 环境）+ TinyUSB（双 CDC） | BSP/demo 零破坏（AGENTS.md 契约）；业务层（协议/传输/状态机/音频管道）Rust 编译期内存安全；WiFi/BLE 走 esp-idf-svc（IDF 成熟 C 栈封装） |
| Hub | Python（asyncio） | 中枢中转 + 接线员：STT/LLM/意图/备忘的 AI 逻辑 Python 生态最强（faster-whisper、openai/anthropic SDK、pydantic）；原定计划即 Python；`pyserial` + `websockets` 够用 |
| 插件桥 | Python（与 Hub 同语言） | CLI 适配器是纯逻辑（hook 事件 → 本地 WS 上报），无性能压力；与 Hub 同语言零成本共享协议绑定 |
| 安卓 App | Kotlin + Jetpack Compose + 原生 BLE + kotlinx-serialization | 现代安卓标准；BLE 网关用平台 API 避免第三方依赖黑盒 |
| 协议 SSOT | JSON Schema + 自研生成器（Node.js 脚本） | 生成器是开发期工具，Node 最顺；只负责输出 C/Rust/Kotlin/Python 四端结构声明，与运行时性能无关 |

> **固件语言不变**：板子固件仍是 C（BSP + LVGL UI 薄层）+ Rust（业务层），内存安全需求在板上，PC 侧无此痛点（Python 本身内存安全）。

### 4.1 运行时内存特性

| 端 | 语言 | 运行时内存模型 |
|---|---|---|
| Hub | Python | 常驻 asyncio 单进程；典型 RSS ~60-80MB；whisper 模型按需加载（base 147MB 进程外，faster-whisper 可量化） |
| 插件桥 | Python | 常驻轻量适配器进程，几 MB 起步 |
| 生成器（开发期） | Node.js | 一次性工具，短暂运行即退出，不计入常驻 |
| （替代对比）Hub 用 Rust | Rust | 更省内存（<30MB），但接线员 AI 逻辑开发成本高——取舍：PC 内存不紧，Python 开发效率优先 |

**原则（2026-08-30 定稿）**：板子固件业务层用 **Rust**（内存安全）；PC 侧 Hub/插件桥/接线员用 **Python**（AI 逻辑优先，原定计划）；协议 SSOT 语言无关，生成器用 Node，产物 Rust/Kotlin/C/Python 四端。

### 4.2 各 CLI 生态机制盘点

- **OpenAI Codex 本体就是 Rust**（`openai/codex`）——其 `exec --json` 事件流、notify 进程外协议，Python 适配器直接解析其 JSON 事件即可。
- Claude Code hooks 是"外部命令 + stdin/stdout JSON"，与语言无关，Python 子进程天然胜任。
- OpenCode（sst/opencode，TypeScript/Node 实现）的 plugin API 是 TS 事件总线；Python 侧用其 JSON 事件协议对接即可，能力挂起机制（permission 事件）由适配器实现。

### 4.3 固件语言策略：混合 C + Rust（2026-08-29 定稿）

| 层 | 语言 | 内容 | 理由 |
|---|---|---|---|
| 硬件驱动层 | C | `firmware/components/bsp`（显示/按键/音频/电池），已实机验证 | 零破坏零重写（AGENTS.md 契约） |
| UI 薄层 | C | `boss_app` 的 LVGL 声明式布局 | 声明式布局不是内存 bug 重灾区；lvgl-rs 绑定尚繁琐，不值得 |
| 业务层 | Rust | `boss_protocol` / `boss_transport` / 链路状态机 / 音频管道 / 队列 | 解析外部输入的重灾区：编译期消灭越界/UAF/数据竞争 |

- **接入方式**：`esp-idf-sys` 生成 `bsp_*` C API 的 Rust 绑定；Rust 组件编出 `.a` 由 ESP-IDF 链接进固件；WiFi/BLE/USB 用 `esp-idf-svc`（IDF C 栈的安全封装）。
- **为什么是 std 而不是 no_std esp-hal**：复用 IDF 成熟网络栈；BSP 直接链接；`serde_json`/`std` 生态可用。彻底 no_std（esp-hal + esp-wifi）留作远期可选。
- **诚实边界**：Rust 消灭的是内存**安全 bug**，不是内存**预算工作**——400KB SRAM 的静态分配与栈规划照做（`heapless` / 静态缓冲优先，谨慎 `alloc`）。

---

## 5. CLI 插件兼容矩阵（核心工程风险）

各 CLI 的扩展机制差异很大，统一策略是：**adapter-core 定义能力接口，各 CLI 适配器声明自己支持的能力子集，Hub 按能力降级。**

### 5.1 各 CLI 机制盘点

| 能力 | Claude Code | Codex CLI | OpenCode | Trae |
|---|---|---|---|---|
| 扩展机制 | hooks（`settings.json`，stdin 收 JSON 事件） | `config.toml` 的 `notify`（外部命令，JSON 事件）+ `exec --json` 事件流 | plugin API（`@opencode-ai/plugin`，TS 事件总线） | 待调研 |
| 状态上报 | Stop / PostToolUse / Notification 事件 | agent-turn-complete / token-count 事件 | chat.message / tool.execute.* 事件 | 待调研 |
| **权限拦截（挂起等待回答）** | **强**：PreToolUse hook 返回 `permissionDecision: allow/deny/ask`，进程挂起等待 | 弱：approval_policy 只能预设（untrusted/on-request/...），notify 只通知不挂起 | **强**：permission 事件可异步等待外部决定 | 待调研 |
| 主动提问 | Notification hook | notify 事件 | event 总线 | 待调研 |
| token usage | hook 事件内含 usage / transcript 可解析 | token-count 事件 | 消息级 usage | 待调研 |
| commit 事件 | PostToolUse(Bash/git) 解析或 Stop 后查 git | 同左 | 同左 | 同左 |

### 5.2 统一适配接口（adapter-core 设计核心）

```typescript
// plugins/adapter-core/src/index.ts —— 设计骨架
export interface AgentAdapter {
  readonly cli: 'claude-code' | 'codex' | 'opencode' | 'trae';
  readonly agentId: string;            // 仓库名，即电话簿联系人名
  /** 能力声明：Hub 据此降级（如 codex 无挂起拦截 → 权限改为"预批+事后通知"） */
  readonly caps: AdapterCaps;
  start(hub: HubClient): Promise<void>;
  stop(): Promise<void>;
}

export interface AdapterCaps {
  statusReport: boolean;               // 状态上报 → 红黄绿灯
  permissionSuspend: boolean;          // 能否挂起等用户回答（黄灯核心）
  proactiveAsk: boolean;               // 主动提问
  usage: 'exact' | 'approx' | 'none';  // token 统计精度（R9 风险应对）
}
```

**降级规则（Hub 侧执行）**：
- `permissionSuspend = false`（如 Codex notify 模式）：权限请求降级为**事后通知**——Agent 按 CLI 自身策略先跑，Hub 推送"repo-B 已自动执行 X（策略：on-failure）"，用户可事后叫停。黄灯在该 Agent 上退化为"通知灯"。
- `usage = 'none'`：Token 面板该 Agent 显示"不支持统计"。
- 适配器对 Hub 只暴露统一事件流（presence/state/ask/usage/commit），Hub 不感知 CLI 差异。

### 5.3 Claude Code 打样要点（M1）

hooks 配置（`.claude/settings.json`，由插件安装器写入）：

```json
{
  "hooks": {
    "PreToolUse":  [{ "hooks": [{ "type": "command", "command": "boss-plugin claude-code pre-tool" }] }],
    "PostToolUse": [{ "hooks": [{ "type": "command", "command": "boss-plugin claude-code post-tool" }] }],
    "Notification":[{ "hooks": [{ "type": "command", "command": "boss-plugin claude-code notify" }] }],
    "Stop":        [{ "hooks": [{ "type": "command", "command": "boss-plugin claude-code stop" }] }],
    "SessionStart":[{ "hooks": [{ "type": "command", "command": "boss-plugin claude-code session-start" }] }]
  }
}
```

`boss-plugin` 是插件 CLI：从 stdin 读 hook 事件 JSON → 转成统一协议 → 经本机 WS 发给 Hub；收到 `ask` 时以 hook 期望的 JSON 格式输出 permissionDecision（**这是"挂起等领导批准"的实现点**：hook 进程阻塞等待板子/手机回答）。

---

## 6. 协议 SSOT 与代码生成

```svg
<svg viewBox="0 0 760 300" xmlns="http://www.w3.org/2000/svg" font-family="ui-sans-serif,system-ui,Microsoft YaHei,sans-serif" font-size="12">
  <defs>
    <marker id="gen-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#7c5cfc"/>
    </marker>
  </defs>
  <style>
    .gbox { fill: #f4f4fa; stroke: #c9c9df; rx: 8; }
    .gtool { fill: #e7e0fb; stroke: #7c5cfc; stroke-width: 1.5; rx: 10; }
    .gdir { font-size: 13px; font-weight: 700; fill: #3a2a7a; }
    .gfile { fill: #5b5b78; }
    .gnote { fill: #8a8aa8; }
  </style>

  <!-- 输入：schema -->
  <rect x="250" y="20" width="260" height="40" class="gbox"/>
  <text x="380" y="45" text-anchor="middle" class="gdir">protocol/schema/hello.json</text>
  <text x="380" y="78" text-anchor="middle" class="gnote">JSON Schema：字段 / 类型 / 约束</text>
  <line x1="380" y1="60" x2="380" y2="100" stroke="#7c5cfc" stroke-width="1.5" marker-end="url(#gen-arr)"/>

  <!-- 生成器 -->
  <rect x="230" y="105" width="300" height="44" class="gtool"/>
  <text x="380" y="123" text-anchor="middle" font-size="13" font-weight="700" fill="#3a2a7a">tools/gen-protocol</text>
  <text x="380" y="140" text-anchor="middle" class="gnote">Node 脚本，开发期工具</text>
  <line x1="380" y1="149" x2="380" y2="190" stroke="#7c5cfc" stroke-width="1.5" marker-end="url(#gen-arr)"/>

  <!-- 输出目录 -->
  <rect x="180" y="195" width="400" height="118" rx="10" fill="#fbfbff" stroke="#7c5cfc" stroke-width="1.5"/>
  <text x="200" y="218" class="gdir">protocol/（四端生成物，随 schema 同步提交）</text>
  <line x1="200" y1="228" x2="560" y2="228" stroke="#e3e3f2" stroke-width="1"/>
  <text x="215" y="248" class="gfile">rust/src/messages.rs</text><text x="385" y="248" class="gnote">Rust：serde 结构（boss-protocol crate，固件业务层用）</text>
  <text x="215" y="268" class="gfile">kotlin/BossProtocol.kt</text><text x="375" y="268" class="gnote">Kotlin：data class（App）</text>
  <text x="215" y="288" class="gfile">c/boss_protocol.h</text><text x="345" y="288" class="gnote">C：结构 + 枚举（固件 UI 薄层 FFI 契约）</text>
  <text x="215" y="308" class="gfile">python/boss_protocol.py</text><text x="385" y="308" class="gnote">Python：dataclass（Hub / 插件桥）</text>
</svg>
```

- 控制消息 = **JSON 行帧**（`\n` 结尾，cJSON / serde_json / kotlinx 原生处理，链路无关）。
- 音频/文件 = **二进制帧**（帧头 `magic(2B) | type(1B) | len(2B) | payload`，与 JSON 帧在同一传输流上按 magic 区分）。
- 生成器只做"Schema → 结构声明"，编解码逻辑各端手写一次（消息少，不值得引入 protobuf 级别的重量）。

Schema 示例（hello）：

```json
{
  "$id": "hello",
  "type": "object",
  "required": ["type", "proto", "device", "fw", "caps"],
  "properties": {
    "type": { "const": "hello" },
    "proto": { "type": "integer", "minimum": 1 },
    "device": { "type": "string" },
    "fw": { "type": "string" },
    "caps": { "type": "array", "items": { "type": "string" } }
  }
}
```

---

## 7. 关键代码骨架

### 7.1 板端传输抽象（components/boss_transport）

```c
// components/boss_transport/include/boss_transport.h —— 设计骨架
typedef enum {
    BOSS_LINK_USB,      // TinyUSB CDC1
    BOSS_LINK_WS,       // WiFi WebSocket
    BOSS_LINK_BLE,      // GATT 伴侣
} boss_link_t;

typedef struct {
    boss_link_t link;
    esp_err_t (*connect)(void);                 /* 阻塞直到会话建立        */
    bool      (*up)(void);                      /* 心跳健康                */
    int       (*send_frame)(const uint8_t *f, size_t n);
    int       (*recv_frame)(uint8_t *buf, size_t n, int timeout_ms);
    void      (*disconnect)(void);
} boss_transport_ops_t;

/* 链路监管器：唯一决策点（PRD 4.1 状态机），按优先级尝试 USB > WS > BLE，
 * 切换时通知协议层发 sync(since_seq)。 */
void boss_transport_supervisor_start(void);

/* 帧回调 → boss_protocol 统一入口（seq 去重在此层） */
typedef void (*boss_frame_cb_t)(const uint8_t *frame, size_t len);
void boss_transport_on_frame(boss_frame_cb_t cb);
```

### 7.2 Hub 网关与会话（hub/boss_hub/gateway）

```python
# hub/boss_hub/gateway/session.py —— 设计骨架
# CDC 与 WS 两个入口产生同一种 DeviceSession；路由层不关心来自哪个链路
from abc import ABC, abstractmethod

class DeviceSession(ABC):
    @abstractmethod
    async def send(self, msg: dict) -> None: ...   # Envelope(dict) → 帧 → 链路
    def on_message(self, cb) -> None: ...          # 帧回调 → boss_protocol 解码
    @property
    @abstractmethod
    def link_kind(self) -> str: ...                # 'usb' | 'ws' | 'ble-relay'

# hub/boss_hub/core/router.py
# 心跳活跃的 session 集合 → DIRECT 路由；全部失活 → RELAY（云中继 + 推送）
class Router:
    def route(self, envelope: dict) -> None:
        sessions = self.registry.active_sessions()
        if not sessions:
            self.relay_queue.push(envelope)        # seq 入队防丢
        else:
            for s in sessions:
                s.send(envelope)                   # 板 + App 对等扇出
```

### 7.3 安卓 App 模块边界（android/）

```svg
<svg viewBox="0 0 780 280" xmlns="http://www.w3.org/2000/svg" font-family="ui-sans-serif,system-ui,Microsoft YaHei,sans-serif" font-size="12">
  <defs>
    <marker id="an-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#7c5cfc"/>
    </marker>
  </defs>
  <style>
    .abox { fill: #f4f4fa; stroke: #c9c9df; rx: 8; }
    .adsc { fill: #5b5b78; }
    .adir { font-size: 13px; font-weight: 700; fill: #3a2a7a; }
  </style>

  <!-- android/ble/ -->
  <rect x="30" y="25" width="150" height="34" class="abox"/>
  <text x="105" y="47" text-anchor="middle" class="adir">android/ble/</text>
  <line x1="180" y1="42" x2="218" y2="42" stroke="#7c5cfc" stroke-width="1.5" marker-end="url(#an-arr)"/>
  <text x="230" y="47" class="adsc">BossBleClient：GATT 连接、分帧、与 hub 连接管理器对接</text>

  <!-- android/app/ -->
  <rect x="30" y="95" width="150" height="34" class="abox"/>
  <text x="105" y="117" text-anchor="middle" class="adir">android/app/</text>
  <line x1="105" y1="129" x2="105" y2="150" stroke="#7c5cfc" stroke-width="1.5"/>
  <line x1="105" y1="150" x2="60" y2="150" stroke="#7c5cfc" stroke-width="1.5"/>

  <!-- terminal/ -->
  <line x1="60" y1="150" x2="60" y2="182" stroke="#7c5cfc" stroke-width="1.5"/>
  <line x1="60" y1="182" x2="90" y2="182" stroke="#7c5cfc" stroke-width="1.5"/>
  <rect x="90" y="165" width="120" height="34" class="abox"/>
  <text x="150" y="187" text-anchor="middle" class="adir">terminal/</text>
  <line x1="210" y1="182" x2="248" y2="182" stroke="#7c5cfc" stroke-width="1.5" marker-end="url(#an-arr)"/>
  <text x="260" y="187" class="adsc">对等终端四屏（电话簿 / 问答 / 来电 / 总览），Compose</text>

  <!-- chat/ -->
  <line x1="60" y1="150" x2="60" y2="225" stroke="#7c5cfc" stroke-width="1.5"/>
  <line x1="60" y1="225" x2="90" y2="225" stroke="#7c5cfc" stroke-width="1.5"/>
  <rect x="90" y="208" width="120" height="34" class="abox"/>
  <text x="150" y="230" text-anchor="middle" class="adir">chat/</text>
  <line x1="210" y1="225" x2="248" y2="225" stroke="#7c5cfc" stroke-width="1.5" marker-end="url(#an-arr)"/>
  <text x="260" y="230" class="adsc">web coding 对话界面（FR-51）：消息流 + 输入框 + diff 渲染</text>

  <!-- notify/ -->
  <line x1="60" y1="150" x2="60" y2="268" stroke="#7c5cfc" stroke-width="1.5"/>
  <line x1="60" y1="268" x2="90" y2="268" stroke="#7c5cfc" stroke-width="1.5"/>
  <rect x="90" y="251" width="120" height="34" class="abox"/>
  <text x="150" y="273" text-anchor="middle" class="adir">notify/</text>
  <line x1="210" y1="268" x2="248" y2="268" stroke="#7c5cfc" stroke-width="1.5" marker-end="url(#an-arr)"/>
  <text x="260" y="273" class="adsc">通知中心（FR-54）+ 前台服务（BLE 保活载体）</text>
</svg>
```

App 与板子的关系：**同一 device 身份的两个表现**还是**两个 device**？设计取**两个 device 会话**（App hello 时 `device: "android-app"`），Hub 按 to 语义扇出——避免"一个身份两个链路"的去重复杂度，且 App 天然常在线。

---

## 8. M0 语音垂直切片（板前预研，2026-08-29 插入）

板子 2026-09-13 才发货。为不阻塞开发，M0 在无实机窗口期用 **PC 仿真**完成语音链路的风险验证——所有 STT 逻辑先在 hub-lite 上跑通，板子到货后只需把"WAV 文件输入"换成"串口 PCM 输入"。

### 8.1 架构澄清：STT 的位置

板子是哑终端，**STT 不在板子上**。板子只负责录音与流式传输：

- 采样格式：16kHz / 16bit / mono PCM，约 **32KB/s**。
- USB CDC 裸流带宽富余百倍，**无需压缩、无需降质**；流式发送环形缓冲几 KB 即可，不缓存整段、不落 Flash。
- 16kHz 恰好是 Whisper 原生采样率，直接喂模型。

STT 是 **Hub 接线员模块的可插拔引擎**（主通道）；安卓 App 端兜底可用系统 `SpeechRecognizer`（免费，即用户所说"最差作为输入法"的落点）。

### 8.2 STT 三引擎可插拔（全部实装，配置切换）

| 引擎 | 接入 | 定位 |
|---|---|---|
| `windows-native` | `sapi-lite`（SAPI 封装，支持文件/内存流识别） | 零成本零延迟；中文一般、无热词——**先用它跑通链路** |
| `whisper-local` | `whisper-rs 0.16`（whisper.cpp 绑定，支持 initial_prompt 热词） | 免费离线、术语较好；需模型文件 + CMake 构建 |
| `cloud-api` | HTTP（字节火山/讯飞/OpenAI，配置切换） | 效果最好；按量付费，M2 起可切 |

统一接口（Hub 侧 trait）：

```rust
/// 16kHz/16bit/mono PCM → 文本；hotwords 为词表纠错提示（引擎支持则注入）
pub trait SttEngine {
    fn name(&self) -> &'static str;
    fn transcribe(&mut self, pcm: &[i16], hotwords: &[&str]) -> anyhow::Result<String>;
}
```

### 8.3 词表纠错层（生物/专业术语的解法）

专业术语（BWA / fastqc / hg38、仓库名、CLI 命令）识别差的解法**不是换更强的 STT，而是词表约束的 LLM 纠错**：

- 接线员 LLM 拿"已知词表"（联系人=仓库列表 + CLI 命令库 + 用户自定义生物术语词典）对转写文本做音近纠正。
- 词表放 Hub 配置文件，**热更新、不烧固件**——哑终端架构红利。
- 实测中"中等 STT 底座 + LLM 词表纠错"对专有名词的准确率远超单换顶级 STT。

### 8.4 任务与出口标准

| # | 任务 | 依赖 | 状态（2026-08-30） |
|---|---|---|---|
| 1 | Python hub 工程：asyncio 骨架 + STT 引擎（windows/whisper/cloud）+ hub-lite.py CLI（WAV → PCM → 文本） | — | 🔶 进行中（语音链路已用 Rust 验证工具 stt-validate 跑通，§8.5；正移植到 Python hub） |
| 2 | 评测样本：SAPI TTS 生成含生物术语的中文指令 WAV（如"把 BWA 比对跑一遍，参考基因组用 hg38"） | 1 | ✅ 完成，`tools/stt-samples/out/` 五样本 + manifest |
| 3 | 三引擎转写准确率对比 + 词表纠错收益验证 | 2 | 🔶 whisper 首轮完成（§8.5）；windows-native 待用户终端跑 `eval-windows.ps1`（沙箱拦截 SAPI 缓存写入） |
| 4 | 协议 SSOT：九条消息 Schema + 生成器 + 四端生成物（M1 任务 1 前置，纯 PC 侧可完成） | — | ✅ 完成：`protocol/schema/` 九条 + `tools/gen-protocol`（含 `--check` CI 校验）+ Rust crate（6 测试全绿，供固件）+ Kotlin + C 头（gcc 校验通过）+ Python 绑定 |
| 5 | 固件 Rust 骨架：esp-idf-hal 组件编译验证（不烧录） | 4 | ⬜ 未开始 |
| 6 | 语音输入法：词表纠错层（`operator/correct`）+ Windows 光标注入（`input/inject`）+ hub-lite `--type` | 1,3 | 🔶 本日实装（§8.6），冒烟通过 + 注入自检 OK；待用户终端真机注入验证 |

**出口标准**：含生物术语的指令 WAV 经 hub-lite 全链路，终端打出正确文本（三引擎中至少一个 + 纠错层达标）；`--type` 模式将纠错后文本落到光标处。

### 8.5 首轮评测结果（2026-08-29，ggml-base，验证工具 Rust `stt-validate` 于 WSL Arch 构建）

> **说明**：本评测用 M0 验证工具（Rust whisper-rs 引擎）跑通，目的是验证"哑终端 + 16kHz 直喂 whisper"链路成立。**生产 STT 已定用 Python hub 的 faster-whisper**，同一模型精度一致，评测结论复用。

五样本（SAPI TTS 合成，含生物/CLI 术语的中文指令）经 whisper-local 引擎转写：

| 样本 | 期望 | whisper-base 实际 | 关键差异 |
|---|---|---|---|
| 01-daily | 喂，让小张把测试跑一遍。 | 会让小张把特事跑一遍。 | 近音字：测试→特事 |
| 02-bio-bwa | 把BWA比对跑一遍，参考基因组用hg38。 | 8BWA比隊跑一遍,參考基因組用HG38。 | **BWA✓ hg38✓**；繁体混排 |
| 03-bio-fastqc | 用fastqc检查一下测序数据的质量，然后用multiqc汇总。 | 用fastq 检查一下测序数据的质量,然后用multiq会总。 | 术语尾部截断；汇总→会总 |
| 04-cli | 在ai-passport仓库上rebase一下主分支，然后提交PR。 | 在內,Passport倉庫上rebase一下主分支,然後提交PR。 | **rebase✓ PR✓**；仓库名偏 |
| 05-mixed | 看一下github上CI的结果，把clippy的警告都修掉。 | 看一下Graphub，CI的結果，clippy的警告都修掉。 | **CI✓ clippy✓**；github→Graphub |

结论：

1. **拉丁字母术语基本存活**（BWA/HG38/rebase/PR/CI/clippy 全对或仅大小写差异）——哑终端 + 16kHz 直喂 whisper 的链路设计成立。
2. 错误集中在两类，**均在词表纠错层（§8.3）的射程内**：繁简混排（比隊→比对、倉庫→仓库）与近音字（特事→测试、会总→汇总、Graphub→github）——词表 + 音近规则可修。
3. base 模型对中文一般；后续可换 small（~466MB）再测一轮，预期普通话错误率明显下降。
4. windows-native 引擎链路可通但 SAPI 需写 `%LOCALAPPDATA%\Microsoft\Speech` 适配缓存，TRAE 沙箱内被拦截（识别返回空）——用户终端跑 `tools/stt-samples/eval-windows.ps1` 出对比数据。
5. **生产路径（2026-08-30 定稿）**：Hub 用 Python（原定计划，AI 逻辑优先）。M0 的 Rust whisper-rs 引擎属验证工具，迁至 `tools/stt-validate/` 保留；Python hub 用 `faster-whisper`（同 ggml 模型，精度一致、加载更快），windows-native 引擎原样移植为 PowerShell 子进程实现。

### 8.6 语音输入法（PC 侧第一优先级，2026-08-30 定稿）

PC 端定位不是"转写展示台"，而是**系统级语音输入法**：STT + 词表纠错后的文字**直接打到当前前台光标处**——用户在哪个应用编辑，文字就落在哪里。**板子长按 OK 键是触发端**（M1 接 gateway `voice.start`，推-按说话）。agent 对话查询、意图路由都是后话，先把语音输入链路做健壮。

```
板子长按 OK → (USB CDC PCM 流) → Hub STT → 词表纠错 → Windows 光标注入
```

PC 侧四段（本日实装）：

| 模块 | 职责 | 健壮性 |
|---|---|---|
| `operator/stt.py` | 三引擎可插拔（windows / whisper / cloud） | 空转写不注入；引擎异常不静默丢字 |
| `operator/correct.py` | 词表纠错层（无 LLM 依赖，确定性） | 术语大小写归一（词边界，不误伤子串）+ 音近/形近替换（长词优先）+ 繁简归一 + 空白归一；用户词表 JSON 热更新、不烧固件 |
| `input/inject.py` | 文字落到光标处（Windows） | SendInput(UNICODE) 逐字键入主通道 + 剪贴板 Ctrl+V 兜底；UIPI 拦截自动降级；无前台窗口明确报错 |
| `dictation.py` | 编排 STT → 纠错 → 注入 | 空结果/注入失败记录不阻断；注入方式 type / paste / auto |

验证命令：

```bash
python hub/hub-lite.py tools/stt-samples/out/02-bio-bwa.wav --engine whisper --model <模型> --hotwords BWA,hg38 --type
```

- `--type`：纠错后文字注入当前光标处（语音输入法模式）
- `--no-correct`：关闭纠错层，度量纠错收益（§8.4 任务 3）
- `--selftest`：仅校验注入能力（前台窗口 + SendInput 通路），不发字

---

## 9. M1 任务分解（垂直切片，USB 先行）

| # | 任务 | 产出 | 依赖 |
|---|---|---|---|
| 1 | 协议 SSOT：hello/hello_ack/presence/state/ask/answer/ring/ring_ack/hangup 九条 Schema + 生成器 | `protocol/` + 四端生成物 | — |
| 2 | Hub 骨架（Python）：CDC 入口 + DeviceSession + Router + 事件总线 | `hub/` 可跑，`python -m hub serve` 监听串口 | 1 |
| 3 | 固件传输层（Rust）：boss_transport（usb 实现）+ boss_protocol（serde_json + seq 去重） | 插线即 hello 握手成功 | 1 |
| 4 | 固件手机系统框架（C + LVGL）：状态栏/桌面/导航/事件层（boss_app）+ 电话簿/问答/来电 UI | 全 UI 流程可演示（模拟数据） | 3 |
| 5 | 插件打样（Python）：claude-code hooks → adapter-core → Hub | 真实会话状态上电话簿 | 2 |
| 6 | 端到端联调：真实 Claude Code 权限 → 板子批准 → 回传 | M1 出口标准达成 | 4+5 |

任务 2/3/4 可三人并行；单人则按序。任务 1 是一切的前置，**协议 Schema 评审是 M1 的第一道闸门**。M0（第 8 节）在板子到货前完成，其任务 4 即本表任务 1。

---

## 10. 工程风险与待办

| # | 事项 | 说明 |
|---|---|---|
| E1 | Trae CLI 插件能力待调研 | 若无开放 hook，兜底方案：外层 wrapper 进程（解析 stdout/exit code），能力降级同 Codex |
| E2 | Codex 权限"事后通知"模式的产品体验 | PRD 黄灯语义在该模式下退化的具体 UI 措辞，DESIGN_PLUGIN 中细化 |
| E3 | 生成器首版范围 | M1 只做九条消息；后续增量加 schema 即重新生成，四端同步 |
| E4 | monorepo CI | 固件（ESP-IDF 构建）与 Rust 业务层（cargo build/test）双轨 + Hub/插件（pytest）一轨，`.github/workflows` 分离 |
| E5 | Android BLE 分帧重传协议 | DESIGN_ANDROID 中定义（帧头含 seq + 分片号，选择性重传） |
