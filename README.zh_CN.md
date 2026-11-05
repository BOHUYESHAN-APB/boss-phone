# BOSS PHONE (English)

> 中文版 / Chinese version: [README.md](README.md)

An AI command terminal for non-technical decision makers: a small ESP32-C3 "dumb terminal" plus a PC-side hub. Voice commands go through the hub to local AI agents (claude-code / codex / opencode, etc.), and agent status, permission requests and key results come back to the device screen.

The repository is currently **PC-side runnable, with the device firmware entry point not yet created**. This README states only facts that can be pointed at a file or reproduced with a command.

## Current status

### Done (each item maps to a file and a command)

| Area | Content | Evidence |
|---|---|---|
| Protocol SSOT | JSON Schema for 9 messages + generated bindings for C / Rust / Kotlin / Python | `protocol/schema/` (9 `.json` files), `protocol/{c,rust,kotlin,python}/`; `node tools/gen-protocol/generate.mjs --check` prints `OK` for all four targets |
| Golden vectors | 14 control frames + 5 media frames + 1 mixed stream, shared byte-level baseline | `protocol/vectors/golden.json`; `python tools/gen-protocol/vectors.py --check` passes |
| Hub gateway & core | CDC serial / WebSocket gateways, framing, device sessions, route decisions, event bus | `hub/hub/gateway/{cdc,ws,framing,handler}.py`, `hub/hub/core/{session,router,eventbus}.py` |
| Hub voice-input path | Three pluggable STT engines (windows / whisper / cloud) + vocabulary correction + Windows cursor injection | `hub/hub/operator/{stt,correct,provider}.py`, `hub/hub/input/inject.py`, `hub/hub/dictation.py`; `python hub-lite.py --selftest` → `✓ 前台窗口` / `✓ SendInput API 可用`, exit 0 |
| Hub automated tests | 7 test files, 71 cases, all green (~2 s) | `cd hub && python -m pytest tests -q` → `71 passed` |
| Style gate | ruff lint + format clean (config in `hub/pyproject.toml`; `ruff` comes with `requirements-dev.txt`) | `cd hub && ruff check hub tests && ruff format --check hub tests` → `All checks passed!` |
| CI | `protocol` / `hub` / `firmware` jobs | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |

### In progress

| Item | State |
|---|---|
| windows-native STT accuracy evaluation | Scripts and samples are in `tools/stt-samples/`; `eval-windows.ps1` must run in a normal user terminal — SAPI writes its adaptation cache to `%LOCALAPPDATA%\Microsoft\Speech`, and in restricted environments recognition returns empty |
| Hub ↔ real board CDC integration | Hub-side listener is implemented (`hub/hub/gateway/cdc.py`); no hardware available to verify |

### Not started

| Item | Note |
|---|---|
| `firmware/main/` (LVGL UI thin layer + boss_app) | `firmware/` only contains the shared hardware layer `components/bsp/`; there is **no `main/`, no `app_main`**, so it does not produce flashable firmware. This is M1 work (see [DESIGN_FIRMWARE](docs/BOSS_PHONE_DESIGN_FIRMWARE.md)) |
| `plugins/` (CLI plugin bridge) | Directory does not exist yet; design in [DESIGN_PLUGIN](docs/BOSS_PHONE_DESIGN_PLUGIN.md) |
| Android app | Directory does not exist yet; design in [DESIGN_ANDROID](docs/BOSS_PHONE_DESIGN_ANDROID.md) |

### Known limitations

- The ESP32-C3 has **no PSRAM**: LVGL buffers and audio buffers both consume internal RAM. Check `firmware/sdkconfig.defaults` and the memory constraints in `docs/AI_HARDWARE_DEVELOPMENT_GUIDE.md` before changing them.
- `windows-native` STT and cursor injection are **Windows-only**; the Linux CI runner does not exercise those paths.
- Protocol schemas and the four generated bindings must be committed together, or the CI `protocol` job fails.

## Architecture

