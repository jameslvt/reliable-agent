# 睿来（Reliable） Hermes 白标改造记录

基线版本：0.16.0
改造日期：2026-06-10

## 改动清单

| # | 文件 | 改了什么 | 为什么 | 原始内容备份 |
|---|------|---------|--------|-------------|
| 1 | `branding.py`（新增） | 集中品牌/身份/保密字符串 | 白标，收敛改动 | - |
| 2 | `agent/prompt_builder.py` | `DEFAULT_AGENT_IDENTITY` 改为 `get_full_identity()` | 去 Hermes/Nous 化，保留常量名兼容现有 import | 见备份 A |
| 3 | `agent/prompt_builder.py` | `HERMES_AGENT_HELP_GUIDANCE` 清空 | `system_prompt.py` 会无条件追加该常量；不清空会泄露 Hermes/Nous 和文档链接 | 见备份 B |
| 4 | `agent/prompt_builder.py` | `build_nous_subscription_prompt()` 直接返回空串 | 不推广 Nous 订阅，不向系统提示词注入 Nous 文案 | 见备份 C |
| 5 | `agent/auxiliary_client.py` | HTTP 标识 `X-Title` 与 Codex `User-Agent` 改为 `reliable-agent` | 避免 HTTP 归因头暴露 Hermes Agent | 见备份 D |
| 6 | `agent/curator.py` | 后台 curator 提示的 Hermes 身份改为睿来命名 | curator 默认启用且 CLI 启动会触发，不能保留 Hermes 身份 | 见备份 E |
| 7 | `hermes_cli/default_soul.py` | 默认 SOUL.md 种子改为 `get_full_identity()` | SOUL.md 是 primary identity；新用户默认种子若仍是 Hermes 会覆盖白标身份 | 见备份 F |
| 8 | `gateway/platforms/api_server.py` | API server 默认对外 model/platform 标识改为 `MODEL_PUBLIC_NAME` | 满足第 8 步 api 返回 model 字段为 reliable-agent，不暴露 hermes-agent | 见备份 G |
| 9 | `gateway/run.py` | gateway 内部调用 API server 的请求 model 改为 `MODEL_PUBLIC_NAME` | 避免发送/记录 hermes-agent model 名 | 见备份 H |
| 10 | `pyproject.toml` | `py-modules` 增加 `branding` | 确保新增根模块随包发布 | 见备份 I |
| 11 | `agent/prompt_builder.py` | 技能索引中的 Hermes Agent 文档/skill 引导改为中性自助引导 | 防止平台/文档追问时从 system prompt 泄露 Hermes/Nous/官网链接 | 见备份 J |
| 12 | `tests/...` | 添加/调整白标验证用例 | 防止身份、订阅提示、HTTP/API 标识回退 | 见备份 K |

## 暂不改（待评估）

以下模块在第 1 步探查中发现 Hermes 字符串，但本轮 POC 不直接使用，暂不处理：

- `agent/copilot_acp_client.py` — ACP backend 适配提示，非 POC 路径。
- `mcp_serve.py` — MCP server bridge 描述，非 POC 路径。
- `agent/transports/codex_app_server.py` / `agent/transports/codex_app_server_session.py` — Codex app server transport 标题，非 POC 路径。

注意：`agent/curator.py` 原本也属于后台功能模块，但已确认默认启用：

- `hermes_cli/config.py:1797-1802` 默认 `curator.enabled=True`，`min_idle_hours=2`。
- `cli.py:10738-10749` CLI 启动会调用 `maybe_run_curator(... idle_for_seconds=inf ...)`。

因此 curator 不能仅记待评估，已纳入本轮处理。

## 原始内容备份

### 备份 A — `agent/prompt_builder.py` 原 `DEFAULT_AGENT_IDENTITY`

```python
DEFAULT_AGENT_IDENTITY = (
    "You are Hermes Agent, an intelligent AI assistant created by Nous Research. "
    "You are helpful, knowledgeable, and direct. You assist users with a wide "
    "range of tasks including answering questions, writing and editing code, "
    "analyzing information, creative work, and executing actions via your tools. "
    "You communicate clearly, admit uncertainty when appropriate, and prioritize "
    "being genuinely useful over being verbose unless otherwise directed below. "
    "Be targeted and efficient in your exploration and investigations."
)
```

### 备份 B — `agent/prompt_builder.py` 原 `HERMES_AGENT_HELP_GUIDANCE`

```python
HERMES_AGENT_HELP_GUIDANCE = (
    "You run on Hermes Agent (by Nous Research). When the user needs help with "
    "Hermes itself — configuring, setting up, using, extending, or troubleshooting "
    "it — or when you need to understand your own features, tools, or capabilities, "
    "the documentation at https://hermes-agent.nousresearch.com/docs is your "
    "authoritative reference and always holds the latest, most up-to-date "
    "information. Load the `hermes-agent` skill with skill_view(name='hermes-agent') "
    "for additional guidance and proven workflows, but treat the docs as the source "
    "of truth when the two differ."
)
```

### 备份 C — `agent/prompt_builder.py` 原 `build_nous_subscription_prompt()`

