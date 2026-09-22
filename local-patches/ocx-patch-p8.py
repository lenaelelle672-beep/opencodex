#!/usr/bin/env python3
from pathlib import Path
import os
import sys

# 目标包路径：默认全局安装；OCX_PATCH_PKG 可指向源码克隆（与 ocx-patch 保持一致）
pkg = Path(os.environ.get("OCX_PATCH_PKG") or (Path.home() / ".npm-global/lib/node_modules/@bitkyc08/opencodex"))
kiro = pkg / "src/adapters/kiro-thinking.ts"
anthropic = pkg / "src/adapters/anthropic.ts"
marker = "Anthropic-compatible gateways may serialize reasoning as a leading literal tag"

if not anthropic.exists():
    sys.exit(f"patch 8: anthropic.ts not found under {pkg}")

if marker in anthropic.read_text():
    print("patch 8 already applied")
    raise SystemExit(0)

ks = kiro.read_text()
asrc = anthropic.read_text()

replacements_kiro = [
    (
        'type ThinkingTag = "<thinking>" | "<think>" | "<reasoning>";\ntype ParserState = "pre" | "thinking" | "streaming";\n',
        'type ThinkingTag = "<thinking>" | "<think>" | "<reasoning>";\ntype ParserState = "pre" | "thinking" | "streaming";\n\nexport type ThinkingParserOptions = {\n  preserveWhitespaceAfterClose?: boolean;\n};\n',
    ),
    (
        '  constructor(private readonly budget?: TranslatorBudget) {}\n',
        '  constructor(\n    private readonly budget?: TranslatorBudget,\n    private readonly options: ThinkingParserOptions = {},\n  ) {}\n',
    ),
    (
        '      const thinking = this.thinkingBuffer.slice(0, idx);\n      const after = this.thinkingBuffer.slice(idx + close.length).trimStart();\n',
        '      const thinking = this.thinkingBuffer.slice(0, idx);\n      const remainder = this.thinkingBuffer.slice(idx + close.length);\n      const after = this.options.preserveWhitespaceAfterClose ? remainder : remainder.trimStart();\n',
    ),
]

replacements_anthropic = [
    (
        'import { isTranslatorBudgetExceededError, retainTranslatedEventBatch, type TranslatorBudget } from "../lib/translator-budget";\n',
        'import { isTranslatorBudgetExceededError, retainTranslatedEventBatch, type TranslatorBudget } from "../lib/translator-budget";\nimport { KiroThinkingParser } from "./kiro-thinking";\n',
    ),
    (
        '      let emittedDone = false;\n      let sawVisibleText = false;\n\n      const emitDone = function* (): Generator<AdapterEvent> {',
        '      let emittedDone = false;\n      let sawVisibleText = false;\n      // Anthropic-compatible gateways may serialize reasoning as a leading literal tag\n      // inside ordinary text blocks instead of emitting structured thinking deltas.\n      const taggedThinking = new KiroThinkingParser(budget, { preserveWhitespaceAfterClose: true });\n      const parseOrdinaryText = (text: string): AdapterEvent[] => {\n        const events = taggedThinking.feed(text);\n        if (events.some(event => event.type === "text_delta" && event.text.length > 0)) sawVisibleText = true;\n        return events;\n      };\n      const flushOrdinaryText = (): AdapterEvent[] => {\n        const events = taggedThinking.flush();\n        if (events.some(event => event.type === "text_delta" && event.text.length > 0)) sawVisibleText = true;\n        return events;\n      };\n\n      const emitDone = function* (): Generator<AdapterEvent> {',
    ),
    (
        '                if (delta.type === "text_delta" && typeof delta.text === "string") {\n                  // Only non-empty text proves the upstream produced usable output; an empty\n                  // delta followed by EOF must stay a truncation error even on the tolerant\n                  // profile, or a cut-off turn would surface as a successful empty answer.\n                  if (delta.text.length > 0) sawVisibleText = true;\n                  yield { type: "text_delta", text: delta.text };\n',
        '                if (delta.type === "text_delta" && typeof delta.text === "string") {\n                  // Visibility is determined after literal thinking tags are classified. Tagged\n                  // reasoning must not make a reasoning-only tolerant-EOF response look complete.\n                  for (const event of parseOrdinaryText(delta.text)) yield event;\n',
    ),
    (
        '              case "content_block_stop": {\n                if (currentBlockType === "tool_use") {',
        '              case "content_block_stop": {\n                if (currentBlockType === "text") {\n                  for (const event of flushOrdinaryText()) yield event;\n                }\n                if (currentBlockType === "tool_use") {',
    ),
    (
        '              case "message_stop": {\n                yield* emitDone();\n',
        '              case "message_stop": {\n                for (const event of flushOrdinaryText()) yield event;\n                yield* emitDone();\n',
    ),
    (
        '      if (!emittedDone) {\n        // Fail closed on transport EOF. Compatible providers may omit message_stop after message_delta.stop_reason.\n',
        '      if (!emittedDone) {\n        for (const event of flushOrdinaryText()) yield event;\n        // Fail closed on transport EOF. Compatible providers may omit message_stop after message_delta.stop_reason.\n',
    ),
    (
        '      const events: AdapterEvent[] = [];\n',
        '      const events: AdapterEvent[] = [];\n      const taggedThinking = new KiroThinkingParser(budget, { preserveWhitespaceAfterClose: true });\n',
    ),
    (
        '          if (block.type === "text" && block.text) {\n            events.push({ type: "text_delta", text: block.text });\n',
        '          if (block.type === "text" && block.text) {\n            events.push(...taggedThinking.feed(block.text), ...taggedThinking.flush());\n',
    ),
]

for old, new in replacements_kiro:
    if old not in ks:
        sys.exit("patch 8 kiro anchor not found; package structure changed")
    ks = ks.replace(old, new, 1)

for old, new in replacements_anthropic:
    if old not in asrc:
        sys.exit("patch 8 anthropic anchor not found; package structure changed")
    asrc = asrc.replace(old, new, 1)

kiro.write_text(ks)
anthropic.write_text(asrc)
print("patch 8 applied")
