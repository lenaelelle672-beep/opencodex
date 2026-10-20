#!/usr/bin/env python3
"""补丁 8（2.88 版）：anthropic 适配器接入上游 InlineThinkTagParser。

上游 2.88 用 src/adapters/inline-think-tags.ts 取代了 kiro-thinking.ts，kiro 与
openai-chat 适配器都已接线，唯独 anthropic 不解析普通文本块里的 <think> 标签。
公司网关这类 Anthropic 兼容上游会把推理序列化成正文开头的字面标签，本补丁把
流式与非流式两条路径的普通文本都过一遍解析器，标签内容转成 reasoning 事件。
"""
from pathlib import Path
import os
import sys

pkg = Path(os.environ.get("OCX_PATCH_PKG") or (Path.home() / ".npm-global/lib/node_modules/@bitkyc08/opencodex"))
anthropic = pkg / "src/adapters/anthropic.ts"
marker = "Anthropic-compatible gateways may serialize reasoning as a leading literal tag"

if not anthropic.exists():
    sys.exit(f"patch 8: anthropic.ts not found under {pkg}")
if marker in anthropic.read_text():
    print("patch 8 already applied")
    raise SystemExit(0)

s = anthropic.read_text()

replacements = [
    # 0) import 解析器
    (
        'import { isTranslatorBudgetExceededError, retainTranslatedEventBatch, type TranslatorBudget } from "../lib/translator-budget";\n',
        'import { isTranslatorBudgetExceededError, retainTranslatedEventBatch, type TranslatorBudget } from "../lib/translator-budget";\n'
        'import { InlineThinkTagParser } from "./inline-think-tags";\n',
    ),
    # 1) 流式路径：解析器与包装函数（2.88 的变量块，serverSearch 声明在其后）
    (
        '      let emittedDone = false;\n'
        '      let sawVisibleText = false;\n',
        '      let emittedDone = false;\n'
        '      let sawVisibleText = false;\n'
        '      // Anthropic-compatible gateways may serialize reasoning as a leading literal tag\n'
        '      // inside ordinary text blocks instead of emitting structured thinking deltas.\n'
        '      const taggedThinking = new InlineThinkTagParser(budget);\n'
        '      const parseOrdinaryText = (text: string): AdapterEvent[] => {\n'
        '        const events = taggedThinking.feed(text);\n'
        '        if (events.some(event => event.type === "text_delta" && event.text.length > 0)) sawVisibleText = true;\n'
        '        return events;\n'
        '      };\n'
        '      const flushOrdinaryText = (): AdapterEvent[] => {\n'
        '        const events = taggedThinking.flush();\n'
        '        if (events.some(event => event.type === "text_delta" && event.text.length > 0)) sawVisibleText = true;\n'
        '        return events;\n'
        '      };\n',
    ),
    # 2) 流式 text_delta：先分类再判可见性
    (
        '                if (delta.type === "text_delta" && typeof delta.text === "string") {\n'
        '                  // Only non-empty text proves the upstream produced usable output; an empty\n'
        '                  // delta followed by EOF must stay a truncation error even on the tolerant\n'
        '                  // profile, or a cut-off turn would surface as a successful empty answer.\n'
        '                  if (delta.text.length > 0) sawVisibleText = true;\n'
        '                  yield { type: "text_delta", text: delta.text };\n',
        '                if (delta.type === "text_delta" && typeof delta.text === "string") {\n'
        '                  // Visibility is determined after literal thinking tags are classified. Tagged\n'
        '                  // reasoning must not make a reasoning-only tolerant-EOF response look complete.\n'
        '                  for (const event of parseOrdinaryText(delta.text)) yield event;\n',
    ),
    # 3) content_block_stop：文本块收尾时冲刷解析器（2.88 新增了 serverSearch 分支）
    (
        '              case "content_block_stop": {\n'
        '                if (serverSearch) serverSearch.streaming = false;\n'
        '                if (currentBlockType === "tool_use") {\n',
        '              case "content_block_stop": {\n'
        '                if (serverSearch) serverSearch.streaming = false;\n'
        '                if (currentBlockType === "text") {\n'
        '                  for (const event of flushOrdinaryText()) yield event;\n'
        '                }\n'
        '                if (currentBlockType === "tool_use") {\n',
    ),
    # 4) message_stop：先冲刷再收尾
    (
        '              case "message_stop": {\n'
        '                yield* emitDone();\n',
        '              case "message_stop": {\n'
        '                for (const event of flushOrdinaryText()) yield event;\n'
        '                yield* emitDone();\n',
    ),
    # 5) 容错 EOF 收尾前冲刷
    (
        '      if (!emittedDone) {\n'
        '        // Fail closed on transport EOF. Compatible providers may omit message_stop after message_delta.stop_reason.\n',
        '      if (!emittedDone) {\n'
        '        for (const event of flushOrdinaryText()) yield event;\n'
        '        // Fail closed on transport EOF. Compatible providers may omit message_stop after message_delta.stop_reason.\n',
    ),
    # 6) 非流式路径：实例化解析器
    (
        '      const events: AdapterEvent[] = [];\n',
        '      const events: AdapterEvent[] = [];\n'
        '      const taggedThinking = new InlineThinkTagParser(budget);\n',
    ),
    # 7) 非流式文本块：过解析器
    (
        '          if (block.type === "text" && block.text) {\n'
        '            events.push({ type: "text_delta", text: block.text });\n',
        '          if (block.type === "text" && block.text) {\n'
        '            events.push(...taggedThinking.feed(block.text), ...taggedThinking.flush());\n',
    ),
]

for i, (old, new) in enumerate(replacements):
    n = s.count(old)
    if n != 1:
        sys.exit(f"patch 8 anthropic anchor {i} matched {n} times (expected 1); package structure changed")
    s = s.replace(old, new, 1)

anthropic.write_text(s)
print("patch 8 applied")
