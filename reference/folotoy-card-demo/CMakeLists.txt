# reference/folotoy-card-demo/CMakeLists.txt
# 上游 FoloToy-Card 基线 demo（原仓库根 main/），收敛为参考工程，保留不删。
# 复用共享硬件层 firmware/components/bsp（单一事实来源，不拷贝、不 fork）。
cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
set(EXTRA_COMPONENT_DIRS "${CMAKE_CURRENT_LIST_DIR}/../../firmware/components")
project(folotoy-card-demo)
