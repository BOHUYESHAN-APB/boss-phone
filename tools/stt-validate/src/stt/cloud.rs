//! cloud-api 引擎：M0 暂为 stub
//!
//! 待选型实装（DESIGN_OVERVIEW §8.2）：
//! - 字节火山引擎 ASR / 讯飞语音听写 / OpenAI gpt-4o-transcribe
//! - 共同形态：PCM 打包（部分要求 speex/opus 或原始 wav 上传）→ HTTP POST → 解析 JSON
//! - 配置：API key 走环境变量（BOSS_STT_CLOUD_KEY），endpoint 走 hub 配置文件
//!
//! M0 出口不依赖本引擎（windows/whisper 达标即可），M2 按成本与效果决策。

use super::SttEngine;
use anyhow::{bail, Result};

pub struct CloudEngine {
    _private: (),
}

impl CloudEngine {
    pub fn new() -> Self {
        Self { _private: () }
    }
}

impl Default for CloudEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl SttEngine for CloudEngine {
    fn name(&self) -> &'static str {
        "cloud-api"
    }

    fn transcribe(&mut self, _pcm: &[i16], _hotwords: &[&str]) -> Result<String> {
        bail!("cloud-api 引擎尚未实装：待选型（字节火山/讯飞/OpenAI）后接入，M0 请用 windows | whisper")
    }
}
