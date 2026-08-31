//! hub-lite：M0 语音链路验证工具（DESIGN_OVERVIEW §8.4 任务 1）
//!
//! WAV 文件 → 16k PCM → STT 引擎（可切换）→ 终端打印文本。
//! 板子到货后，输入源换成串口 PCM（Python hub 正式网关），本工具保留作引擎评测对比。
//!
//! 用法：
//!   cargo run -p stt-validate --bin hub-lite -- <样本.wav> [--engine windows|whisper|cloud]
//!                                                [--model <ggml模型路径>] [--hotwords 词1,词2]

use anyhow::{Context, Result};
use std::path::PathBuf;
use std::time::Instant;

fn main() -> Result<()> {
    let mut wav: Option<PathBuf> = None;
    let mut engine = "windows".to_string();
    let mut model: Option<PathBuf> = None;
    let mut hotwords: Vec<String> = Vec::new();

    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--engine" => engine = args.next().context("--engine 需要值")?,
            "--model" => model = Some(PathBuf::from(args.next().context("--model 需要值")?)),
            "--hotwords" => {
                let v = args.next().context("--hotwords 需要值（逗号分隔）")?;
                hotwords = v.split(',').map(|s| s.trim().to_string()).collect();
            }
            _ if wav.is_none() => wav = Some(PathBuf::from(&arg)),
            _ => anyhow::bail!("多余参数: {arg}"),
        }
    }

    let wav = wav.context("用法: hub-lite <样本.wav> [--engine windows|whisper|cloud] [--model <路径>] [--hotwords 词1,词2]")?;

    println!("== BOSS PHONE hub-lite（M0 语音链路验证）==");
    println!("WAV     : {}", wav.display());
    println!("引擎    : {engine}");
    if !hotwords.is_empty() {
        println!("热词    : {}", hotwords.join(" / "));
    }

    // 1. 加载并校验音频（板端格式契约：16k/16bit/mono）
    let pcm = stt_validate::audio::load_pcm_mono_16k(&wav)?;
    let secs = pcm.len() as f64 / stt_validate::audio::SAMPLE_RATE as f64;
    println!("音频    : {:.1}s / {} 样本", secs, pcm.len());

    // 2. 构建引擎并转写
    let kind = stt_validate::stt::EngineKind::from_str(&engine)?;
    let mut stt = stt_validate::stt::create(kind, model.as_deref())?;
    let hw: Vec<&str> = hotwords.iter().map(|s| s.as_str()).collect();

    println!("转写中  : {}", stt.name());
    let t0 = Instant::now();
    let text = stt.transcribe(&pcm, &hw)?;
    let dt = t0.elapsed();

    // 3. 输出（M0 出口标准：终端打出正确文本）
    println!("----------------------------------------");
    println!("耗时    : {:.2}s", dt.as_secs_f64());
    println!("转写结果:");
    println!("{}", if text.is_empty() { "（空）" } else { &text });
    println!("----------------------------------------");
    Ok(())
}
