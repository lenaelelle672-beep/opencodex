# opencodex + Codex 模型配置指南

> 让 Codex（ChatGPT.app 里的 Codex GUI / CLI）使用任意第三方模型：Cursor 账号、xAI 官方、公司网关（gs-deepseek）等。
> 原理：本地起一个 opencodex 代理，Codex 所有请求先到代理，再由代理翻译转发到各 provider。
> 当前版本：**opencodex 2.88.0**（2026-10-20 从 2.60.0 升级，8 个本地补丁重新锚定；13/14/15 已被上游吸收）

---

## 一、架构总览

```
Codex app / CLI / ZCode 等客户端
        │  (OpenAI 兼容协议)
        ▼
opencodex 代理  http://127.0.0.1:10100/v1
        │  (协议翻译: Responses → 各家协议)
        ├── cursor            (api2.cursor.sh,       OAuth 登录, 用 Cursor 订阅额度)
        ├── xai               (api.x.ai,             OAuth 登录, xAI 官方直连)
        ├── zhipu-bigmodel-coding (open.bigmodel.cn, 个人智谱 Coding Plan)
        ├── gs-deepseek       (公司网关,              API Key,   Anthropic 协议)
        └── ...               (40+ 内置 provider)
```

关键概念：
- **provider**：一个上游服务（cursor / xai / gs-deepseek...）
- **模型 id**：带前缀写 `provider/model`，如 `xai/grok-4.7`、`cursor/kimi-k3`
- **combo + nativeAlias**：Codex GUI 只显示原生模型名（gpt-5.6-sol 等），用 combo 把原生名"劫持"到任意 provider 的模型上（见第四节，**重点**）

---

## 二、安装与启动

```bash
# 1. 安装（Node 18+，建议先换国内镜像）
npm config set registry https://registry.npmmirror.com
npm install -g @bitkyc08/opencodex

# 2. 启动
ocx start          # 前台启动, 控制台 http://localhost:10100

# 3. （推荐）装个快捷脚本 ocxup：启动+自动验证链路
#    见本文末尾附录 A
```

验证：
```bash
ocx status                    # 代理状态
curl http://127.0.0.1:10100/healthz
```

---

## 三、配置 Provider

### 3.1 OAuth 登录型（Cursor / xAI）

```bash
ocx login cursor    # 浏览器弹出 cursor.com 授权页, 批准即可
ocx login xai       # 同理, Grok 账号授权
```

- 不需要本地装 Cursor IDE / 不需要 API Key
- 走订阅额度（Cursor 的 fast requests / xAI 官方额度）
- Cursor 登录后默认会做 live 模型发现，**如果新模型不显示，关掉它改用静态表**（见 5.1）

### 3.2 API Key 型（公司网关 gs-deepseek 为例）

控制台 http://localhost:10100 → Providers → 添加，或命令行：

```bash
ocx provider add gs-deepseek --adapter anthropic \
  --base-url https://<公司网关域名> \
  --auth-mode key
# key 在控制台粘贴（注意：粘贴时别把引号带进去！）
```

> ⚠️ 公司网关的模型 id 是**全小写**：`glm-5.3-flash`、`deepseek-v4.1-flash`。写成 `DeepSeek-V4-Flash` 或其它大小写会返回
> `503 model_not_found ... No available channel for model ... under group`。

### 3.3 测试连通

```bash
ocx provider test cursor
ocx provider test gs-deepseek
# 期望输出: connected — N models available
```

---

## 四、让模型出现在 Codex 里（核心）

### 4.1 直接注册模型（命令行可用的形式）

```bash
# 注册自定义模型 + 最大上下文
ocx models add cursor claude-fable-5 --context-window 200000
ocx models add cursor kimi-k3        --context-window 1000000
ocx models add xai   grok-4.7        --context-window 500000

# 用法（CLI）:
codex -m "xai/grok-4.7" "你的任务"
```

### 4.2 Codex GUI 的坑：只认原生模型名

**Codex GUI 的模型选择器有白名单，带 `/` 前缀的路由模型一律不显示。**
解决办法：用 **combo + nativeAlias** 把 GUI 里的原生模型名劫持到你想用的模型：

```bash
# 把 GUI 里的 GPT-5.6-Terra 劫持到 xAI 官方 grok-4.7
ocx combo set terra-native \
  --targets xai/grok-4.7 \
  --alias gpt-5.6-terra \
  --native-alias \
  --display-name "xAI Grok 4.7 (官方直连)"
```

