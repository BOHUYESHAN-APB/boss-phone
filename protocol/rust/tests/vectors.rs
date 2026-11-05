//! L2 协议黄金向量测试（DESIGN_TEST 协议一致性门禁，Rust 端）。
//!
//! 基准文件 protocol/vectors/golden.json 由 tools/gen-protocol/vectors.py 生成：
//! Python 端做字节级比对（encode_control 与 wire_hex 逐字节一致），
//! Rust 端做语义级比对——信封 JSON 必须能无损往返 Envelope 结构
//! （反序列化 → 再序列化 → 语义相等），保证 schema 演进后两端
//! 结构声明不漂移。C/Kotlin 端编解码落地后接入同一基准。

use boss_protocol::Envelope;
use serde_json::Value;

const GOLDEN: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../../protocol/vectors/golden.json");

fn golden() -> Value {
    let raw = std::fs::read_to_string(GOLDEN).expect("读取 golden.json");
    serde_json::from_str(&raw).expect("解析 golden.json")
}

fn control_vectors() -> Vec<Value> {
    golden()["control"]
        .as_array()
        .expect("control 数组")
        .clone()
}

#[test]
fn envelope_roundtrip_all_control_vectors() {
    for vec in control_vectors() {
        let name = vec["name"].as_str().unwrap();
        let envelope = &vec["envelope"];

        // 信封 JSON → Envelope（字段/枚举/嵌套结构任一漂移都会在此失败）
        let wire_json = serde_json::to_string(envelope).expect("序列化信封");
        let parsed: Envelope = serde_json::from_str(&wire_json)
            .unwrap_or_else(|e| panic!("[{name}] 信封解码失败: {e}"));

        // Envelope → JSON → 语义等价（键序无关，None 字段不出现）
        let back: Value =
            serde_json::from_str(&serde_json::to_string(&parsed).expect("回编码")).unwrap();
        assert_eq!(back, *envelope, "[{name}] 往返后语义不一致");
    }
}

#[test]
fn type_name_matches_envelope_type_field() {
    for vec in control_vectors() {
        let name = vec["name"].as_str().unwrap();
        let envelope = &vec["envelope"];
        let parsed: Envelope =
            serde_json::from_value(envelope.clone()).unwrap_or_else(|e| panic!("[{name}] {e}"));
        let expect = envelope["type"].as_str().unwrap();
        assert_eq!(parsed.message.type_name(), expect, "[{name}] type 不匹配");
    }
}

#[test]
fn media_vector_wire_layout() {
    // 媒体帧字节布局：AA55 | TYPE | FLAGS | LEN(大端 u16) | PAYLOAD
    // （与 hub.gateway.framing.encode_media 同一规格；Rust 传输层落地时以本布局实现）
    for vec in golden()["media"].as_array().expect("media 数组") {
        let name = vec["name"].as_str().unwrap();
        let wire = hex_decode(vec["wire_hex"].as_str().unwrap());
        assert_eq!(&wire[0..2], &[0xAA, 0x55], "[{name}] magic");
        assert_eq!(wire[2], vec["type"].as_u64().unwrap() as u8, "[{name}] type");
        assert_eq!(wire[3], vec["flags"].as_u64().unwrap() as u8, "[{name}] flags");
        let len = u16::from_be_bytes([wire[4], wire[5]]) as usize;
        let payload_hex = vec["payload_hex"].as_str().unwrap();
        assert_eq!(
            len,
            payload_hex.len() / 2,
            "[{name}] LEN 与载荷长度不一致"
        );
        assert_eq!(wire.len(), 6 + len, "[{name}] 总长");
    }
}

/// 十六进制解码（避免只为测试引 hex crate）
fn hex_decode(s: &str) -> Vec<u8> {
    assert!(s.len() % 2 == 0);
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).expect("合法 hex"))
        .collect()
}
