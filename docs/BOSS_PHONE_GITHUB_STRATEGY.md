# GitHub / Git 组织与发布策略（计划）

> 状态：本地计划 + 本地重排已执行（2026-08-31）。**GitHub 侧操作（改名/推送/打 tag/CI）全部推迟**，等"仓库要绑定到其他内容"的决定后再动。

## 0. 决策记录（用户拍板）

| 主题 | 决定 |
|---|---|
| 仓库形态 | **单仓库 monorepo**（保持） |
| 命名 | 仓库将来改 `FoloToy/boss-phone`；产品名 **BOSS PHONE（领导电话）**；改名**暂缓**，待绑定决定后执行 |
| 发布策略 | **先只打 git tag**（v0.1.0 起）；Release 资产（固件 bin / Hub 包）待固件可用 + CI 后接 |
| 示例代码 | **不删**，收敛到 `reference/folotoy-card-demo/`（参考硬件逻辑怎么写） |
| 上游文档 | `docs/AI_HARDWARE_DEVELOPMENT_GUIDE.md` 等开发指南**保留** |
| README | **重写为我们的**（已执行） |
| 执行时机 | **本地先做**；GitHub push/改名/CI 等用户决定 |

## 1. 仓库形态：monorepo（保持）

- 协议 SSOT（`protocol/`）被固件/Hub/插件四端共享 → 单仓保证原子变更、一次 CI 跑四端。
- 现状即单仓，保持。

## 2. 组织形态：FoloToy org（现状保持）

- 远程：`https://github.com/FoloToy/ai-passport`（已在 **FoloToy 组织**下）。
- 后端/发布含义：Hub 是 Python 包（本地部署），不依赖 GitHub 托管；"仓库绑定到其他内容"待定，可能影响 org 下多仓划分（固件/Hub/插件注册表）。
- 结论：org 保持；是否在 org 下新建插件/其他仓库，等绑定决定。

## 3. 仓库布局（本次已重排，本地）

```
boss-phone/
├── README.md / README.zh_CN.md   # 我们的（已重写）
├── AGENTS.md                     # 已更新路径
├── LICENSE / Cargo.toml / .gitignore / .clangd
├── docs/                         # BOSS_PHONE_*.md（我们的）+ AI_HARDWARE_DEVELOPMENT_GUIDE.md（保留）
├── firmware/                     # 固件：components/bsp（硬件层）；main/ 待 boss_app
├── reference/folotoy-card-demo/  # 上游基线 demo（收敛保留，复用共享 BSP）
├── hub/                          # PC 总机房（Python）
├── protocol/                     # 协议 SSOT + 四端绑定
├── tools/                        # 生成器 / STT 评测 / PDF
└── plugins/                      # （未来）插件桥 SDK
```

- 移动记录：`main/`、`tests/` → `reference/folotoy-card-demo/`；`components/`、`CMakeLists.txt`、`sdkconfig.defaults` → `firmware/`（git mv 保留历史）。
- 产物清理：`tools/stt-samples/out/`、`tools/pdf-export/_out/` 已加 `.gitignore`（脚本保留、产物不提交）。

## 4. Git 工作流

- **分支模型**：`main` 主干 + 短期 feature branch + PR 合并（PR 说明硬件/修订、构建与真机结果）。
- **提交约定**：Conventional Commits（`feat(bsp)/feat(hub)/fix/refactor/docs` 等），延续 AGENTS.md。
- **备份分支**：`backup/pre-boss-phone-20260824` 保留为只读快照，不合并、不删除。
- **CI 门禁（待 GitHub 侧启用后）**：协议 `--check`、hub `py_compile`、固件编译；push 后查 Actions。

## 5. GitHub 发布

- **版本节奏**：语义化 tag `vX.Y.Z`，与任务表里程碑对齐。当前节点 = **v0.1.0**（M0 收尾：协议四端 + STT/纠错/注入链路）。
- **先只打 tag**：本地 tag + 远端 tag（待推送决定）；Release 资产（固件 bin、Hub 包）留到 v0.2.0 接 CI 出包。
- 预发布标签：`v0.x.y-alpha/beta` 用于联调期。

## 6. 任务表

| ID | 任务 | 验收 | 状态 |
|---|---|---|---|
| G1 | 本地重排仓库布局（firmware/reference 收敛） | `git status` 显示 R（保留历史）；AGENTS/README 路径一致 | ✅ 完成 |
| G2 | README 重写为我们的 + .gitignore 补产物规则 | README 介绍 BOSS PHONE/布局/快速开始；`stt-samples/out` 不进版本库 | ✅ 完成 |
| G3 | 本地打 `v0.1.0` tag（暂不推送） | `git tag` 可查 v0.1.0，锚定 M0 收尾点 | ⬜ 待办（用户确认后） |
| G4 | GitHub 仓库改名 `FoloToy/boss-phone` | 访问新地址有效；旧地址重定向；本地 remote 更新 | ⬜ 暂缓（绑定决定后） |
| G5 | 建 `.github/workflows/`（协议 --check + hub py_compile） | push 后 Actions 绿 | ⬜ 暂缓（GitHub 侧启用后） |
| G6 | v0.2.0 接 Release 资产（固件 bin + Hub 包） | Release 附件可下载 | ⬜ 暂缓（固件可用后） |

## 7. 待用户决定

1. 仓库要绑定到哪些其他内容（影响 org 下多仓划分）。
2. GitHub 侧（改名/推送/tag/CI）何时启用。
3. 是否把 Hub 发布为 PyPI 包（插件生态分发落点）。