命名随意（不能和 provider 重名），一个原生名绑一个模型：

**2026-09-22 精简后的最终 7 行（2.60.0）**：

| GUI 里显示 | 实际走的 |
|---|---|
| xAI Grok 4.7 (官方直连)（劫持 gpt-5.6-terra） | xai/grok-4.7 |
| 智谱 Flash | zhipu-bigmodel-coding/glm-5.3-flash |
| 公司的GLM5.3Flash | gs-deepseek/glm-5.3-flash（公司网关） |
| 公司的DeepSeek4.1 | gs-deepseek/deepseek-v4.1-flash（公司网关） |
| 智谱 5.3（劫持 **gpt-6-astra**，窗口 500k） | 先 zhipu-bigmodel-coding/glm-5.3（官方 Coding Plan），撞限额再 xai/grok-4.7 |

已移除：GS-Sol 全系、公司 `glm`/`glm-5.3` 旧条目，以及**整个 Cursor provider**（2026-10-21：OAuth 会话一个月内两度被吊销，弃用）。官方 OpenAI（gpt-5.5 等）保留在目录里但走 ChatGPT 登录直连，不占 OpenCodex 配额。

带 `/` 的路由行（如 `zhipu-bigmodel-coding/glm-5.3`、`xai/grok-4.7`）会和上面的 nativeAlias **重复出现**。官方入口只留原生别名，重复路由行用 `ocx models disable <provider>/<model>` 藏掉，不要 disable `gpt-6-astra`。

> 🚨 **不要用 `gpt-daybreak-blue-latest` 做 nativeAlias**（2026-09-22 踩坑）：Codex 内置目录里这个 slug 被标了
> `"visibility": "hide"` + `"model_specialty": "cyber"`，GUI 会把它当成隐藏的网络安全专用模型直接过滤 ——
> 磁盘 catalog 里明明有这一行，选择器就是不显示（7 行只出 6 行）。改绑内置目录里
> `visibility: "list"` 且 `model_specialty: null` 的 slug（如 `gpt-6-astra`）才会显示。
> 内置可用 slug 一览（从 ChatGPT.app 的 codex 二进制里读出来的）：
> `gpt-5.5`、`gpt-5.6-sol`、`gpt-5.6-terra`、`gpt-5.6-luna`、`gpt-6-astra` 是 `list`；
> `gpt-5.4`、`gpt-daybreak-blue-latest`、`gpt-daybreak-red-latest`、`codex-auto-review` 是 `hide`。

> ⚠️ **provider 的 `models` 列表由 registry 重新派生**，手改 config.json 里的 `models` 下次 `ocx start` 会被抹掉。要真正新增模型（如 grok-4.7），必须改源码 registry（附录 B 补丁 13/13b），或直接依赖目录层的 `disabledModels` 做可见性控制。

配完刷新 + 重启 Codex 的 app-server：
```bash
ocx sync --restart-codex
```

> ⚠️ 显示名在 GUI 里更新不及时的话，`ocx sync` 后完全退出 Codex app（Cmd+Q）再打开。

### 4.3 多目标 failover（可选）

```bash
# fable-5 优先, 挂了自动切 grok-4.7
ocx combo set terra-native \
  --targets cursor/claude-fable-5,xai/grok-4.7 \
  --alias gpt-5.6-terra --native-alias
```

---

## 五、常见问题与坑（实战总结）

### 5.1 新模型 404 / not_found

opencodex 静态表可能还没收录新模型（比如当时的 grok-4.7）。**注意：`ocx models add` 只影响目录可见性，provider 的 `models` 元数据下次 `ocx start` 仍会按 registry 重派生**——要真正让新模型走通，得改源码 registry（附录 B 补丁 13）。两层修法：

```bash
# ① 关 live 发现, 防止它把"它不认识的"新模型滤掉
ocx provider edit cursor --live-models off
ocx provider edit xai   --live-models off

# ② 注册自定义模型
ocx models add xai grok-4.7 --context-window 500000
```

仍不行（协议层问题，如 Cursor 的 effort 后缀模型）需要打源码补丁 → 附录 B。

### 5.2 手改 config.json 会丢！

**opencodex 启动时会按 registry 规则重写 `~/.opencodex/config.json`，registry 不认识的模型键（`models` / `modelReasoningEfforts` / `modelContextWindows` / `modelInputModalities`）会被丢弃。**
`modelDisplayNames` 是例外——它是纯展示层，手改能留住。
改配置一律用官方命令（会持久化）：

