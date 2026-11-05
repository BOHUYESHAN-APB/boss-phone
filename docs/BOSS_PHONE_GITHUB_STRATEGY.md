# GitHub / Git 组织与发布策略

> 状态：**已建仓并推送**（2026-08-31），**仓库规范化与 CI 复绿完成**（2026-11-05），**v0.1.0 tag 已打**（2026-11-06）。公开仓 `BOHUYESHAN-APB/boss-phone`，三个 CI job 全绿。剩余：Release 资产（待固件可用）。

## 0. 决策记录（用户拍板 + 执行结果）

| 主题 | 决定 | 结果 |
|---|---|---|
| 仓库形态 | **单仓库 monorepo**（保持） | ✅ 已重排并推送 |
| 命名 | 仓库 **`boss-phone`**；产品名 **BOSS PHONE（领导电话）** | ✅ 建于个人账号 `BOHUYESHAN-APB/boss-phone`（公开） |
| 发布策略 | **先只打 git tag**（v0.1.0 起）；Release 资产待固件可用 + CI 后接 | ✅ v0.1.0 tag 已打并推送（2026-11-06） |
| 示例代码 | **不删**，收敛到 `reference/folotoy-card-demo/` | ✅ 已收敛 |
| 上游文档 | `docs/AI_HARDWARE_DEVELOPMENT_GUIDE.md` 等**保留** | ✅ |
| README | **重写为我们的**（中文主版 + 英文版，按真实现状） | ✅ 2026-11-05 |
| 仓库基建 | gitattributes / editorconfig / CONTRIBUTING / SECURITY / CHANGELOG / PR 与 Issue 模板 / Dependabot | ✅ 2026-11-05 |
| CI | GitHub Actions 三 job：协议 `--check` + 黄金向量 + Rust roundtrip；hub compileall + ruff + pytest；固件 ESP-IDF（RTOS）编译 | ✅ **2026-11-05 三 job 全绿** |

## 1. 仓库形态：monorepo（保持）

- 协议 SSOT（`protocol/`）被固件/Hub/插件四端共享 → 单仓保证原子变更、一次 CI 跑四端。
- 现状即单仓，保持。

## 2. 组织形态

- 原远程 `FoloToy/ai-passport` 保留为备份 remote `folotoy`；**主仓迁至个人账号 `BOHUYESHAN-APB/boss-phone`（公开）**。
- "仓库要绑定到其他内容"待定；如后续插件生态要分发，可再开 org 或在 org 下建插件仓库。

## 3. 仓库布局（已重排，已推送）

```
boss-phone/
├── README.md / README.zh_CN.md   # 我们的（已重写）
├── AGENTS.md                     # 已更新路径
├── LICENSE / Cargo.toml / .gitignore / .clangd
├── .github/workflows/ci.yml      # 协议 --check + hub 测试 + 固件编译
├── docs/                         # BOSS_PHONE_*.md（我们的）+ AI_HARDWARE_DEVELOPMENT_GUIDE.md（保留）
├── firmware/                     # 固件：components/bsp（硬件层）；main/ 待 boss_app
├── reference/folotoy-card-demo/  # 上游基线 demo（收敛保留，复用共享 BSP）
├── hub/                          # PC 总机房（Python）+ tests/
├── protocol/                     # 协议 SSOT + 四端绑定
├── tools/                        # 生成器 / STT 评测 / PDF
└── plugins/                      # （未来）插件桥 SDK
```

- 移动记录：`main/`、`tests/` → `reference/folotoy-card-demo/`；`components/`、`CMakeLists.txt`、`sdkconfig.defaults` → `firmware/`（git mv 保留历史）。
- 产物清理：`tools/stt-samples/out/`、`tools/stt-validate/models/`、`tools/pdf-export/_out/`、`node_modules/` 已 gitignore；**whisper 模型（141MB）已从历史中 filter 清除**。

## 4. Git 工作流

- **分支模型**：`main` 主干 + 短期 feature branch + PR 合并（PR 说明硬件/修订、构建与真机结果）。
- **提交约定**：Conventional Commits（`feat(bsp)/feat(hub)/fix/refactor/docs` 等），延续 AGENTS.md。
- **备份分支**：`backup/pre-boss-phone-20260824` 保留为只读快照；原 `FoloToy/ai-passport` 保留为 remote `folotoy`。
- **CI 门禁（已启用）**：push/PR 触发，见 §6。

## 5. GitHub 发布

- **版本节奏**：语义化 tag `vX.Y.Z`，与任务表里程碑对齐。当前节点 = **v0.1.0**（M0 收尾：协议四端 + STT/纠错/注入链路）。
- **先只打 tag**：本地 tag + 推送；Release 资产（固件 bin、Hub 包）留到 v0.2.0 接 CI 出包。
- 预发布标签：`v0.x.y-alpha/beta` 用于联调期。

## 6. CI 与任务表

