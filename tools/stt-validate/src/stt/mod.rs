//! STT 可插拔引擎层（DESIGN_OVERVIEW §8.2）
//!
//! 三引擎全部实装，配置切换；统一输入为 16kHz/16bit/mono PCM。
//! 专业术语（BWA/hg38/仓库名等）靠上层 LLM 词表纠错（§8.3），
//! 引擎侧的 hotwords 参数仅在引擎原生支持热词时注入（如 whisper initial_prompt）。

pub mod cloud;
pub mod windows_ps;
#[cfg(feature = "stt-whisper")]
pub mod whisper_local;

use anyhow::{bail, Result};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EngineKind {
    /// Windows 自带（System.Speech，PowerShell 子进程，零依赖）
    WindowsNative,
    /// whisper.cpp 本地（feature stt-whisper；需模型文件 + cmake 构建）
    WhisperLocal,
    /// 云 API（M0 暂为 stub）
    CloudApi,
}

impl EngineKind {
    pub fn from_str(s: &str) -> Result<Self> {
        match s.to_ascii_lowercase().as_str() {
            "windows" | "windows-native" => Ok(Self::WindowsNative),
            "whisper" | "whisper-local" => Ok(Self::WhisperLocal),
            "cloud" | "cloud-api" => Ok(Self::CloudApi),
            _ => bail!("未知引擎: {s}（可选：windows | whisper | cloud）"),
        }
    }

    pub fn name(&self) -> &'static str {
        match self {
            Self::WindowsNative => "windows-native",
            Self::WhisperLocal => "whisper-local",
            Self::CloudApi => "cloud-api",
        }
    }
}

/// 16kHz/16bit/mono PCM → 文本
///
/// `hotwords`：词表纠错提示（引擎支持则注入；不支持则由上层 LLM 纠错层兜底）
pub trait SttEngine {
    fn name(&self) -> &'static str;

    fn transcribe(&mut self, pcm: &[i16], hotwords: &[&str]) -> Result<String>;
}

/// 引擎工厂
pub fn create(kind: EngineKind, model_path: Option<&std::path::Path>) -> Result<Box<dyn SttEngine>> {
    match kind {
        EngineKind::WindowsNative => Ok(Box::new(windows_ps::WindowsPsEngine::new())),
        EngineKind::WhisperLocal => {
            #[cfg(feature = "stt-whisper")]
            {
                let path = model_path
                    .ok_or_else(|| anyhow::anyhow!("whisper 引擎需要 --model <ggml模型路径>"))?;
                Ok(Box::new(whisper_local::WhisperEngine::new(path)?))
            }
            #[cfg(not(feature = "stt-whisper"))]
            {
                let _ = model_path;
                bail!("whisper 引擎未编译：请用 --features stt-whisper 构建（需 cmake + C++ 编译器）")
            }
        }
        EngineKind::CloudApi => Ok(Box::new(cloud::CloudEngine::new())),
    }
}