```bash
ocx config set providers.xai.modelReasoningEfforts '{"grok-4.7":["low","medium","high","xhigh"]}'
ocx config show          # 查看（密钥自动脱敏）
```

### 5.3 401: OpenAI account pool has no usable account

Codex 默认模型走了 ChatGPT 账号池（没登录）。用 4.2 的 combo 劫持默认模型即可绕过，无需登录 ChatGPT。

### 5.4 503: No available targets for combo

combo 唯一目标失败后被拉进 60 秒冷却，期间所有请求秒拒。根修需打补丁（附录 B 补丁 3）。

### 5.5 400: prompt length 超限（如 500K 模型收到 900K）

会话是在大上下文模型（如 1M 的 K3）时代攒大的，切到小上下文模型（grok-4.7=500K）后旧历史直接超限。
**解决：开新会话，或旧会话 `/compact` 压缩后再切。**

### 5.6 推理档位：GUI 显示 ≠ 实际生效

- Codex GUI 对带前缀的路由模型，推理滑杆只显示到 xhigh（硬编码，改不了）
- 实际档位看请求发送值；要强制最高档，需代理补丁（附录 B 补丁 5），自动抬到各模型真实最高档
- 各模型真实最高档不同：grok-4.7/xhigh、fable-5/max、kimi-k3/max、智谱/thinking enabled——补丁会按模型自动对齐

### 5.7 Cursor 限流（rate limit exceeded / resource limit exceeded）

- 确认是 Cursor 服务端拒绝（错误文本带 `Cursor Connect error`）还是代理报错
- 减轻配额消耗：把 Codex 后台辅助调用分流到别的 provider：
```json
// ~/.opencodex/config.json（用 ocx config set 改, 别手改）
"shadowCallIntercept": { "enabled": true, "model": "gs-deepseek/deepseek-v4.1-flash" }
```

---

## 六、其他客户端接入（ZCode 等 OpenAI 兼容客户端）

```
Base URL: http://127.0.0.1:10100/v1
API Key:  随便填（如 sk-opencodex），本机不校验
Model:    xai/grok-4.7（或其他带前缀模型 id）
```

---

## 附录 A：ocxup 快捷脚本

放到 `~/.npm-global/bin/ocxup`（PATH 内），chmod +x：

```bash
#!/bin/bash
# ocxup: opencodex 启动/停止/重启 + 链路自检
OCX_BIN="$HOME/.npm-global/bin/ocx"
is_running() { curl -s -o /dev/null -m 2 http://127.0.0.1:10100/healthz; }
case "${1:-start}" in
  status) "$OCX_BIN" status; exit 0;;
  stop)   "$OCX_BIN" stop; exit 0;;
  restart) "$OCX_BIN" stop >/dev/null 2>&1; sleep 1;;
esac
if is_running; then echo "✅ opencodex 已在运行"; else
  "$OCX_BIN" start >/tmp/ocxup-start.log 2>&1 &
  for i in $(seq 10); do sleep 1; is_running && break; done
  is_running && echo "✅ opencodex 已启动" || { echo "❌ 启动失败"; tail -20 /tmp/ocxup-start.log; exit 1; }
fi
code=$(curl -s -o /dev/null -w "%{http_code}" -m 60 -X POST http://127.0.0.1:10100/v1/responses \
  -H "Content-Type: application/json" \
  -d '{"model":"xai/grok-4.7","input":"hi","stream":false}')
echo "模型链路: HTTP $code (200=正常)"
```

日常：`ocxup` 启动 / `ocxup stop` 停止 / `ocxup restart` 重启。

## 附录 B：本地补丁（2026-10-20 更新，2.88.0 适配，共 8 个）

以下问题配置层无解，需要改安装包源码（`~/.npm-global/lib/node_modules/@bitkyc08/opencodex/src/`）：