| ID | 任务 | 验收 | 状态 |
|---|---|---|---|
| G1 | 本地重排仓库布局（firmware/reference 收敛） | `git status` 显示 R（保留历史）；AGENTS/README 路径一致 | ✅ |
| G2 | README 重写为我们的 + .gitignore 补产物规则 | README 介绍 BOSS PHONE/布局/快速开始；模型/产物不进版本库 | ✅ |
| G3 | 建公开仓 `BOHUYESHAN-APB/boss-phone` + 推送 main | 远程可访问；origin 指向新仓；历史完整 | ✅ 2026-08-31 |
| G4 | `.github/workflows/ci.yml`（协议 --check + hub py_compile/测试 + 固件 esp-idf 编译） | push 后 Actions 绿 | ✅ 2026-11-05 三 job 全绿（升级为 5 项门禁，见下） |
| G5 | 本地打 `v0.1.0` tag（暂不推送） | `git tag` 可查 v0.1.0 | ✅ 2026-11-06 |
| G6 | v0.2.0 接 Release 资产（固件 bin + Hub 包） | Release 附件可下载 | ⬜ 暂缓（固件可用后） |
| G7 | 仓库规范化基建（gitattributes/editorconfig/贡献与安全/PR 与 Issue 模板/Dependabot） | 新文件入库且 CI 不回归 | ✅ 2026-11-05 |
| G8 | README / AGENTS 改为本仓库真实现状（不再沿用上游模板腔） | 中文主 README + 英文 README + Agent 约定三份一致 | ✅ 2026-11-05 |

**CI 验证结论（2026-11-05 复绿）**：三个 job 全绿，门禁较 8 月版更严：

| job | 门禁 |
|---|---|
| `protocol` | `generate.mjs --check` + `vectors.py --check` + `cargo test -p boss-protocol`（黄金向量 roundtrip） |
| `hub` | `compileall` + `ruff check` + `ruff format --check` + `pytest`（71 用例） |
| `firmware` | ESP-IDF v5.5 / esp32c3 编译 `reference/folotoy-card-demo`（产出 694KB app 镜像，分区余量 34%） |

固件 job 有两处踩坑记录（已修复，勿回退）：
1. `idf-component-manager` 在"检查组件新版本"时会完整重解依赖图；lvgl 9.6.0 起清单带
   `$CONFIG{LV_USE_FREETYPE}` 条件依赖，重解阶段 Kconfig 未生成 → `MissingKconfigError`。
   解法：提交 `dependencies.lock`（与 BSP 清单 `manifest_hash` 配套）+ 设
   `IDF_COMPONENT_CHECK_NEW_VERSION=0`。
2. `dependencies.lock` 是**要入库的**，不是构建产物（旧 `.gitignore` 把它忽略了）。

## 6.1 Git 传输排障（本机 2026-11 实测）

本机 git 直连 GitHub 曾失败，两条独立原因：

- **TLS 被本机代理软件中间人接管**：`github.com` 被解析到 `127.0.0.1`，443 上是
  Steamcommunity302/Watt Toolkit 的 MITM 证书；git 默认 `http.sslBackend=schannel`
  走 Secure Channel 时直接报 `schannel: AcquireCredentialsHandle failed:
  SEC_E_NO_CREDENTIALS`。
- **凭据助手不可用**：`credential.https://github.com.helper` 指向 gh CLI，
  而 git 调 `sh.exe` 时在受限环境里 `couldn't create signal pipe`。

可用配置（已写入本仓库 `.git/config`，仅影响本仓库）：
`http.sslBackend=openssl` + `http.sslCAInfo=.git/ca-bundle-boss-phone.pem`
（系统根证书 + MITM 根证书合并导出；**该文件在 `.git/` 内，不入库**）。
推送时用一次性 header 注入令牌：

```bash
TOKEN=$(gh auth token)
B64=$(printf 'x-access-token:%s' "$TOKEN" | base64 -w0)
git -c credential.helper= \
    -c "http.https://github.com/.extraHeader=Authorization: Basic $B64" push origin main
```

（Windows PowerShell 里 `base64 -w0` 换成 .NET：
`[Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("x-access-token:$TOKEN"))`。）

## 7. remote 与本机备份

| remote | 用途 | 写权限 |
|---|---|---|
| `origin` | `https://github.com/BOHUYESHAN-APB/boss-phone.git`，**云端主仓** | 可推送 |
| `folotoy` | `https://github.com/FoloToy/ai-passport/`，上游基线，只读参考 | 已禁用推送（url 设为 `DISABLED_UPSTREAM_READ_ONLY`） |
| `local` | `file:///.git/mirrors/boss-phone.git`，本机 bare 镜像（git dir 内，不入库） | 可推送 |

另有全量快照 `git bundle`：`.git/mirrors/boss-phone.bundle`。

## 8. 待用户决定

1. 仓库要绑定到哪些其他内容（影响 org 下多仓划分）。
2. ~~是否打 `v0.1.0` tag~~ → 已打（2026-11-06，见 §5）。
3. 是否把 Hub 发布为 PyPI 包（插件生态分发落点）。
4. 是否给 CI 增加 ESP-IDF 构建产物（bin）作为 Release 资产上传。