```
┌──────────────┐   voice/keys   ┌────────────────┐  local/LAN   ┌──────────────┐
│ Device        │ ◄────────────► │ PC hub          │ ◄──────────► │ CLI plugin   │
│ (dumb term.)  │  USB CDC/WS    │ Python+asyncio  │              │ bridge       │
│ ESP32-C3      │                │ STT/correct/    │              │ (not yet     │
│ LVGL thin UI  │                │ inject          │              │ implemented) │
└──────────────┘                └────────────────┘              └──────────────┘
      ▲ status / Q&A / incoming call   │ Android app (rich terminal, not implemented)
      └──────────────────────────────────┘
```

- **Device = dumb terminal**: records audio (16 kHz / 16-bit / mono PCM), handles keys, renders whatever the hub sends. No AI on the board.
- **Hub = the switchboard**: voice input method (STT + vocabulary correction → text typed at the current cursor), agent status forwarding, offline routing; Python + asyncio.
- **Plugin bridge = per-CLI adapters**: convert agent events into protocol messages (designed, not implemented).
- **Protocol = single source of truth**: change a message only in `protocol/schema/`; the generator produces all four bindings.

## Repository layout

| Path | Actual content and status |
|---|---|
| [`firmware/`](firmware/) | ESP-IDF project shell: `CMakeLists.txt`, `sdkconfig.defaults` (target esp32c3 / 8 MB flash / USB-Serial-JTAG console / LVGL 16-bit), `components/bsp/` (6 headers + 6 `.c` files: display, button, audio, battery, shared I2C; pin source of truth in `bsp_pins.h`). **No `main/`** |
| [`reference/folotoy-card-demo/`](reference/folotoy-card-demo/) | Upstream FoloToy-Card baseline demo: `main/` (`main.c` + four hardware demo pages + `demo.h` + pixel UI library), `tests/test_ui_pixel_math.c`, `CMakeLists.txt`, `sdkconfig.defaults`. Reuses `firmware/components/bsp`; read-only reference; **the only buildable firmware project today** |
| [`hub/`](hub/) | PC hub (Python 3.11+, asyncio): entry points `hub-lite.py` and `python -m hub` (subcommands `serve` / `link` / `telemetry` / `sim`; `link` and `sim` are placeholders today); package `hub/hub/` (`audio`, `cli`, `config`, `dictation`, `server`, `telemetry` + `gateway/`, `core/`, `operator/`, `input/`); `tests/` with 7 files / 71 cases |
| [`protocol/`](protocol/) | Protocol SSOT: `schema/` with 9 messages; `vectors/golden.json`; generated bindings in `c/`, `rust/`, `kotlin/`, `python/` (generator in `tools/gen-protocol/`) |
| [`tools/`](tools/) | `gen-protocol/` (`generate.mjs` four-target generator + `vectors.py` golden vectors), `stt-samples/` (SAPI sample generation and evaluation scripts), `stt-validate/` (Rust STT evaluation tool), `pdf-export/` (Node, exports the doc set to PDF) |
| [`docs/`](docs/) | 12 design documents (11 `BOSS_PHONE_*.md` + the upstream `AI_HARDWARE_DEVELOPMENT_GUIDE.md`) + [`docs/pdf/BOSS_PHONE_设计文档集.pdf`](docs/pdf/BOSS_PHONE_设计文档集.pdf) |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | Three CI jobs (see below) |

## Quick start

### Hub (Windows, Python 3.11+)

Run these from `hub/` — `hub` is a local package, so `python -m hub` from the repository root fails.

```bash
cd hub
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

python -m pytest tests -q        # 71 passed
python -m compileall -q hub tests
ruff check hub tests             # ruff is installed via requirements-dev.txt
ruff format --check hub tests
python -m hub telemetry          # print one CPU/memory snapshot
python -m hub serve              # resident process; WS-only mode when no serial port is configured; Ctrl+C to stop
```

Voice path and voice input method (WAV → PCM → STT → vocabulary correction → optional cursor injection):

```bash
cd hub
python hub-lite.py ..\tools\stt-samples\out\01-daily.wav --engine windows   # transcribe + correct
python hub-lite.py --selftest                                             # check injection capability only; types nothing
python hub-lite.py ..\tools\stt-samples\out\02-bio-bwa.wav --engine windows --type   # type corrected text at the cursor
```