| # | 文件 | 解决什么 |
|---|---|---|
| 3 | combos/resolve.ts | 单目标 combo 失败不进 60s 冷却（防 503 黑洞）|
| 11 | codex/catalog/effort.ts | 目录里所有有推理能力的模型统一可选 max/ultra，代理按上游真实最高档发送（智谱 enabled / Anthropic max / xAI xhigh）|
| 4 | adapters/cursor/transport-retry.ts | Cursor 限流错误改为可退避重试 |
| 5 | server/effort-policy.ts + responses/core-normalize.ts | 主对话强制抬到该模型真实最高推理档 |
| 8 | adapters/anthropic.ts + kiro-thinking.ts | Anthropic 系普通文本 `<think>` 标签转为推理事件（防泄漏进正文）|
| 9 | images/plan.ts | 生图/生视频桥支持 xAI OAuth 登录（上游只认 API Key）|
| 10 | images/plan.ts | 生图桥改为配置驱动武装（Codex 无 ChatGPT 登录时不会发生图工具，代理主动注入；豁免压缩与非流式请求）|
| 12 | lib/errors.ts + combos/failover.ts | 智谱/计划额度上限原文回给 Codex（`usage_limit_exceeded` 进 hop 列表），切模型不再被前一个 provider 的限额粘住 |
| 13 | providers/registry/entries-core.ts | xai registry 收录 grok-4.7（service tier / Responses wire / 视觉 / prompt cache / 推理档 low-xhigh / 500k 窗口）|
| 13b | providers/registry/model-seeds.ts | `XAI_MODELS` 收录 grok-4.7 |
| ~~13/13b~~ xai registry grok-4.7 | **2.88 上游已吸收**（含 grok-4.7-build-fast 快车道），无需再打 |
| ~~14~~ Grok CLI 钉定版本 | **2.88 上游已吸收**（#6341/#6343，1.0.46） |
| ~~15~~ cursor grok-4.7 窗口 | **2.88 上游已吸收**（与本地改法一字不差） |

> **为什么 13 必须改源码**：`ocx start` 每次都从 `PROVIDER_REGISTRY` 重新派生 provider 的 `models`、`modelReasoningEfforts`、`modelContextWindows` 等元数据，写进 `config.json` 的 `grok-4.7` 键会在下一次启动被抹掉。抹掉之后 `supportedLadderFor()` 返回 `undefined`，补丁 5 就把回合抬到 `max`，而 xAI 的 grok-4.7 只认 `low/medium/high/xhigh` —— 报 400 `Invalid reasoning effort.`。同理，`grok-4.7` 的能力必须落在 registry 里才稳。

> 2.41.0 已原生内置、无需再打的旧补丁：1/2（Cursor grok-4.6 映射与 Fast 路径）、6（registry grok-4.6）、7（xAI 工具 union schema，上游已用 `xai-tool-schema.ts` 模块重写）。

> ⚠️ `ocx update` 升级后补丁会丢，需重打。补丁已做成幂等脚本（`~/.npm-global/bin/ocx-patch`，重跑全部显示"已打过"）：
> ```bash
> ocx update && ~/.npm-global/bin/ocx-patch && ocxup restart
> ```
> 回滚到 2.41.0：
> ```bash
> npm i -g @bitkyc08/opencodex@2.41.0 && ~/.npm-global/bin/ocx-patch && ~/.npm-global/bin/ocxup start
> ```

> 🖼️ 生图须知：xAI Imagine 会拒绝版权角色（如"皮卡丘"→ 400 content-moderated，且被拒也计费），提示词用原创描述；grok 直连依赖 `/etc/hosts` 钉定 4 个 xAI 域名（脚本 `~/.npm-global/bin/fix-xai-dns`，需 sudo，幂等可重跑）。生图/生视频桥的正确探针是 `POST /v1/images/generations`（返回 `b64_json`），**不是** `/v1/responses`——把 `grok-imagine-*` 当聊天模型探测会得到误导性的 503。

## 附录 D：2.60.0 端到端验证（2026-09-22）

| Picker 行 | 上游 | 结果 |
|---|---|---|
| xAI Grok 4.7 (官方直连) | xai/grok-4.7 | 200，`model=grok-4.7-build`，`reasoning.effort=xhigh` |
| Cursor Grok 4.7 | cursor/grok-4.7 | 200，`model=grok-4.7` |
| Cursor Kimi K3 | cursor/kimi-k3 | 200，`model=kimi-k3` |
| 智谱 5.3（gpt-6-astra） | zhipu glm-5.3 → cursor/grok-4.7 | 200（智谱 Coding Plan 当时撞 7 天限额，combo 已 hop 到 Cursor） |
| 智谱 Flash | zhipu glm-5.3-flash | 429 已达到 7 天使用上限，2026-09-24 14:44:59 后恢复 |
| 公司的GLM5.3Flash | gs-deepseek/glm-5.3-flash | 200 |
| 公司的DeepSeek4.1 | gs-deepseek/deepseek-v4.1-flash | 200 |

`ultra` 档全 7 行可选；实测 wire 映射：xAI terra `ultra→xhigh`（openai-responses），Cursor/智谱保持各自最高合法档。生图桥 `/v1/images/generations` 200 返回 1 张图。

