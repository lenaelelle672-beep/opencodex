# 本地补丁集（2.60.0）

这些改动**不在上游**，是本机为了把 Codex 接到 xAI/Cursor/智谱/公司网关而必须打的补丁。
`ocx update` 升级后补丁会丢，用同一目录里的脚本重打：

```bash
# 打到全局安装包
ocx update && ~/.npm-global/bin/ocx-patch && ~/.npm-global/bin/ocxup restart

# 打到源码克隆（用于把补丁提交成 commit）
OCX_PATCH_PKG="$PWD" local-patches/ocx-patch
```

脚本是幂等的：重复运行会输出「已打过」并跳过，不会重复插入。

## 补丁清单

| # | 文件 | 解决什么 |
|---|---|---|
| 3 | `src/combos/resolve.ts` | 单目标 combo 失败不进 60s 冷却（防 503 黑洞） |
| 4 | `src/adapters/cursor/transport-retry.ts` | Cursor 限流错误改为可退避重试 |
| 5 | `src/server/effort-policy.ts` + `src/server/responses/core-normalize.ts` | 主对话强制抬到该模型真实最高推理档 |
| 8 | `src/adapters/anthropic.ts` + `src/adapters/kiro-thinking.ts` | Anthropic 系普通文本 `<think>` 标签转为推理事件（防泄漏进正文） |
| 9 | `src/images/plan.ts` | 生图/生视频桥支持 xAI OAuth 登录（上游只认 API Key） |
| 10 | `src/images/plan.ts` | 生图桥改为配置驱动武装（Codex 无 ChatGPT 登录时不会发图工具，代理主动注入；豁免压缩与非流式请求） |
| 11 | `src/codex/catalog/effort.ts` | 目录里所有有推理能力的模型统一可选 `max`/`ultra`，代理按上游真实最高档发送 |
| 12 | `src/lib/errors.ts` + `src/combos/failover.ts` | 智谱/计划额度上限原文回给 Codex（`usage_limit_exceeded` 进 hop 列表），切模型不再被前一个 provider 的限额粘住 |
| 13 | `src/providers/registry/entries-core.ts` | xai registry 收录 `grok-4.7`（service tier / Responses wire / 视觉 / prompt cache / 推理档 low–xhigh / 500k 窗口） |
| 13b | `src/providers/registry/model-seeds.ts` | `XAI_MODELS` 收录 `grok-4.7` |

## 为什么 13/13b 必须改源码

`ocx start` 每次都从 `PROVIDER_REGISTRY` 重新派生 provider 的 `models`、`modelReasoningEfforts`、
`modelContextWindows` 等元数据，手写进 `config.json` 的 `grok-4.7` 键会在下一次启动被抹掉。
抹掉之后 `supportedLadderFor()` 返回 `undefined`，补丁 5 就把回合抬到 `max`，而 xAI 的
`grok-4.7` 只认 `low/medium/high/xhigh` —— 报 400 `Invalid reasoning effort.`。

## 已知会打破的既有测试

补丁 5（强制抬档）与补丁 11（目录统一显示 ultra）按设计改变了 Codex 目录/线缆上的档位契约，
所以上游这几个测试会失败，属于预期：

- `tests/codex-integration/model-pinned-effort.test.ts`（operator pin 语义被抬档覆盖）
- `tests/codex-integration/codex-catalog.test.ts` 的 Astra 档位边界与 combo 交叉用例
- `tests/images/plan.test.ts` 的 `authMode oauth does not arm the bridge`（补丁 9 正是要武装它）

其余套件（`scripts/test.ts`）在打补丁前后结果一致。验证基线：

```bash
bun run scripts/test.ts tests/providers/kiro/kiro-stream.test.ts \
  tests/codex-integration/effort-policy.test.ts tests/codex-integration/codex-catalog.test.ts \
  tests/codex-integration/catalog-duplicate-slug-dedup.test.ts \
  tests/codex-integration/model-pinned-effort.test.ts \
  tests/images/plan.test.ts tests/images/artifacts-ssrf.test.ts \
  tests/images/pinned-https-get.test.ts tests/images/xai-client.test.ts \
  tests/server/error-fidelity.test.ts
# 纯净 2.60.0：650 pass / 0 fail
# 打补丁后：622 pass / 28 fail（全部为上述三类预期失败）
```

## 已推送到 fork 的分支

云端仓库是 fork `lenaelelle672-beep/opencodex`（**不是**上游 `lidge-jun/opencodex`）。
本补丁集已随源码克隆提交并推送：

| 分支 | 内容 |
|---|---|
| `local/260-patchset` | **本补丁集**，基于上游 tag `v2.60.0` 的完整源码 + 10 个补丁 |
| `upgrade-2.41` | 2.41 期的补丁 8/9/10/11（历史参考：`7bee16067`、`ce8dda9e6`、`8610340b8`、`95afc514d`） |
| `fix/cursor-call-id-nonstring` | Cursor Responses 回放容忍缺失/非字符串 call_id |
| `fix/codex-usage-limit-fidelity` | 计划额度上限原文回给 Codex（2.48 期） |

> `fork/main` 停留在 2.48.0 那条线（含上面两个 `fix/*`），与上游 2.60.0 没有共同祖先，
> 所以本补丁集单独走 `local/260-patchset`，没有合进 `main`。