`--engine` accepts `windows` (zero dependencies, mediocre quality), `whisper` (needs `pip install "faster-whisper>=1.0"` and a model file), or `cloud` (a stub in M0). `--no-correct` disables the vocabulary layer so its gain can be measured. `tools/stt-samples/out/` is gitignored, so a fresh clone must first generate the samples from a normal terminal with `powershell -ExecutionPolicy Bypass -File tools/stt-samples/gen-samples.ps1` (SAPI TTS; a Chinese voice pack is required). Both `hub-lite.py` and the `python -m hub` entry point reconfigure their stdout/stderr to UTF-8, so Chinese text and `✓` do not raise `UnicodeEncodeError` under a GBK console. The pipeline runs end to end, but the `windows` engine can return an empty transcript in a restricted terminal (SAPI cannot write its adaptation cache — see the first "In progress" row); switch to `whisper` or run it from your own terminal. `--type` requires an editing window to be focused first.

### Protocol checks (from the repository root)

```bash
node tools/gen-protocol/generate.mjs --check    # generated bindings in sync with schemas (9 messages / 2 nested structs / 4 enums)
python tools/gen-protocol/vectors.py --check    # golden-vector wire_hex in sync with envelope definitions
cargo test -p boss-protocol                     # Rust envelope roundtrip + golden-vector semantic checks
```

To change a message: edit `protocol/schema/`, run `node tools/gen-protocol/generate.mjs` to regenerate, add a vector in `tools/gen-protocol/vectors.py`, run `python tools/gen-protocol/vectors.py`, then commit the four bindings together with `golden.json`.

### Firmware

`firmware/` contains only the BSP component and no `main/`, so it **cannot be built into flashable firmware on its own**. The buildable project today is the upstream reference demo (which also reuses `firmware/components/bsp`):

```bash
cd reference/folotoy-card-demo
idf.py set-target esp32c3
idf.py build
idf.py flash monitor
```

Requires ESP-IDF 5.5.x (known environment: 5.5.3). `bsp_pins.h` is the pin map source of truth — change it first when porting to another board revision.

The pixel-UI math can be unit-tested on the host without ESP-IDF:

```bash
cd reference/folotoy-card-demo
mkdir -p build
cc -I main tests/test_ui_pixel_math.c main/ui_pixel_math.c -o build/ui_pixel_math_test
./build/ui_pixel_math_test
```

## Protocol and golden vectors

Nine messages: `hello` / `hello_ack` / `presence` / `state` / `ask` / `answer` / `ring` / `ring_ack` / `hangup`. Every message uses the same envelope `type / from / to / seq / ts / payload`, independent of the transport.

Two frame kinds (`hub/hub/gateway/framing.py`, identical to `protocol/vectors/`):

- control frame: compact UTF-8 JSON + `\n` (`ensure_ascii=False`, separators `,` and `:`);
- media frame: `AA 55 | TYPE(1B) | FLAGS(1B) | LEN(2B big-endian) | PAYLOAD`, with TYPE `01` voice / `02` audio / `03` file-data / `04` file-meta.

`protocol/vectors/golden.json` is the shared byte-level baseline for all four targets: 14 control frames, 5 media frames and 1 mixed CDC stream (`cdc-mixed`, control and media frames interleaved). Python performs byte-exact comparison (`hub/tests/test_protocol_vectors.py`); Rust performs semantic envelope roundtrips (`protocol/rust/tests/vectors.rs`).

## Tests and CI

| Suite | Content | Command | Status |
|---|---|---|---|
| Hub (L1 unit) | Frame parsing, vocabulary correction, dictation orchestration | `cd hub && python -m pytest tests -q` | 71 passed |
| Hub (L3 integration) | Real WS listener; virtual device runs hello → hello_ack → state → disconnect cleanup | same command (`hub/tests/test_integration_ws.py`) | passing |
| Hub (L2 vectors) | Golden-vector byte roundtrip + schema validation | same command (`hub/tests/test_protocol_vectors.py`, 48 cases) | passing |
| Hub (lint) | ruff check + ruff format --check (config in `hub/pyproject.toml`) | `cd hub && ruff check hub tests && ruff format --check hub tests` | passing |
| Rust protocol | Envelope/message structures (6 unit tests) + golden-vector roundtrip (3) | `cargo test -p boss-protocol` | runs in CI |
| Generated artifacts | Four bindings in sync with schemas and vectors | the two `--check` commands above | passing |

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml), on push to `main` and on pull requests) runs three jobs:

