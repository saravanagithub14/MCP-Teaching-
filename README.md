# Learn MCP by connecting an LLM to your own tools

On its own, a large language model (LLM) like GPT can only write text. It can't
check the weather, read your notes or save a file. **MCP (Model Context
Protocol)** is an open standard that fixes this: you wrap your code as an *MCP
server*, and any AI app can discover it and let its model use it.

This course builds that up one idea at a time, in Python, using the official
`mcp` SDK and an **OpenAI** model.

## How each stage works

Every stage has two parts:

- **Part 1: the MCP idea.** Plain MCP, no LLM. You see exactly what the
  protocol does. Runs free and offline.
- **Part 2: add the LLM.** The same idea with an OpenAI model in charge of
  choosing the tools. Needs an API key ([setup below](#set-up-your-openai-key)).

Each folder runs on its own and has its own beginner-friendly README.

| Stage | Folder | MCP idea (part 1) | With the LLM (part 2) |
|---|---|---|---|
| 1 | [`stage1_weather`](stage1_weather/README.md) | A server offers a tool, a client calls it | GPT calls your tool to answer a question |
| 2 | [`stage2_wire`](stage2_wire/README.md) | MCP is JSON-RPC messages over a pipe | GPT's tool request, translated into a raw MCP message |
| 3 | [`stage3_typed_tools`](stage3_typed_tools/README.md) | Type hints become schemas, enums, errors | A tool loop: GPT reads an error and fixes its own call |
| 4 | [`stage4_resources_prompts`](stage4_resources_prompts/README.md) | Tools, resources and prompts | User picks a prompt, host adds a resource, model calls a tool |
| 5 | [`stage5_multi_server`](stage5_multi_server/README.md) | A host merges many servers | GPT mixes tools from two servers in one answer |
| 6 | [`stage6_http`](stage6_http/README.md) | The same server over HTTP | GPT uses a remote server reached by URL |
| 7 | [`stage7_agent`](stage7_agent/README.md) | The agent loop with a rule-based planner | A chat agent with memory that asks before changing data |

Run everything: `bash run_all.sh` (part 2 of each stage is skipped if no key is set).

## The one picture to remember

```
   you --> [ host app ] <------> OpenAI model
                |       tool list  ^   |  "please call get_weather(city=Tokyo)"
                |       + results  |   v
                +--MCP--> weather server
                +--MCP--> notes server
```

- The **model** never runs code and never talks to a server. It reads the tool
  list and *asks* for calls.
- The **host** (the program in the middle) does every MCP call and passes
  results back.
- The **servers** don't know an LLM exists. They just answer MCP requests.

## Setup

```
pip install -r requirements.txt
```

### Set up your OpenAI key

1. Create an API key on the OpenAI platform website (the "API keys" page of
   your account). API usage is billed per request. The demos here are small,
   but set a monthly spending limit in your account to be safe.
2. Put the key in an environment variable called `OPENAI_API_KEY`:

   ```
   # Windows PowerShell (this window only)
   $env:OPENAI_API_KEY = "sk-..."

   # Windows, saved for every new window
   setx OPENAI_API_KEY "sk-..."

   # macOS / Linux / Git Bash
   export OPENAI_API_KEY="sk-..."
   ```

3. Test it: `cd stage1_weather` then `python llm_chat.py`.

**Never paste your key into a code file** or commit it to git. The scripts read
it from the environment, so it never needs to be in the code.

### Choosing a model

The scripts use `gpt-5.4-mini` by default, a small, cheap model that supports
tool calling. To use another one, set `OPENAI_MODEL`:

```
$env:OPENAI_MODEL = "gpt-5.4"        # PowerShell
export OPENAI_MODEL="gpt-5.4"        # macOS / Linux
```

OpenAI's model list changes over time. If the default stops working, pick any
current model that lists "function calling" as supported.

### Free option: a local model

The scripts use OpenAI's *Chat Completions* format, which many other tools also
speak. To run a model on your own computer (for example with Ollama), point the
scripts at it:

```
$env:OPENAI_BASE_URL = "http://localhost:11434/v1"
$env:OPENAI_API_KEY  = "local"        # any text; local servers don't check it
$env:OPENAI_MODEL    = "qwen2.5"      # a local model that supports tools
```

Small local models make more mistakes choosing tools than OpenAI's models, which
is itself a useful lesson.

## Talking points per stage

**1. The starting point.** Connect, `tools/list`, `tools/call`. Then the twist:
the tool list goes to GPT, and GPT decides to call `get_weather`. The model
only *asks*. Our script does the call. The docstring is what the model reads to
decide, so it's really a prompt.

**2. Under the hood.** The `->` and `<-` lines are the whole protocol. The LLM
part shows that turning GPT's `tool_call` into an MCP `tools/call` is copying
two fields. MCP and OpenAI describe tools with the same three facts: name,
description, JSON Schema.

**3. Typed tools.** `Literal["C","F"]` becomes an enum the model reads, so it
sends valid values. `ToolError` sends your message back to the model, and the
loop lets it retry (watch it ask for 10 days, get told 1 to 7, and retry with
7). Unexpected exceptions are masked so internals never reach the model.

**4. Three primitives.** Tool: model-controlled. Resource: app-controlled (the
host pastes it into the system message). Prompt: user-controlled (a template
like a slash command). Same server, three different owners of the decision.

**5. Many servers.** Without MCP, every AI app needs custom code for every
service (M x N). With it, each side implements MCP once (M + N). The model sees
one merged list and never knows there are two servers. Names are namespaced
(`weather__get_weather`) to avoid clashes.

**6. HTTP.** Only the transport changed. The model code is identical. Stdio is
local and one-to-one; HTTP is remote and shared. A network server needs auth.

**7. The agent.** Memory (keep the message list), a system message, and human
approval for tools that change data, driven by MCP tool annotations. Compare
`agent.py` with `rule_agent.py`: same loop, but the LLM understands "save that"
where the rules can't.

## Ideas for next steps

- Swap the mock weather for a real public weather API
- Save notes to SQLite so they survive a restart
- Wire your server into a desktop AI app that supports MCP and watch it work there
- Port the agent to OpenAI's newer *Responses* API
- Add auth to the HTTP server
- Stream the model's answer word by word

A note on **sampling** (a server asking the host's LLM to write something):
older tutorials teach it, but the MCP SDK used here marks it deprecated as of
2026-07-28, so this course leaves it out.

## SDK notes

Written against the official `mcp` Python SDK 2.x and the `openai` Python SDK
2.x. If you've seen older examples that use the separate `fastmcp` package, the
server code is nearly identical:

| fastmcp | This project (mcp 2.x) |
|---|---|
| `from fastmcp import FastMCP` | `from mcp.server.mcpserver import MCPServer` |
| `@mcp.tool` | `@mcp.tool()` |
| `Client("my_server.py")` | `Client(StdioServerParameters(command=..., args=[...]))` |