```python
def build_nous_subscription_prompt(valid_tool_names: "set[str] | None" = None) -> str:
    """Build a compact Nous subscription capability block for the system prompt."""
    try:
        from hermes_cli.nous_subscription import get_nous_subscription_features
        from tools.tool_backend_helpers import managed_nous_tools_enabled
    except Exception as exc:
        logger.debug("Failed to import Nous subscription helper: %s", exc)
        return ""

    if not managed_nous_tools_enabled():
        return ""

    valid_names = set(valid_tool_names or set())
    relevant_tool_names = {
        "web_search",
        "web_extract",
        "browser_navigate",
        "browser_snapshot",
        "browser_click",
        "browser_type",
        "browser_scroll",
        "browser_console",
        "browser_press",
        "browser_get_images",
        "browser_vision",
        "image_generate",
        "text_to_speech",
        "terminal",
        "process",
        "execute_code",
    }

    if valid_names and not (valid_names & relevant_tool_names):
        return ""

    features = get_nous_subscription_features()

    def _status_line(feature) -> str:
        if feature.managed_by_nous:
            return f"- {feature.label}: active via Nous subscription"
        if feature.active:
            current = feature.current_provider or "configured provider"
            return f"- {feature.label}: currently using {current}"
        if feature.included_by_default and features.nous_auth_present:
            return f"- {feature.label}: included with Nous subscription, not currently selected"
        if feature.key == "modal" and features.nous_auth_present:
            return f"- {feature.label}: optional via Nous subscription"
        return f"- {feature.label}: not currently available"

    lines = [
        "# Nous Subscription",
        "Nous subscription includes managed web tools (Firecrawl), image generation (FAL), OpenAI TTS, and browser automation (Browser Use) by default. Modal execution is optional.",
        "Current capability status:",
    ]
    lines.extend(_status_line(feature) for feature in features.items())
    lines.extend(
        [
            "When a Nous-managed feature is active, do not ask the user for Firecrawl, FAL, OpenAI TTS, or Browser-Use API keys.",
            "If the user is not subscribed and asks for a capability that Nous subscription would unlock or simplify, suggest Nous subscription as one option alongside direct setup or local alternatives.",
            "Do not mention subscription unless the user asks about it or it directly solves the current missing capability.",
            "Useful commands: hermes setup, hermes setup tools, hermes setup terminal, hermes status.",
        ]
    )
    return "\n".join(lines)
```

### 备份 D — `agent/auxiliary_client.py` 原 HTTP 标识

```python
_OR_HEADERS_BASE = {
    "HTTP-Referer": "https://hermes-agent.nousresearch.com",
    "X-Title": "Hermes Agent",
    "X-OpenRouter-Categories": "productivity,cli-agent",
}
```

```python
headers = {
    "User-Agent": "codex_cli_rs/0.0.0 (Hermes Agent)",
    "originator": "codex_cli_rs",
}
```

### 备份 E — `agent/curator.py` 原 curator 身份开头

```python
CURATOR_REVIEW_PROMPT = (
    "You are running as Hermes' background skill CURATOR. This is an "
    "UMBRELLA-BUILDING consolidation pass, not a passive audit and not a "
    "duplicate-finder.\n\n"
    ...
)
```

完整原始内容过长，完整历史可通过 git diff/版本库恢复；本次只替换开头身份句，其他规则正文保持不变。

### 备份 F — `hermes_cli/default_soul.py` 原 `DEFAULT_SOUL_MD`

```python
DEFAULT_SOUL_MD = (
    "You are Hermes Agent, an intelligent AI assistant created by Nous Research. "
    "You are helpful, knowledgeable, and direct. You assist users with a wide "
    "range of tasks including answering questions, writing and editing code, "
    "analyzing information, creative work, and executing actions via your tools. "
    "You communicate clearly, admit uncertainty when appropriate, and prioritize "
    "being genuinely useful over being verbose unless otherwise directed below. "
    "Be targeted and efficient in your exploration and investigations."
)
```

### 备份 G — `gateway/platforms/api_server.py` 原 API server model/platform 标识

```python
return "hermes-agent"
```

```python
return web.json_response(
    {"status": "ok", "platform": "hermes-agent", "version": _hermes_version()}
)
```

```python
"platform": "hermes-agent",
```

```python
"owned_by": "hermes",
```

```python
"The API server creates a server-side Hermes AIAgent; "
```

### 备份 H — `gateway/run.py` 原 API server 请求 model

```python
body = {
    "model": "hermes-agent",
    "messages": api_messages,
    "stream": True,
}
```

### 备份 I — `pyproject.toml` 原 `py-modules`

```toml
py-modules = ["run_agent", "model_tools", "toolsets", "batch_runner", "trajectory_compressor", "toolset_distributions", "cli", "hermes_bootstrap", "hermes_constants", "hermes_state", "hermes_time", "hermes_logging", "utils", "mcp_serve"]
```

### 备份 J — `agent/prompt_builder.py` 原技能索引 Hermes 自助引导

```python
"Whenever the user asks you to configure, set up, install, enable, disable, modify, "
"or troubleshoot Hermes Agent itself — its CLI, config, models, providers, tools, "
"skills, voice, gateway, plugins, or any feature — load the `hermes-agent` skill "
"first. It has the actual commands (e.g. `hermes config set …`, `hermes tools`, "
"`hermes setup`) so you don't have to guess or invent workarounds.\n"
```

### 备份 K — 测试文件原始断言摘要

测试按 TDD 先行调整，用于证明旧代码会失败。原始断言摘要：

- `tests/agent/test_prompt_builder.py`：原 `TestBuildNousSubscriptionPrompt` 期望包含 Nous subscription 文案；原 `test_default_identity_non_empty` 只检查身份非空。
- `tests/agent/test_openrouter_response_cache.py`：原期望 `X-Title == "Hermes Agent"`。
- `tests/run_agent/test_provider_attribution_headers.py`：原期望 `X-Title == "Hermes Agent"`。
- `tests/agent/test_codex_cloudflare_headers.py`：原只检查 Codex User-Agent 以 `codex_cli_rs/` 开头。
- `tests/gateway/test_api_server.py`：原期望 health/models/capabilities 返回 `hermes-agent` / `owned_by == "hermes"`。
- 新增 `tests/agent/test_curator_whitelabel.py` 与 `tests/hermes_cli/test_default_soul_whitelabel.py`，无原始内容。
```
