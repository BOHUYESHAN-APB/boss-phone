//! windows-native 引擎：PowerShell 子进程调 System.Speech（SAPI 听写）
//!
//! 为什么走子进程而不是 sapi-lite：
//! - System.Speech API 确定（`SetInputToWaveFile` 即离线文件识别，dictation grammar 一行）
//! - 零第三方依赖、零额外构建要求（PowerShell Windows 自带）
//! - sapi-lite 的 dictation 支持待验证，后续可替换为库内调用
//!
//! 已知限制：中文听写质量一般、无热词——M0 先用它跑通链路（用户指定），
//! 术语纠错交给上层 LLM 词表纠错层。

use super::SttEngine;
use anyhow::{Context, Result};

pub struct WindowsPsEngine {
    timeout_secs: u32,
}

impl WindowsPsEngine {
    pub fn new() -> Self {
        Self { timeout_secs: 10 }
    }
}

impl Default for WindowsPsEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl SttEngine for WindowsPsEngine {
    fn name(&self) -> &'static str {
        "windows-native"
    }

    fn transcribe(&mut self, pcm: &[i16], _hotwords: &[&str]) -> Result<String> {
        // System.Speech 只吃 WAV 文件：把 PCM 写临时 WAV（16k/16bit/mono）
        let stamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_millis();
        let wav_path = std::env::temp_dir().join("boss-stt-debug.wav");
        let ps1_path = std::env::temp_dir().join(format!("boss-stt-{stamp}.ps1"));
        let _ = stamp;
        write_wav(&wav_path, pcm)?;

        // 走临时 .ps1 + -File（UTF-8 BOM）：-Command 内嵌模式实测识别为空，
        // -File 模式与手工诊断路径完全一致，可复现。
        let script = format!(
            r#"param([string]$WavPath)
Add-Type -AssemblyName System.Speech
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$rec = New-Object System.Speech.Recognition.SpeechRecognitionEngine([System.Globalization.CultureInfo]::GetCultureInfo('zh-CN'))
$rec.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
$rec.SetInputToWaveFile($WavPath)
$texts = @()
while ($true) {{
    $r = $rec.Recognize([TimeSpan]::FromSeconds({}))
    if (-not $r) {{ break }}
    $texts += $r.Text
}}
Write-Output ($texts -join '')
"#,
            self.timeout_secs / 2
        );
        // UTF-8 BOM：Windows PowerShell 5.1 无 BOM 会按 ANSI 解析中文
        let mut bytes = vec![0xEF, 0xBB, 0xBF];
        bytes.extend_from_slice(script.as_bytes());
        std::fs::write(&ps1_path, bytes).context("写临时 .ps1 失败")?;

        let wav_str = wav_path.to_str().unwrap_or_default();
        // LOCALAPPDATA 重定向：SAPI 会写 %LOCALAPPDATA%\Microsoft\Speech\Files\MSASR\*.dat
        // 适配缓存，沙箱/受限环境下该写会被拦截，识别静默返回空。重定向到临时目录绕开。
        let fake_local = std::env::temp_dir().join(format!("boss-stt-sapi-{stamp}"));
        std::fs::create_dir_all(&fake_local).context("创建 SAPI 缓存目录失败")?;
        let output = std::process::Command::new("powershell")
            .env("LOCALAPPDATA", &fake_local)
            .args([
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                ps1_path.to_str().unwrap_or_default(),
                wav_str,
            ])
            .output()
            .context("启动 PowerShell 失败")?;

        let _ = std::fs::remove_file(&ps1_path); // 调试：保留 WAV 供 diag 复测

        if !output.status.success() {
            anyhow::bail!(
                "PowerShell 识别失败（exit {}）：{}",
                output.status.code().unwrap_or(-1),
                String::from_utf8_lossy(&output.stderr)
            );
        }
        Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
    }
}

/// 写 16k/16bit/mono WAV
///
/// 手写头部而非 hound：SAPI 的 SetInputToWaveFile 只认 WAVEFORMATEX
/// （fmt chunk 18 字节、含 cbSize=0），hound 写的 16 字节裸 PCM fmt 会被
/// 静默拒绝（识别返回空），实测坑，勿改回 hound。
fn write_wav(path: &std::path::Path, pcm: &[i16]) -> Result<()> {
    use std::io::Write;

    const SAMPLE_RATE: u32 = 16_000;
    let data_len = (pcm.len() * 2) as u32;

    let mut f = std::fs::File::create(path)
        .with_context(|| format!("创建临时 WAV 失败: {}", path.display()))?;
    let mut w = std::io::BufWriter::new(&mut f);

    // RIFF 头：size = 文件大小 - 8 = 4(WAVE) + 8+18(fmt) + 8+data
    w.write_all(b"RIFF")?;
    w.write_all(&(38 + data_len).to_le_bytes())?;
    w.write_all(b"WAVE")?;

    // fmt chunk（WAVEFORMATEX：18 字节 + cbSize=0）
    w.write_all(b"fmt ")?;
    w.write_all(&18u32.to_le_bytes())?;
    w.write_all(&1u16.to_le_bytes())?; // PCM
    w.write_all(&1u16.to_le_bytes())?; // mono
    w.write_all(&SAMPLE_RATE.to_le_bytes())?;
    w.write_all(&(SAMPLE_RATE * 2).to_le_bytes())?; // byte rate
    w.write_all(&2u16.to_le_bytes())?; // block align
    w.write_all(&16u16.to_le_bytes())?; // bits per sample
    w.write_all(&0u16.to_le_bytes())?; // cbSize

    // data chunk
    w.write_all(b"data")?;
    w.write_all(&data_len.to_le_bytes())?;
    for &s in pcm {
        w.write_all(&s.to_le_bytes())?;
    }
    w.flush()?;
    Ok(())
}
