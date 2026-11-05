# 安全策略（SECURITY）

## 支持范围

| 组件 | 支持状态 |
|---|---|
| `hub/`（Python 总机房） | ✅ 当前开发主线 |
| `firmware/`（BSP + 固件入口） | ✅ 当前开发主线 |
| `protocol/`（SSOT + 四端绑定） | ✅ 当前开发主线 |
| `reference/folotoy-card-demo/` | ⚠️ 上游基线参考代码，仅接受"与产品路径共享 BSP 时"的安全修复 |
| `docs/`、`tools/` | ✅ 随主线修复 |

当前版本尚未发布正式 Release（v0.1.0 tag 待打），安全修复以 `main` 分支快进方式提供。

## 如何报告漏洞

**请不要开公开 issue、不要在 PR 或讨论区贴利用细节。**

优先级从高到低：

1. **GitHub Security Advisory（首选）**：仓库 `Security` → `Report a vulnerability`
   （<https://github.com/BOHUYESHAN-APB/boss-phone/security/advisories/new>），可私密沟通、协商修复窗口与致谢方式。
2. 若无法使用 Advisory：通过维护者 GitHub 主页所列的联系方式私信（邮件/私聊），标题注明 `[SECURITY]`。

报告请尽量包含：受影响组件与版本/commit、复现步骤或 PoC、影响面评估（数据泄露 / 越权 / 拒绝服务）、你希望的处理时限。我们会在 **3 个工作日内**确认收到，并在修复发布后按需公开致谢（可匿名）。

## 本项目的敏感面（威胁模型见 `docs/BOSS_PHONE_DESIGN_SECURITY.md`）

| 敏感对象 | 位置 | 说明 |
|---|---|---|
| 设备↔Hub 鉴权 token | `hub.toml` 的 `ws.token`；设备 nvs | 长期凭据；默认值 `change-me` **必须在部署时替换** |
| 设备配对码 | 首次 USB 连接时板子屏幕显示 6 位码 | 防止工位邻居插线冒充设备 |
| 接线员（Operator）模型密钥 | `hub.toml` 的 `operator.api_key` | 第三方 API 计费凭据，泄露即资损 |
| CI/遥测 GitHub token | `hub.toml` 的 `telemetry.github_token` | 建议最小只读 scope，优先走本机 `gh` CLI |
| 云中继 token | `hub.toml` 的 `relay.token` | 阶段 3 公网形态使用 |
| 插件 token | 插件安装器写入 CLI 配置 + Hub | 防止恶意插件冒名上报/诱导批准 |
| 设备 nvs 中的凭据 | 固件 nvs 分区 | 不得以明文写入日志或串口输出 |

## 硬性规则

- **密钥一律不入库**：`hub.toml`、`.env`、模型密钥、设备凭据、token 都不提交。仓库 `.gitignore` 已忽略 `hub.toml`；示例配置请写进文档（如 `docs/BOSS_PHONE_DESIGN_DEPLOYMENT.md`）并用占位符。
- 日志中不得输出完整 token / api_key / 音频 payload 明文；排障需要时用 `debug_payload` 本地开关，且不得把日志贴进 issue。
- **录音与语音数据默认不留存**：hub 侧不持久化原始音频；云端 STT/LLM 请求按最小必要传输，备忘录音"上传即删"为默认行为。用户主动开启留存时才落盘，并在部署文档醒目提示。
- 局域网 WS 默认仅绑定内网接口、必须校验 token；云中继默认关闭，由用户显式开启。
- 依赖引入保持最小面：新依赖需说明用途与维护状态；CI 通过 Dependabot 跟踪 pip / npm / cargo / GitHub Actions 更新。
- 固件侧不得在串口/USB 控制台打印 nvs 凭据；OTA 相关改动需说明签名与回滚策略。

## 披露节奏

- 修复合并后，经报告者同意再发布 Advisory（含影响版本、修复版本、缓解措施）。
- 在修复可被利用前，不公开 PoC；协调窗口默认为 90 天，可协商缩短或延长。