| Job | Content |
|---|---|
| `protocol` | `node tools/gen-protocol/generate.mjs --check` + `python tools/gen-protocol/vectors.py --check` + `cargo test -p boss-protocol` |
| `hub` | installs `requirements.txt` + `requirements-dev.txt`, runs `python -m compileall -q hub tests`, `ruff check` + `ruff format --check`, `python -m pytest tests -q` |
| `firmware` | builds `reference/folotoy-card-demo` with `espressif/esp-idf-ci-action@v1` (ESP-IDF v5.5, target esp32c3) |

CI does not cover: on-device acceptance (screen / buttons / audio need manual verification), STT accuracy evaluation (reported, not gated), and the Windows-only windows-native STT and cursor injection paths.

## Documentation

| Document | Content |
|---|---|
| [PRD](docs/BOSS_PHONE_PRD.md) | Product requirements (single source of requirements) |
| [DESIGN_OVERVIEW](docs/BOSS_PHONE_DESIGN_OVERVIEW.md) | Overall technical design: layout, stack, module boundaries, code skeletons |
| [DESIGN_PROTOCOL](docs/BOSS_PHONE_DESIGN_PROTOCOL.md) | Protocol spec: message dictionary, framing, seq/sync, error codes, sequence diagrams |
| [DESIGN_FIRMWARE](docs/BOSS_PHONE_DESIGN_FIRMWARE.md) | Firmware: partition table, task/memory budget, boss_app / boss_transport |
| [DESIGN_HUB](docs/BOSS_PHONE_DESIGN_HUB.md) | PC hub: dual-entry gateway, sessions/routing, event bus, offline queue, telemetry |
| [DESIGN_PLUGIN](docs/BOSS_PHONE_DESIGN_PLUGIN.md) | Plugin bridge: unified AgentAdapter and per-CLI adapters |
| [DESIGN_ANDROID](docs/BOSS_PHONE_DESIGN_ANDROID.md) | Android app: BLE gateway, peer rich terminal, push |
| [DESIGN_DEPLOYMENT](docs/BOSS_PHONE_DESIGN_DEPLOYMENT.md) | Deployment and operations: provisioning, pairing, upgrade, troubleshooting |
| [DESIGN_TEST](docs/BOSS_PHONE_DESIGN_TEST.md) | Testing and acceptance: M1–M4 checklists, on-device matrix, CI layers |
| [DESIGN_SECURITY](docs/BOSS_PHONE_DESIGN_SECURITY.md) | Security: threat model, auth, transport security, privacy |
| [GITHUB_STRATEGY](docs/BOSS_PHONE_GITHUB_STRATEGY.md) | GitHub / Git organization and release strategy |
| [AI_HARDWARE_DEVELOPMENT_GUIDE](docs/AI_HARDWARE_DEVELOPMENT_GUIDE.md) | Upstream hardware guide (board facts, constraints, acceptance) |

All documents can be exported as a single PDF: [`docs/pdf/BOSS_PHONE_设计文档集.pdf`](docs/pdf/BOSS_PHONE_设计文档集.pdf) (export script `tools/pdf-export/export.mjs`).

## Contributing and license

- Environment requirements, where changes belong, and the verification checklist are in [`CONTRIBUTING.md`](CONTRIBUTING.md); repository conventions (directory responsibilities, coding style, commit flow) live in [`AGENTS.md`](AGENTS.md), and automated agents follow that file too.
- Before submitting, at minimum run `cd hub && python -m pytest tests -q`, `ruff check hub tests`, and both protocol `--check` commands. Firmware changes must be verified item by item on real hardware per [DESIGN_TEST](docs/BOSS_PHONE_DESIGN_TEST.md), with the observed results recorded.
- The protocol only grows: add capabilities in a way old peers can ignore, and commit the four generated bindings together.
- Security reporting: [`SECURITY.md`](SECURITY.md); notable changes are tracked in [`CHANGELOG.md`](CHANGELOG.md).

MIT, see [LICENSE](LICENSE) (copyright line retained from upstream FoloToy).
