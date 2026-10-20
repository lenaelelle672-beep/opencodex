# 本地补丁集（2.88.0）

这些改动**不在上游**，是本机为了把 Codex 接到 xAI/Cursor/智谱/公司网关而必须打的补丁。
`ocx update` 升级后补丁会丢，用同一目录里的脚本重打：

```bash
# 打到全局安装包
ocx update && ~/.npm-global/bin/ocx-patch && ~/.npm-global/bin/ocxup restart

# 打到源码克隆（用于把补丁提交成 commit）
OCX_PATCH_PKG="$PWD" local-patches/ocx-patch
```

脚本是幂等的：重复运行会输出「已打过」并跳过。

## 补丁清单（2.88 适配后剩 8 个）

| # | 文件 | 解决什么 |
|---|---|---|
| 3 | `src/combos/resolve.ts` | 单目标 combo 失败不进冷却（防 503 黑洞）。2.88 上游加了账号池冷却（`accountScoped`），锚点改为在其后再排除单目标 |
| 4 | `src/adapters/cursor/transport-retry.ts` | Cursor 限流错误改为可退避重试 |
| 5 | `src/server/effort-policy.ts` + `src/server/responses/core-normalize.ts` | 主对话强制抬到该模型真实最高推理档 |
| 8 | `src/adapters/anthropic.ts` | Anthropic 系普通文本 `<think>` 标签转为推理事件。2.88 上游用 `inline-think-tags.ts` 取代了 `kiro-thinking.ts`（kiro/openai-chat 已接线），本补丁改为给 anthropic 适配器接 `InlineThinkTagParser`，不再改 kiro 侧 |
| 9 | `src/images/plan.ts` | 生图/生视频桥支持 xAI OAuth 登录 |
| 10 | `src/images/plan.ts` | 生图桥改为配置驱动武装 |
| 11 | `src/codex/catalog/effort.ts` | 目录里所有有推理能力的模型统一可选 `max`/`ultra` |
| 12 | `src/lib/errors.ts` + `src/combos/failover.ts` | 智谱「使用上限」归类为 `usage_limit_exceeded` 并进 hop 列表。2.88 的 failover 里相似代码块有两处，hop 判定处用 `if ([ "permission_denied", ...` 前缀唯一锚定 |

## 已被 2.88 上游吸收、无需再打的补丁

| 旧 # | 内容 | 上游证据 |
|---|---|---|
| 13/13b | xai registry 收录 grok-4.7 | `entries-core.ts` 12 处 grok-4.7（service tier / Responses 优先级 2026-09-23 实测）+ `model-seeds.ts` `XAI_MODELS` 首位，另有 `grok-4.7-build-fast` OAuth 快车道 |
| 14 | Grok CLI 钉定版本 1.0.46 | `xai-transport.ts` `version: "1.0.46"`（上游 #6341/#6343） |
| 15 | cursor grok-4.7 窗口 500k | `discovery.ts` 启发式已含 `grok-4.7`，与本地改法一字不差 |

## 2.60 → 2.88 升级实录（2026-10-20）

- 8 个保留补丁中 P3/P12 换锚点、P8 整体重写，其余 5 个锚点未漂移。
- 新 registry 带进 10 个多余目录行（`gpt-6-sol`/`gpt-6-luna`/`gpt-6.1-sol`/`codex-auto-review`/
  5 个 `cursor/*` 新模型/公司网关新发现的 `deepseek-v4.1-flash-1017`），已全部加入
  `disabledModels` 藏掉，picker 维持 7 行。
- **智谱 5.3（gpt-6-astra）上下文 272k → 500k**：2.60 时代被 cursor/grok-4.7 的 256k
  启发式拖低（combo 窗口取成员最小值），上游 2.86 重做窗口推断后自然修复。
- 全量探针 7 行 + 生图桥全 200；P12 冒烟 `使用上限 → usage_limit_exceeded → hop` 通过；
  Kimi K3 随 Cursor 配额 10-16 重置恢复。

## 运维手册

`opencodex-Codex模型配置指南.md` 是本机日常操作的完整手册（provider 接入、combo 劫持、
7 行 picker 映射、排错实录）。入库版本把公司内网网关域名替换成 `<公司网关域名>` 占位符。

```bash
sed 's/aibedrock\.uniview\.com/<公司网关域名>/g' \
  ~/Desktop/opencodex-Codex模型配置指南.md \
  > local-patches/opencodex-Codex模型配置指南.md
```

## 已推送到 fork 的分支

云端仓库是 fork `lenaelelle672-beep/opencodex`（**不是**上游 `lidge-jun/opencodex`）。

| 分支 | 内容 |
|---|---|
| `local/288-patchset` | **本补丁集**，基于上游 tag `v2.88.0` |
| `local/260-patchset` | 2.60.0 时代的补丁集（含已被上游吸收的 13/13b/14/15，历史留档） |
| `upgrade-2.41` | 2.41 期补丁 8/9/10/11（历史参考） |
| `fix/cursor-call-id-nonstring` / `fix/codex-usage-limit-fidelity` | 2.48 期两个修复 |

> `fork/main` 停在 2.48.0 那条线，与上游无共同祖先可干净合并，补丁集一律单独走分支。
