//! 音频输入：WAV 加载与格式校验
//!
//! 板端约定格式（DESIGN_OVERVIEW §8.1）：16kHz / 16bit / mono PCM，约 32KB/s。
//! M0 用 WAV 文件仿真板子输入；板子到货后换成串口 PCM 流，格式校验复用。

use anyhow::{bail, Context, Result};

pub const SAMPLE_RATE: u32 = 16_000;
pub const CHANNELS: u16 = 1;

/// 读取 WAV 并校验为板端约定格式，返回 PCM 样本
pub fn load_pcm_mono_16k(path: &std::path::Path) -> Result<Vec<i16>> {
    let mut reader = hound::WavReader::open(path)
        .with_context(|| format!("打开 WAV 失败: {}", path.display()))?;
    let spec = reader.spec();

    if spec.sample_rate != SAMPLE_RATE {
        bail!(
            "采样率不符：要求 {} Hz，实际 {} Hz（请重采样后重试）",
            SAMPLE_RATE,
            spec.sample_rate
        );
    }
    if spec.channels != CHANNELS {
        bail!("声道数不符：要求单声道，实际 {} 声道", spec.channels);
    }
    if spec.bits_per_sample != 16 {
        bail!(
            "位深不符：要求 16bit，实际 {} bit",
            spec.bits_per_sample
        );
    }

    let pcm: Vec<i16> = reader
        .samples::<i16>()
        .collect::<std::result::Result<_, _>>()
        .context("解码 PCM 样本失败")?;
    let secs = pcm.len() as f64 / SAMPLE_RATE as f64;
    if secs > 120.0 {
        bail!("音频过长（{:.1}s > 120s），M0 评测样本请控制在 2 分钟内", secs);
    }
    Ok(pcm)
}

/// i16 PCM → f32（[-1.0, 1.0]），whisper 等引擎输入格式
pub fn pcm_to_f32(pcm: &[i16]) -> Vec<f32> {
    pcm.iter().map(|&s| s as f32 / 32768.0).collect()
}
