//! BOSS PHONE M0 STT 验证工具（stt-validate）
//!
//! 三引擎可插拔 STT + hub-lite 语音链路验证（WAV → PCM → 文本）。
//! 生产 STT 在 Python hub（faster-whisper 等），本 crate 保留作引擎评测与对比基线。

pub mod audio;
pub mod stt;
