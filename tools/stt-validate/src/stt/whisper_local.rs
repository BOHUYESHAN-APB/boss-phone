//! whisper-local 引擎：whisper.cpp（whisper-rs 0.16 绑定）
//!
//! 构建要求：`--features stt-whisper`（whisper.cpp 从源码编译，需 cmake + C++ 编译器）
//! 模型：ggml 格式（中文推荐 small/medium，放 hub/models/，已 gitignore）
//! 下载：https://huggingface.co/ggerganov/whisper.cpp（ggml-*.bin）

use super::SttEngine;
use anyhow::{Context, Result};
use whisper_rs::{FullParams, SamplingStrategy, WhisperContext, WhisperContextParameters};

pub struct WhisperEngine {
    ctx: WhisperContext,
}

impl WhisperEngine {
    pub fn new(model_path: &std::path::Path) -> Result<Self> {
        let ctx = WhisperContext::new_with_params(
            model_path.to_str().context("模型路径非 UTF-8")?,
            WhisperContextParameters::default(),
        )
        .with_context(|| format!("加载 whisper 模型失败: {}", model_path.display()))?;
        Ok(Self { ctx })
    }
}

impl SttEngine for WhisperEngine {
    fn name(&self) -> &'static str {
        "whisper-local"
    }

    fn transcribe(&mut self, pcm: &[i16], hotwords: &[&str]) -> Result<String> {
        let samples = crate::audio::pcm_to_f32(pcm);

        let mut params = FullParams::new(SamplingStrategy::Greedy { best_of: 1 });
        params.set_language(Some("zh"));
        // 热词注入：initial_prompt 引导模型偏向词表（whisper 原生支持的纠错手段）
        if !hotwords.is_empty() {
            params.set_initial_prompt(&hotwords.join("，"));
        }

        let mut state = self
            .ctx
            .create_state()
            .context("创建 whisper state 失败")?;
        state
            .full(params, &samples)
            .context("whisper 推理失败")?;

        let mut text = String::new();
        for segment in state.as_iter() {
            text.push_str(&format!("{segment}"));
        }
        Ok(text.trim().to_string())
    }
}
