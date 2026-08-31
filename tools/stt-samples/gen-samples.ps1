# M0 STT 评测样本生成（DESIGN_OVERVIEW §8.4 任务 2）
# 用 System.Speech TTS 生成 16k/16bit/mono 中文指令 WAV（含生物/CLI 术语）
# 用法: powershell -ExecutionPolicy Bypass -File gen-samples.ps1 [输出目录]
param([string]$OutDir = "$PSScriptRoot\out")

Add-Type -AssemblyName System.Speech

# 板端格式契约：16kHz / 16bit / mono（与 hub::audio 校验一致）
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer

# 优先选中文语音（未安装中文语音包时 TTS 合成中文会失败，需装语言包）
$zh = $synth.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like "zh*" } | Select-Object -First 1
if ($zh) {
    $synth.SelectVoice($zh.VoiceInfo.Name)
    Write-Host "TTS 语音: $($zh.VoiceInfo.Name)"
} else {
    Write-Warning "未找到中文 TTS 语音（Huihui/Yaoyao 等），中文样本可能无法正确合成——请安装中文语言包"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# 样本表：文件名 → 期望文本（manifest.json 供准确率评测脚本对照）
$samples = [ordered]@{
    "01-daily"      = "喂，让小张把测试跑一遍。"
    "02-bio-bwa"    = "把BWA比对跑一遍，参考基因组用hg38。"
    "03-bio-fastqc" = "用fastqc检查一下测序数据的质量，然后用multiqc汇总。"
    "04-cli"        = "在ai-passport仓库上rebase一下主分支，然后提交PR。"
    "05-mixed"      = "看一下github上CI的结果，把clippy的警告都修掉。"
}

$manifest = @()
foreach ($kv in $samples.GetEnumerator()) {
    $wav = Join-Path $OutDir "$($kv.Key).wav"
    $synth.SetOutputToWaveFile($wav, $fmt)
    $synth.Speak($kv.Value)
    $manifest += [pscustomobject]@{ file = "$($kv.Key).wav"; text = $kv.Value }
    Write-Host "生成: $wav"
}

$manifest | ConvertTo-Json | Out-File (Join-Path $OutDir "manifest.json") -Encoding utf8
Write-Host "完成，清单: $(Join-Path $OutDir 'manifest.json')"
