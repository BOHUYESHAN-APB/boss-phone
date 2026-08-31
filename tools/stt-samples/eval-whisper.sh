#!/usr/bin/env bash
# M0 STT 评测：whisper-local 引擎跑全部样本（DESIGN_OVERVIEW §8.4 任务 3）
# 环境：WSL Arch（Rust release 构建见 ~/boss），模型用 Windows 侧 tools/stt-validate/models/
# 用法：wsl -d arch-linux-current -- bash /mnt/c/.../tools/stt-samples/eval-whisper.sh

set -euo pipefail

MODEL=/mnt/c/Users/ETPau/Documents/GITHUB/ai-passport/tools/stt-validate/models/ggml-base.bin
DIR=/mnt/c/Users/ETPau/Documents/GITHUB/ai-passport/tools/stt-samples/out
BIN=~/boss/target/release/hub-lite

run() {
    # $1=文件名 $2=热词(逗号分隔)；只取“转写结果”下一行
    "$BIN" "$DIR/$1" --engine whisper --model "$MODEL" --hotwords "$2" 2>/dev/null \
        | grep -A1 "转写结果" | tail -1
}

echo "===== whisper-local（ggml-base）五样本评测 ====="
echo ""
echo "[01-daily] 期望: 喂，让小张把测试跑一遍。"
echo "  实际: $(run 01-daily.wav 小张)"
echo ""
echo "[02-bio-bwa] 期望: 把BWA比对跑一遍，参考基因组用hg38。"
echo "  实际: $(run 02-bio-bwa.wav BWA,hg38)"
echo ""
echo "[03-bio-fastqc] 期望: 用fastqc检查一下测序数据的质量，然后用multiqc汇总。"
echo "  实际: $(run 03-bio-fastqc.wav fastqc,multiqc,测序数据)"
echo ""
echo "[04-cli] 期望: 在ai-passport仓库上rebase一下主分支，然后提交PR。"
echo "  实际: $(run 04-cli.wav ai-passport,rebase,PR)"
echo ""
echo "[05-mixed] 期望: 看一下github上CI的结果，把clippy的警告都修掉。"
echo "  实际: $(run 05-mixed.wav github,CI,clippy)"