## 附录 C：日常速查

```bash
ocxup                    # 启动（含链路自检）
ocxup stop / restart     # 停止 / 重启
ocx status               # 状态
ocx provider list/test   # provider 列表 / 连通测试
ocx models list-custom   # 已注册的自定义模型
ocx combo list/show X    # combo 劫持关系
ocx sync --restart-codex # 刷新 Codex catalog 并重启其 app-server
ocx observe logs         # 实时请求日志（排错第一现场）
ocx config show          # 全量配置（脱敏）
```


## 附录 E：上游更新与 426 事件（2026-10-09）

- **上游已到 2.81.0**（本机 2.60.0，中间 1299 个提交）。升级命令照旧：
  `ocx update && ~/.npm-global/bin/ocx-patch && ocxup restart`，升级后必须重验
  terra/luna/sol/astra 四条路由 + 生图桥。
- **426 Upgrade Required 事件**：`gpt-5.6-terra`（xai/grok-4.7 OAuth 车道）全量报
  `Your Grok CLI version (0.2.93) is outdated. Please update to version 1.0.13 or later`。
  原因是 OpenCodex 钉定了伪装的 Grok CLI 版本号，xAI 网关提高了下限。补丁 14 把钉定
  提到 1.0.46（与上游一致），修完实测 terra 200 / model=grok-4.7-build / effort=xhigh。
  这个钉定值以后还会过期——再看到 426 且文案提版本号，就是这个原因，照补丁 14 改版本号即可。
- 同日智谱 Coding Plan 的 7 天限额已恢复（gpt-6-astra 直接回 glm-5.3，不再 hop）。


## 附录 F：2.60 → 2.88 升级实录（2026-10-20）

- **版本**：2.60.0 → 2.88.0（npm latest；2.89.0 仅在 GitHub，registry 未上架）。
- **补丁**：8 个保留（P3/P12 换锚点，P8 重写为接上游新模块 `InlineThinkTagParser`，
  其余 5 个锚点未漂移）；13/13b、14、15 已被上游吸收，脚本自动跳过。
- **目录**：新 registry 多出 10 行（gpt-6-sol/luna、gpt-6.1-sol、codex-auto-review、
  5 个 cursor 新模型、公司网关新发现的 deepseek-v4.1-flash-1017），已加入 disabledModels，
  picker 维持 7 行。
- **智谱 5.3 窗口 272k → 500k**：2.60 时代被 cursor/grok-4.7 的 256k 启发式拖低
  （combo 窗口取成员最小值），上游 2.86 重做窗口推断后自然修复，本地补丁 15 归档。
- **探针**：7 行全 200（Kimi K3 随 Cursor 配额 10-16 重置恢复）+ 生图桥 200 +
  P12 冒烟 `使用上限 → usage_limit_exceeded → hop` 通过。
- **云端**：fork 新增 `local/288-patchset`（基于 v2.88.0）；`local/260-patchset` 留档。
  大 pack 推送被 GitHub 拒（HTTP 400）时用
  `git -c http.postBuffer=524288000 push fork <分支>`。
- **回退**：`npm i -g @bitkyc08/opencodex@2.60.0 && ~/.npm-global/bin/ocx-patch && ~/.npm-global/bin/ocxup start`
  （注意回退后 15 个补丁的脚本仍兼容：13/14/15 会重新打上）。


## 附录 G：移除 Cursor（2026-10-21）

Cursor OAuth 会话一个月内两度被吊销（xAI 也死过一次），第二次 refresh token 直接失效，
`ocx login cursor` 也只是续命。决定整体弃用：

- 删 `providers.cursor`、删 `cursor-grok47-native`（gpt-5.6-luna）与 `k3-native`（gpt-5.6-sol）两个 combo；
- 智谱 5.3（gpt-6-astra）的 failover 备胎 cursor/grok-4.7 → **xai/grok-4.7**（同一底层模型，官方直连）；
- visionSidecar 从 gpt-5.6-luna 改指 gpt-5.6-terra；
- `ocxup` 次检从 Cursor 车道换成智谱链路（gpt-6-astra）。
- picker 7 行 → **5 行**，全量探针 200。auth.json 里的 Cursor 凭证未删（想彻底清就 `ocx logout cursor`）。
- 若日后想恢复：`ocx login cursor` + 把两个 combo 加回来即可，配置备份在
  `config.json.bak-no-cursor-20261021-*`。
