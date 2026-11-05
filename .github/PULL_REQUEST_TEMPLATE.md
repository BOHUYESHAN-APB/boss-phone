# 拉取请求（Pull Request）

> 提交前请确认：本 PR 只做一个主题的改动，已按 `CONTRIBUTING.md` §5 跑过本地验证。
> 标题请按 Conventional Commits 写，例如 `feat(hub): add golden-vector byte check`。

## 变更说明

<!-- 为什么改、改了什么、有没有替代方案被否掉 -->

## 影响范围

<!-- 勾选所有受影响的部分 -->
- [ ] `firmware/`（BSP / 固件入口 / 构建配置）
- [ ] `reference/folotoy-card-demo/`（仅限与共享 BSP 一致性的改动）
- [ ] `hub/`（gateway / core / operator / 语音输入法）
- [ ] `protocol/`（Schema 或四端生成物 / 黄金向量）
- [ ] `tools/`（协议生成器 / STT 评测 / PDF 导出）
- [ ] `docs/` 与仓库基建（CI、模板、`.gitignore` 等）

## 验证清单（必填）

- [ ] **构建通过**：本地 `idf.py build`（固件相关）和/或 CI 三 job（protocol / hub / firmware）全绿
- [ ] **测试通过**：`python -m pytest tests -q`（hub，71 项）与 `cargo test -p boss-protocol --quiet`（协议相关）
- [ ] **Lint 通过**：`python -m ruff check hub tests` 与 `python -m ruff format --check hub tests`
- [ ] **协议生成物已同步**：`node tools/gen-protocol/generate.mjs --check` 与 `python tools/gen-protocol/vectors.py --check` 均 OK（改动协议时必勾）
- [ ] **无密钥入库**：未提交 `hub.toml`、token、api_key、设备凭据、录音/模型等敏感或大体积产物
- [ ] **真机验收记录**（硬件相关改动必填，见下节；纯文档/CI 改动可填 N/A）

## 真机验收（硬件相关改动）

<!--
构建结果与真机结果请分开写：
- 构建结果：编译器版本 / 目标 / 是否零 warning
- 真机结果：板子批次与修订版、烧录命令、实际观察到的现象（屏幕/按键/音频/电池）
-->
- 硬件批次 / 修订版：
- 供电方式：USB / 电池
- 烧录命令：
- 真机观察结果：
- 截图或照片（显示类改动必附）：

## 兼容性与影响面

- [ ] 无协议 / 引脚 / 配置兼容性影响
- [ ] 有兼容性影响（请在下方说明字段、引脚或配置变更及迁移方式）

<!-- 例如：协议字段新增可选字段 / BSP 引脚变更 / hub.toml 新增配置项 -->

## 关联 Issue

<!-- Closes #123 -->
