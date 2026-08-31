# firmware/CMakeLists.txt —— BOSS PHONE 固件（ESP-IDF 工程）
#
# 注意：BOSS PHONE 固件入口（main/ = LVGL UI 薄层 + boss_app）待 DESIGN_FIRMWARE
# 落地后在此创建。当前本工程仅含共享硬件层 components/bsp；
# 上游基线 demo（可运行版本）已收敛到 reference/folotoy-card-demo/。
cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(boss-phone-firmware)
