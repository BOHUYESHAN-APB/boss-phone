"""L2 协议黄金向量测试（DESIGN_TEST 协议一致性门禁）。

protocol/vectors/golden.json 是四端共同的字节级基准：
- encode 方向：hub 的 encode_control/encode_media 必须编出与 wire_hex 相同的字节；
- decode 方向：FrameParser 必须从 wire_hex 解回 envelope（字节级往返，非宽松等价）；
- 向量自身必须通过 protocol/schema 的 JSON Schema 校验（防止向量烂掉）。

Rust 端等价校验见 protocol/rust/tests/vectors.rs（语义级 roundtrip）。
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from hub.gateway.framing import FrameParser, encode_control, encode_media

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = json.loads((ROOT / "protocol" / "vectors" / "golden.json").read_text(encoding="utf-8"))

_TYPE_NAMES = {1: "voice", 2: "audio", 3: "file-data", 4: "file-meta"}


@pytest.fixture(scope="module")
def schema_validator():
    cache: dict[str, Draft7Validator] = {}

    def get(name: str) -> Draft7Validator:
        if name not in cache:
            s = json.loads(
                (ROOT / "protocol" / "schema" / f"{name}.json").read_text(encoding="utf-8")
            )
            cache[name] = Draft7Validator(s)
        return cache[name]

    return get


@pytest.mark.parametrize("vec", GOLDEN["control"], ids=lambda v: v["name"])
def test_control_encode_matches_golden_bytes(vec):
    """encode 方向：hub 编码字节必须与黄金向量逐字节一致。"""
    assert encode_control(vec["envelope"]) == bytes.fromhex(vec["wire_hex"])


@pytest.mark.parametrize("vec", GOLDEN["control"], ids=lambda v: v["name"])
def test_control_decode_roundtrip(vec):
    """decode 方向：wire_hex → FrameParser → 完整还原信封（含 ts/seq）。"""
    out = FrameParser().feed(bytes.fromhex(vec["wire_hex"]))
    assert out == [("control", vec["envelope"])]


@pytest.mark.parametrize("vec", GOLDEN["control"], ids=lambda v: v["name"])
def test_control_payload_valid_against_schema(vec, schema_validator):
    """向量自身合法性：payload 必须通过对应 JSON Schema。"""
    errors = list(schema_validator(vec["schema"]).iter_errors(vec["envelope"]["payload"]))
    assert not errors, "\n".join(e.message for e in errors)


@pytest.mark.parametrize("vec", GOLDEN["media"], ids=lambda v: v["name"])
def test_media_encode_decode_roundtrip(vec):
    """媒体帧：encode_media 字节一致 + FrameParser 还原 type/flags/payload。"""
    payload = bytes.fromhex(vec["payload_hex"])
    wire = bytes.fromhex(vec["wire_hex"])
    assert encode_media(vec["type"], vec["flags"], payload) == wire

    out = FrameParser().feed(wire)
    assert len(out) == 1
    kind, frame = out[0]
    assert kind == "media"
    assert (frame.type, frame.flags, frame.payload) == (vec["type"], vec["flags"], payload)
    assert frame.type_name == _TYPE_NAMES[vec["type"]]


@pytest.mark.parametrize("vec", GOLDEN["stream"], ids=lambda v: v["name"])
def test_mixed_stream_framing(vec):
    """混排流：控制帧与媒体帧在同一 CDC 字节流上按序分帧。"""
    out = FrameParser().feed(bytes.fromhex(vec["wire_hex"]))
    got = []
    for kind, obj in out:
        if kind == "control":
            got.append(f"control:{obj['type']}")
        else:
            got.append(f"media:{obj.type_name}")
    assert got == vec["expect"]
