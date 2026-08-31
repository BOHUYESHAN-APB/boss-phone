# M0 STT 评测：windows-native 引擎跑全部样本（DESIGN_OVERVIEW §8.4 任务 3）
# 需在用户自己的终端运行（非 TRAE 沙箱）——SAPI 要写
# %LOCALAPPDATA%\Microsoft\Speech\Files\MSASR\*.dat 适配缓存，沙箱会拦截导致识别返回空。
# 用法: powershell -ExecutionPolicy Bypass -File eval-windows.ps1
# 结果写入 out\windows-results.txt

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$root = Split-Path $PSScriptRoot -Parent   # tools/
$repo = Split-Path $root -Parent           # 仓库根
$bin = Join-Path $repo "target\debug\hub-lite.exe"
$out = Join-Path $PSScriptRoot "out"

if (-not (Test-Path $bin)) {
    Write-Error "未找到 $bin，请先: cargo build -p stt-validate --bin hub-lite"
}

$samples = [ordered]@{
    "01-daily"      = "喂，让小张把测试跑一遍。"
    "02-bio-bwa"    = "把BWA比对跑一遍，参考基因组用hg38。"
    "03-bio-fastqc" = "用fastqc检查一下测序数据的质量，然后用multiqc汇总。"
    "04-cli"        = "在ai-passport仓库上rebase一下主分支，然后提交PR。"
    "05-mixed"      = "看一下github上CI的结果，把clippy的警告都修掉。"
}

$lines = @()
$lines += "===== windows-native（SAPI 听写）五样本评测 ====="
$lines += ""

foreach ($kv in $samples.GetEnumerator()) {
    $wav = Join-Path $out "$($kv.Key).wav"
    Write-Host "识别中: $($kv.Key)"
    $all = & $bin $wav --engine windows
    $idx = [array]::IndexOf($all, "转写结果:")
    $text = if ($idx -ge 0 -and $idx + 1 -lt $all.Count) { $all[$idx + 1] } else { "（解析失败）" }
    $lines += "[$($kv.Key)] 期望: $($kv.Value)"
    $lines += "  实际: $text"
    $lines += ""
}

$report = Join-Path $out "windows-results.txt"
$lines | Out-File $report -Encoding utf8
Write-Host ""
Write-Host "完成，结果已写入: $report"
Write-Host "（把该文件交给 TRAE 即可继续三引擎对比分析）"
