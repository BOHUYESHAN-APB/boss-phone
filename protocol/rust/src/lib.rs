//! boss-protocol：BOSS PHONE 通讯协议 Rust 端（hub 与固件业务层共用）
//!
//! 分层（DESIGN_OVERVIEW §6 / DESIGN_PROTOCOL）：
//! - [`messages`]：九条消息的结构声明，由 `tools/gen-protocol` 从 `protocol/schema/*.json`
//!   生成（SSOT），禁止手改；
//! - 本文件：手写的信封与消息路由——所有消息套同一信封（type/from/to/seq/ts/payload），
//!   与链路无关；帧封装（JSON 行 / 媒体二进制帧）在传输层实现。
//!
//! 兼容原则（DESIGN_PROTOCOL §1）：未知字段一律忽略（serde 默认行为）；
//! 可选字段新增后旧端不携带也能解码（`#[serde(default)]`）。

pub mod messages;

pub use messages::*;

use serde::{Deserialize, Serialize};

/// 信封内的具体消息（tag = `type` 字段，content = `payload` 字段）
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", content = "payload", rename_all = "snake_case")]
pub enum Message {
    Hello(Hello),
    HelloAck(HelloAck),
    Presence(Presence),
    State(State),
    Ask(Ask),
    Answer(Answer),
    Ring(Ring),
    RingAck(RingAck),
    Hangup(Hangup),
}

impl Message {
    /// 消息类型名（信封 `type` 字段的值）
    pub fn type_name(&self) -> &'static str {
        match self {
            Self::Hello(_) => "hello",
            Self::HelloAck(_) => "hello_ack",
            Self::Presence(_) => "presence",
            Self::State(_) => "state",
            Self::Ask(_) => "ask",
            Self::Answer(_) => "answer",
            Self::Ring(_) => "ring",
            Self::RingAck(_) => "ring_ack",
            Self::Hangup(_) => "hangup",
        }
    }
}

/// 统一信封（DESIGN_PROTOCOL §2）
///
/// 媒体帧（voice/audio/file 数据段）不套本信封，走二进制帧（传输层职责）。
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Envelope {
    #[serde(flatten)]
    pub message: Message,
    /// 发送方 ID：`agent:<repo>` / `hub` / `operator` / `device` / `android-app`
    pub from: String,
    /// 接收方：`device` / `operator` / `agent:<repo>` / `all`
    pub to: String,
    /// 控制消息必填；媒体帧不适用。发送方本地递增，对端据此去重补收
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub seq: Option<u32>,
    /// 毫秒时间戳（发送时本地时钟，仅展示）
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub ts: Option<u64>,
}

/// 协议当前版本（hello.proto 的取值）
pub const PROTO_VERSION: u32 = 1;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn envelope_roundtrip_state() {
        let json = r#"{"type":"state","from":"agent:repo-b","to":"device","seq":42,"ts":1756000000000,"payload":{"agent_id":"repo-b","state":"running","summary":"跑测试中","since":1756000000000}}"#;
        let env: Envelope = serde_json::from_str(json).expect("解码 state 信封");
        assert_eq!(env.from, "agent:repo-b");
        assert_eq!(env.seq, Some(42));
        let Message::State(st) = &env.message else {
            panic!("应解码为 State");
        };
        assert_eq!(st.state, AgentState::Running);
        assert_eq!(st.task, None); // 可选字段缺省

        let out = serde_json::to_string(&env).expect("回编码");
        assert!(out.contains(r#""type":"state""#), "type 保留: {out}");
        assert!(out.contains(r#""payload""#), "payload 嵌套: {out}");
        assert!(!out.contains("task"), "None 字段不序列化: {out}");
    }

    #[test]
    fn envelope_roundtrip_ask_with_questions() {
        let json = r#"{"type":"ask","from":"agent:repo-b","to":"device","seq":7,"payload":{"ask_id":"u-1","agent_id":"repo-b","reason":"需要写权限","questions":[{"q_no":1,"kind":"single","prompt":"允许写入 src/ 吗？","options":["允许","拒绝"],"optional":false},{"q_no":2,"kind":"input","prompt":"备注","options":[],"optional":true,"default":"无"}]}}"#;
        let env: Envelope = serde_json::from_str(json).expect("解码 ask 信封");
        let Message::Ask(ask) = &env.message else {
            panic!("应解码为 Ask");
        };
        assert_eq!(ask.questions.len(), 2);
        assert_eq!(ask.questions[0].kind, QuestionKind::Single);
        assert_eq!(ask.questions[1].r#default.as_deref(), Some("无"));

        let back: Envelope = serde_json::from_str(&serde_json::to_string(&env).unwrap()).unwrap();
        assert_eq!(back, env);
    }

    #[test]
    fn hello_optional_resume_seq() {
        let json = r#"{"type":"hello","from":"device","to":"hub","payload":{"proto":1,"device":"passport:AA:BB","fw":"0.1.0","caps":["proto.v1","audio.pcm"]}}"#;
        let env: Envelope = serde_json::from_str(json).expect("无 resume_seq 的 hello 可解码");
        let Message::Hello(h) = &env.message else { panic!() };
        assert_eq!(h.resume_seq, None);

        let json2 = r#"{"type":"hello","from":"device","to":"hub","payload":{"proto":1,"device":"passport:AA:BB","fw":"0.1.0","caps":[],"resume_seq":99}}"#;
        let env2: Envelope = serde_json::from_str(json2).expect("带 resume_seq 的 hello 可解码");
        let Message::Hello(h2) = &env2.message else { panic!() };
        assert_eq!(h2.resume_seq, Some(99));
    }

    #[test]
    fn ring_enum_values() {
        let json = r#"{"type":"ring","from":"hub","to":"device","payload":{"ring_id":"r-1","agent_id":"repo-b","kind":"red_alert","reason":"CI 失败","summary":"clippy 报错 3 处"}}"#;
        let env: Envelope = serde_json::from_str(json).expect("解码 ring");
        let Message::Ring(r) = &env.message else { panic!() };
        assert_eq!(r.kind, RingKind::RedAlert);
        assert_eq!(r.ringtone, None);
    }

    #[test]
    fn unknown_fields_ignored() {
        // 只增不改：新增字段不破坏旧端解码
        let json = r#"{"type":"ring_ack","from":"device","to":"hub","payload":{"ring_id":"r-1","accept":true,"future_field":123}}"#;
        let env: Envelope = serde_json::from_str(json).expect("未知字段应被忽略");
        let Message::RingAck(ra) = &env.message else { panic!() };
        assert!(ra.accept);
    }

    #[test]
    fn unknown_message_type_rejected() {
        let json = r#"{"type":"no_such","from":"x","to":"y","payload":{}}"#;
        let err = serde_json::from_str::<Envelope>(json).unwrap_err();
        assert!(err.to_string().contains("unknown variant"), "{err}");
    }
}
