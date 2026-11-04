# 本地补丁集（2.97.0）

这些改动**不在上游**，是本机为了把 Codex 接到 xAI/智谱/公司网关而必须打的补丁。
`ocx update` 升级后补丁会丢，用同一目录里的脚本重打：

```bash
# 打到全局安装包
ocx update && ~/.npm-global/bin/ocx-patch && ~/.npm-global/bin/ocxup restart

# 打到源码克隆（用于把补丁提交成 commit）
OCX_PATCH_PKG="$PWD" local-patches/ocx-patch
```

脚本幂等：重复运行输出「已打过」并跳过。

## 保留的补丁（2.97.0 适配后剩 8 个）

| # | 文件 | 解决什么 |
|---|---|---|
| 3 | `src/combos/resolve.ts` | 单目标 combo 失败不进冷却（防 503 黑洞）；锚点在上游 `accountScoped` 判断之后 |
| 4 | `src/adapters/cursor/transport-retry.ts` | Cursor 限流错误改为可退避重试 |
| 5 | `src/server/effort-policy.ts` + `src/server/responses/core-normalize.ts` | 主对话强制抬到该模型真实最高推理档 |
| 8 | `src/adapters/anthropic.ts` | Anthropic 系普通文本 `<think>` 标签转为推理事件（接上游 `inline-think-tags.ts`） |
| 9 | `src/images/plan.ts` | 生图/生视频桥支持 xAI OAuth 登录 |
| 10 | `src/images/plan.ts` | 生图桥改为配置驱动武装 |
| 11 | `src/codex/catalog/effort.ts` | 目录里所有有推理能力的模型统一可选 `max`/`ultra` |
| 12 | `src/lib/errors.ts` + `src/combos/failover.ts` | 智谱「使用上限」归类为 `usage_limit_exceeded` 并进 hop 列表 |

## 已被上游吸收、无需再打

| 旧 # | 内容 | 上游证据 |
|---|---|---|
| 13/13b | xai registry 收录 grok-4.7 | `entries-core.ts` 原生含 grok-4.7（含 build-fast 快车道）+ `model-seeds.ts` |
| 14 | Grok CLI 钉定版本 | `xai-transport.ts` `version: "1.0.46"` |
| 15 | cursor grok-4.7 窗口 500k | `discovery.ts` 启发式已含 grok-4.7 |
| 16 | 剥离 `output.encrypted_content` | `request-strips.ts` 原生 `stripUnsupportedOutputInclude()` |

## 2.88 → 2.97 升级实录（2026-11-04）

- 8 个保留补丁**锚点全部未漂移**，脚本一次通过；13/13b/14/15/16 自动跳过。
- 新 registry 带进 3 个多余行：`gpt-6.1-terra`（GPT-6.1 Terra）、`zhipu-bigmodel-coding/glm-5.3-flashx-legal`、
  `codex-auto-review`，已加入 `disabledModels` 隐藏，picker 维持 5 行。
- 探针（带 Codex 实际发送的 `include: ["reasoning.encrypted_content","output.encrypted_content"]`）：
  terra / 智谱5.3 / 公司两行全 200，生图桥 200。
- 智谱 Flash 撞 **7 天**限额（非 5 小时），单目标无备胎，等重置；智谱 5.3 撞限则 hop 到 xai 正常。

## 运维手册

`opencodex-Codex模型配置指南.md` 是本机日常操作的完整手册。入库版把公司内网网关域名替换为
`<公司网关域名>` 占位符：

```bash
sed 's/aibedrock\.uniview\.com/<公司网关域名>/g' \
  ~/Desktop/opencodex-Codex模型配置指南.md \
  > local-patches/opencodex-Codex模型配置指南.md
```

## 已推送到 fork 的分支

云端仓库是 fork `lenaelelle672-beep/opencodex`（**不是**上游 `lidge-jun/opencodex`）。

| 分支 | 内容 |
|---|---|
| `local/297-patchset` | **本补丁集**，基于上游 tag `v2.97.0` |
| `local/288-patchset` | 2.88.0 时代补丁集（历史留档） |
| `local/260-patchset` | 2.60.0 时代补丁集（历史留档） |
| `upgrade-2.41` | 2.41 期补丁（历史参考） |

> `fork/main` 停在 2.48.0 那条线，与上游无共同祖先可干净合并，补丁集一律单独走分支。
> 大 pack 推送被 GitHub 拒（HTTP 400）时用 `git -c http.postBuffer=524288000 push`。
