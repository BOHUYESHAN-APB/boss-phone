# GitHub / Git 组织与发布策略（计划）

> 状态：**已建仓并推送**（2026-08-31）。公开仓 `BOHUYESHAN-APB/boss-phone`，CI 全绿。剩余：v0.1.0 tag、Release 资产（待固件可用）。

## 0. 决策记录（用户拍板 + 执行结果）

| 主题 | 决定 | 结果 |
|---|---|---|
| 仓库形态 | **单仓库 monorepo**（保持） | ✅ 已重排并推送 |
| 命名 | 仓库 **`boss-phone`**；产品名 **BOSS PHONE（领导电话）** | ✅ 建于个人账号 `BOHUYESHAN-APB/boss-phone`（公开） |
| 发布策略 | **先只打 git tag**（v0.1.0 起）；Release 资产待固件可用 + CI 后接 | ⬜ v0.1.0 tag 待打 |
| 示例代码 | **不删**，收敛到 `reference/folotoy-card-demo/` | ✅ 已收敛 |
| 上游文档 | `docs/AI_HARDWARE_DEVELOPMENT_GUIDE.md` 等**保留** | ✅ |
| README | **重写为我们的** | ✅ |
| CI | GitHub Actions 三 job：协议 `--check` + hub Python 测试 + 固件 ESP-IDF（RTOS）编译 | ✅ **2026-08-31 全绿** |

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
| G4 | `.github/workflows/ci.yml`（协议 --check + hub py_compile/测试 + 固件 esp-idf 编译） | push 后 Actions 绿 | ✅ 2026-08-31 三 job 全绿（含 RTOS 固件编译） |
| G5 | 本地打 `v0.1.0` tag（暂不推送） | `git tag` 可查 v0.1.0 | ⬜ 待办 |
| G6 | v0.2.0 接 Release 资产（固件 bin + Hub 包） | Release 附件可下载 | ⬜ 暂缓（固件可用后） |

**CI 验证结论（2026-08-31）**：GitHub Actions 支持 RTOS 验证——`espressif/esp-idf-ci-action@v1`（官方 ESP-IDF Docker）成功编译 `reference/folotoy-card-demo`（ESP32-C3 / FreeRTOS）；Python hub 在 Linux 上 compileall + 10 测试通过；协议生成产物与 schema 同步。

## 7. 待用户决定

1. 仓库要绑定到哪些其他内容（影响 org 下多仓划分）。
2. 是否打 `v0.1.0` tag。
3. 是否把 Hub 发布为 PyPI 包（插件生态分发落点）。
