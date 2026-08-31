#!/usr/bin/env node
// BOSS PHONE 协议代码生成器（DESIGN_OVERVIEW §6：Schema → 四端结构声明）
//
// 用法：
//   node tools/gen-protocol/generate.mjs           # 重新生成四端产物
//   node tools/gen-protocol/generate.mjs --check   # CI 校验：产物是否与 schema 同步
//
// 输入：protocol/schema/*.json（JSON Schema，SSOT）
// 输出：
//   protocol/rust/src/messages.rs         Rust 结构声明（serde，固件业务层用）
//   protocol/kotlin/BossProtocol.kt       Kotlin data class（kotlinx.serialization）
//   protocol/c/boss_protocol.h            C 结构头（固件 UI 薄层 FFI 契约；编解码在 Rust 层）
//   protocol/python/boss_protocol.py      Python dataclass（Hub / 插件桥用）
//
// 约定：生成器只做结构声明；编解码逻辑各端手写（消息少，不引 protobuf 重量）。

import { readdirSync, readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const schemaDir = join(root, "protocol", "schema");
const checkMode = process.argv.includes("--check");

// ---------- 命名工具 ----------

const pascal = (s) => s.split(/[_\s-]+/).map((w) => w[0].toUpperCase() + w.slice(1)).join("");
const camel = (s) => { const p = pascal(s); return p[0].toLowerCase() + p.slice(1); };
const snakeUpper = (s) => s.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toUpperCase();

const RUST_KEYWORDS = new Set(["default", "type", "ref", "fn", "box", "in", "as", "async"]);
const C_KEYWORDS = { default: "default_value", type: "type_", ref: "ref_" };

// ---------- 中间模型 ----------

const messages = []; // { name, desc, fields }
const structs = [];  // { name, desc, fields } 嵌套结构（如 Question）
const enums = [];    // { name, desc, values } 去重后的枚举

/** 字段：{ json, doc, optional, kind, enumRef?, itemKind?, structRef? } */
function fieldOf(jsonName, prop, required) {
    const f = {
        json: jsonName,
        doc: prop.description ?? "",
        optional: !required.includes(jsonName),
        kind: "string",
        enumRef: null,
        itemKind: null,
        structRef: null,
    };
    if (prop.enum) {
        const name = prop["x-enum"];
        if (!name) throw new Error(`${jsonName}: 枚举缺 x-enum 注解`);
        let e = enums.find((x) => x.name === name);
        if (!e) {
            e = { name, desc: prop.description ?? "", values: prop.enum };
            enums.push(e);
        } else if (JSON.stringify(e.values) !== JSON.stringify(prop.enum)) {
            throw new Error(`枚举 ${name} 两处定义不一致`);
        }
        f.kind = "enum";
        f.enumRef = name;
    } else if (prop.type === "array") {
        f.kind = "array";
        const it = prop.items ?? {};
        if (it.enum) {
            const name = it["x-enum"];
            if (!name) throw new Error(`${jsonName}[]: 枚举缺 x-enum 注解`);
            if (!enums.find((x) => x.name === name)) enums.push({ name, desc: it.description ?? "", values: it.enum });
            f.itemKind = { kind: "enum", enumRef: name };
        } else if (it.type === "object") {
            const name = it["x-struct"];
            if (!name) throw new Error(`${jsonName}[]: 嵌套结构缺 x-struct 注解`);
            if (!structs.find((x) => x.name === name)) {
                const req = it.required ?? [];
                const fields = Object.entries(it.properties ?? {}).map(([k, p]) => fieldOf(k, p, req));
                structs.push({ name, desc: it.description ?? "", fields });
            }
            f.itemKind = { kind: "struct", structRef: name };
        } else if (it.type === "integer") {
            f.itemKind = { kind: it.format === "uint64" ? "u64" : "u32" };
        } else if (it.type === "string") {
            f.itemKind = { kind: "string" };
        } else {
            throw new Error(`${jsonName}: 不支持的数组元素类型 ${JSON.stringify(it)}`);
        }
    } else if (prop.type === "integer") {
        f.kind = prop.format === "uint64" ? "u64" : "u32";
    } else if (prop.type === "boolean") {
        f.kind = "bool";
    } else if (prop.type === "string") {
        f.kind = "string";
    } else {
        throw new Error(`${jsonName}: 不支持的类型 ${JSON.stringify(prop)}`);
    }
    return f;
}

// ---------- 读取 schema ----------

const files = readdirSync(schemaDir).filter((f) => f.endsWith(".json")).sort();
for (const file of files) {
    const raw = JSON.parse(readFileSync(join(schemaDir, file), "utf8"));
    const req = raw.required ?? [];
    messages.push({
        name: raw.title,
        desc: raw.description ?? "",
        fields: Object.entries(raw.properties ?? {}).map(([k, p]) => fieldOf(k, p, req)),
    });
}
if (messages.length === 0) throw new Error("未读到任何 schema");

// ---------- Rust 生成 ----------

function rustType(f) {
    if (f.kind === "struct") return f.structRef;
    const base = ({ string: "String", bool: "bool", u32: "u32", u64: "u64" })[f.kind]
        ?? (f.kind === "enum" ? f.enumRef : null);
    if (base !== null) return base;
    if (f.kind === "array") {
        const it = rustType(f.itemKind);
        return `Vec<${it}>`;
    }
    throw new Error(`rustType: ${f.json ?? JSON.stringify(f)}`);
}

function rustField(f) {
    const lines = [];
    if (f.doc) lines.push(`    /// ${f.doc}`);
    let name = f.json;
    if (RUST_KEYWORDS.has(name)) name = `r#${name}`;
    if (f.optional) {
        lines.push(`    #[serde(default, skip_serializing_if = "Option::is_none")]`);
        lines.push(`    pub ${name}: Option<${rustType(f)}>,`);
    } else {
        lines.push(`    pub ${name}: ${rustType(f)},`);
    }
    return lines.join("\n");
}

function genRust() {
    const out = [];
    out.push("// GENERATED by tools/gen-protocol/generate.mjs — DO NOT EDIT");
    out.push(`// Source: protocol/schema/*.json（${messages.length} 条消息 SSOT）`);
    out.push("// 重新生成：node tools/gen-protocol/generate.mjs");
    out.push("#![allow(clippy::all)]");
    out.push("");
    out.push("use serde::{Deserialize, Serialize};");
    out.push("");
    for (const e of enums) {
        if (e.desc) out.push(`/// ${e.desc}`);
        out.push("#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]");
        out.push('#[serde(rename_all = "snake_case")]');
        out.push(`pub enum ${e.name} {`);
        for (const v of e.values) out.push(`    ${pascal(v)},`);
        out.push("}");
        out.push("");
    }
    const allStructs = [...structs, ...messages.map((m) => ({ name: pascal(m.name), desc: m.desc, fields: m.fields }))];
    for (const s of allStructs) {
        if (s.desc) out.push(`/// ${s.desc}`);
        out.push("#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]");
        out.push(`pub struct ${s.name} {`);
        for (const f of s.fields) out.push(rustField(f));
        out.push("}");
        out.push("");
    }
    return out.join("\n");
}

// ---------- Kotlin 生成 ----------

const ktProp = (f) => camel(f.json);
const ktTypeBase = (k, f) => ({ string: "String", bool: "Boolean", u32: "Long", u64: "Long" })[k]
    ?? (k === "enum" ? f.enumRef : null);

function ktType(f) {
    if (f.kind === "struct") return f.structRef;
    const base = ktTypeBase(f.kind, f);
    if (base !== null) return base;
    if (f.kind === "array") return `List<${ktType(f.itemKind)}>`;
    throw new Error(`ktType: ${f.json ?? JSON.stringify(f)}`);
}

function genKotlin() {
    const out = [];
    out.push("// GENERATED by tools/gen-protocol/generate.mjs — DO NOT EDIT");
    out.push(`// Source: protocol/schema/*.json（${messages.length} 条消息 SSOT）`);
    out.push("// 重新生成：node tools/gen-protocol/generate.mjs");
    out.push("// 说明：只含 payload 结构声明；信封与消息路由在 Android 端接入时手写。");
    out.push("package boss.protocol");
    out.push("");
    out.push("import kotlinx.serialization.SerialName");
    out.push("import kotlinx.serialization.Serializable");
    out.push("");
    for (const e of enums) {
        if (e.desc) out.push(`/** ${e.desc} */`);
        out.push("@Serializable");
        out.push(`enum class ${e.name} {`);
        for (const v of e.values) out.push(`    @SerialName("${v}") ${pascal(v)},`);
        out.push("}");
        out.push("");
    }
    const allStructs = [...structs, ...messages.map((m) => ({ name: pascal(m.name), desc: m.desc, fields: m.fields }))];
    for (const s of allStructs) {
        if (s.desc) out.push(`/** ${s.desc} */`);
        out.push("@Serializable");
        out.push(`data class ${s.name}(`);
        const lines = s.fields.map((f) => {
            const head = f.doc ? `    /** ${f.doc} */\n` : "";
            const sn = f.json === ktProp(f) ? "" : `@SerialName("${f.json}") `;
            if (f.optional) return `${head}    ${sn}val ${ktProp(f)}: ${ktType(f)}? = null,`;
            return `${head}    ${sn}val ${ktProp(f)}: ${ktType(f)},`;
        });
        out.push(lines.join("\n").replace(/,$/, ""));
        out.push(")");
        out.push("");
    }
    return out.join("\n");
}

// ---------- C 生成 ----------

const cTypeBase = (k, f) => ({ string: "const char*", bool: "bool", u32: "uint32_t", u64: "uint64_t" })[k]
    ?? (k === "enum" ? `boss_${snakeUpper(f.enumRef).toLowerCase()}_t` : null);

function cType(f) {
    if (f.kind === "struct") return `boss_${snakeUpper(f.structRef).toLowerCase()}_t`;
    const base = cTypeBase(f.kind, f);
    if (base !== null) return base;
    if (f.kind === "array") {
        if (f.itemKind.kind === "struct") return `boss_${snakeUpper(f.itemKind.structRef).toLowerCase()}_list_t`;
        if (f.itemKind.kind === "string") return "boss_str_list_t";
        return "boss_u32_list_t";
    }
    throw new Error(`cType: ${f.json ?? JSON.stringify(f)}`);
}

function cFieldName(f) {
    return C_KEYWORDS[f.json] ?? f.json;
}

function genC() {
    const out = [];
    out.push("/* GENERATED by tools/gen-protocol/generate.mjs — DO NOT EDIT */");
    out.push(`/* Source: protocol/schema 目录（${messages.length} 条消息 SSOT）*/`);
    out.push("/* 重新生成：node tools/gen-protocol/generate.mjs */");
    out.push("/* 定位：固件 UI 薄层的 FFI 契约——字符串与数组均为 Rust 层持有的借用视图，");
    out.push(" * UI 层只读不释放；JSON 编解码全部在 Rust 业务层（boss-protocol crate）。 */");
    out.push("#ifndef BOSS_PROTOCOL_H");
    out.push("#define BOSS_PROTOCOL_H");
    out.push("");
    out.push("#include <stdbool.h>");
    out.push("#include <stddef.h>");
    out.push("#include <stdint.h>");
    out.push("");
    out.push("#ifdef __cplusplus");
    out.push('extern "C" {');
    out.push("#endif");
    out.push("");
    for (const e of enums) {
        const t = `boss_${snakeUpper(e.name).toLowerCase()}_t`;
        out.push(`/* ${e.desc} */`);
        out.push(`typedef enum {`);
        e.values.forEach((v, i) => out.push(`    BOSS_${snakeUpper(e.name)}_${snakeUpper(v)} = ${i},`));
        out.push(`} ${t};`);
        out.push(`const char* ${t.replace(/_t$/, "_name")}(const ${t} v); /* 字符串表（Rust 层实现） */`);
        out.push("");
    }
    out.push("/* 借用视图：items 由 Rust 持有，UI 层只读 */");
    out.push("typedef struct { const char** items; size_t len; } boss_str_list_t;");
    out.push("typedef struct { uint32_t* items; size_t len; } boss_u32_list_t;");
    out.push("");
    // 嵌套结构：先具名 typedef 前向声明，再定义列表视图，最后定义结构体本体
    for (const s of structs) {
        const t = `boss_${snakeUpper(s.name).toLowerCase()}_t`;
        out.push(`typedef struct ${t} ${t};`);
    }
    for (const s of structs) {
        const t = `boss_${snakeUpper(s.name).toLowerCase()}_t`;
        out.push(`typedef struct { ${t}* items; size_t len; } ${t.replace(/_t$/, "_list_t")};`);
    }
    out.push("");
    const allStructs = [...structs, ...messages.map((m) => ({ name: pascal(m.name), desc: m.desc, fields: m.fields }))];
    for (const s of allStructs) {
        const t = `boss_${snakeUpper(s.name).toLowerCase()}_t`;
        out.push(`/* ${s.desc} */`);
        out.push(`typedef struct ${t} {`);
        for (const f of s.fields) {
            const opt = f.optional ? " /* 可选，未带时为 NULL/空 */" : "";
            const d = f.doc ? ` /* ${f.doc} */` : "";
            out.push(`    ${cType(f)} ${cFieldName(f)};${opt || d}`);
        }
        out.push(`} ${t};`);
        out.push("");
    }
    out.push("/* 消息类型（信封 type 字段的合法值，与 Rust Message 枚举一一对应） */");
    out.push("typedef enum {");
    messages.forEach((m, i) => out.push(`    BOSS_MSG_${snakeUpper(m.name)} = ${i},`));
    out.push("    BOSS_MSG_COUNT");
    out.push("} boss_msg_type_t;");
    out.push("");
    out.push("#ifdef __cplusplus");
    out.push("}");
    out.push("#endif");
    out.push("");
    out.push("#endif /* BOSS_PROTOCOL_H */");
    return out.join("\n");
}

// ---------- Python 生成 ----------

const PY_KEYWORDS = new Set([
    "False", "None", "True", "and", "as", "assert", "async", "await", "break", "class", "continue",
    "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in",
    "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield",
]);

const pyType = (f) => {
    if (f.kind === "struct") return f.structRef;
    const base = ({ string: "str", bool: "bool", u32: "int", u64: "int" })[f.kind]
        ?? (f.kind === "enum" ? f.enumRef : null);
    if (base !== null) return base;
    if (f.kind === "array") return `list[${pyType(f.itemKind)}]`;
    throw new Error(`pyType: ${f.json ?? JSON.stringify(f)}`);
};

const pyName = (json) => (PY_KEYWORDS.has(json) ? `${json}_` : json);

function genPython() {
    const out = [];
    out.push('"""GENERATED by tools/gen-protocol/generate.mjs — DO NOT EDIT');
    out.push(`Source: protocol/schema/*.json（${messages.length} 条消息 SSOT）`);
    out.push("重新生成：node tools/gen-protocol/generate.mjs");
    out.push("说明：只含 payload 结构声明（dataclass）；信封与消息路由在 Hub/插件接入时手写。");
    out.push('"""');
    out.push("from __future__ import annotations");
    out.push("");
    out.push("from dataclasses import dataclass");
    out.push("from enum import Enum");
    out.push("from typing import Optional");
    out.push("");
    for (const e of enums) {
        if (e.desc) out.push(`# ${e.desc}`);
        out.push(`class ${e.name}(str, Enum):`);
        for (const v of e.values) out.push(`    ${pyName(v)} = ${JSON.stringify(v)}`);
        out.push("");
    }
    const allStructs = [...structs, ...messages.map((m) => ({ name: pascal(m.name), desc: m.desc, fields: m.fields }))];
    for (const s of allStructs) {
        if (s.desc) out.push(`# ${s.desc}`);
        out.push("@dataclass");
        out.push(`class ${s.name}:`);
        for (const f of s.fields) {
            const doc = f.doc ? `  # ${f.doc}` : "";
            if (f.optional) out.push(`    ${pyName(f.json)}: Optional[${pyType(f)}] = None${doc}`);
            else out.push(`    ${pyName(f.json)}: ${pyType(f)}${doc}`);
        }
        out.push("");
    }
    return out.join("\n");
}

// ---------- 写出 / 校验 ----------

const outputs = [
    ["protocol/rust/src/messages.rs", genRust()],
    ["protocol/kotlin/BossProtocol.kt", genKotlin()],
    ["protocol/c/boss_protocol.h", genC()],
    ["protocol/python/boss_protocol.py", genPython()],
];

let dirty = 0;
for (const [rel, content] of outputs) {
    const path = join(root, rel);
    const exists = existsSync(path);
    const same = exists && readFileSync(path, "utf8") === content;
    if (checkMode) {
        console.log(`${same ? "OK     " : "STALE  "} ${rel}`);
        if (!same) dirty++;
    } else {
        mkdirSync(dirname(path), { recursive: true });
        writeFileSync(path, content, "utf8");
        console.log(`${exists ? "更新" : "生成"} ${rel}`);
    }
}
console.log(`消息 ${messages.length} 条 / 嵌套结构 ${structs.length} 个 / 枚举 ${enums.length} 个`);

if (checkMode && dirty > 0) {
    console.error(`\n${dirty} 个产物与 schema 不同步，请运行: node tools/gen-protocol/generate.mjs`);
    process.exit(1);
}
