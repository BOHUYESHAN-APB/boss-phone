# folotoy-card-demo —— 上游基线演示（参考工程）

> 收敛自上游 FoloToy-Card 固件基线（原仓库根 `main/`）。**保留不删**，作为"关键硬件逻辑怎么写"的参考实现。BOSS PHONE 产品固件走 `firmware/`（boss_app 落地后使用），**不在此工程上迭代**。

## 这是什么

一个最小完整可运行的 ESP-IDF 工程：LVGL 菜单 + 四个独立硬件验证页，展示如何调用共享 BSP（`../../firmware/components/bsp`）驱动本板外设。硬件逻辑要点全在演示页里，是理解板级驱动的活文档：

| 目录/文件 | 演示的硬件逻辑 |
|---|---|
| `main/main.c` | BSP 初始化顺序、LVGL 任务锁（`bsp_lvgl_lock/unlock`）、按键事件分发（菜单 vs 演示页） |
| `main/demo_display.c` | LCD/SPI 显示初始化 + LVGL 接入（`bsp_display_*`） |
| `main/demo_button.c` | 按键矩阵、短按/长按事件语义（`bsp_button_*`、`BSP_BTN_LONG`） |
| `main/demo_audio.c` | 音频 codec：`bsp_audio_set_format(16k/16bit/mono)`、播放/录音走独立任务、**C3 无 PSRAM 的 96KB 录音缓冲分配失败处理** |
| `main/demo_battery.c` | 电池 ADC 采样与电量换算（`bsp_battery_*`） |
| `main/ui_pixel.*` | 点阵像素 UI 库（自绘菜单卡片/吉祥物） |
| `main/ui_pixel_math.*` | 纯数学动画函数（闪烁/跳动），可主机单测 |

## 构建

共享硬件层在 `firmware/components/bsp`（本工程通过 `EXTRA_COMPONENT_DIRS` 引用，不拷贝）。ESP-IDF 5.5.x：

```bash
cd reference/folotoy-card-demo
get_idf553
idf.py set-target esp32c3
idf.py build
```

主机逻辑测试（`ui_pixel_math`）：

```bash
cc tests/test_ui_pixel_math.c main/ui_pixel_math.c -o /tmp/t && /tmp/t
```

## 与 BOSS PHONE 的关系

- 本工程 = 上游基线（硬件能力的最小可执行说明），**不改写**。
- BOSS PHONE 固件 = `firmware/`（目前仅 `components/bsp` 硬件层；`main/` 待 boss_app 落地）。
- 硬件约束 / 事实来源优先级见根 `AGENTS.md` 与 `docs/AI_HARDWARE_DEVELOPMENT_GUIDE.md`（保留的上游开发指南）。
