# Stage 7: A real chat agent

## The big idea in one sentence

An **agent** is an LLM in a loop: it reads your message, calls tools, reads the
results and keeps going until the job is done, while remembering the
conversation and asking your permission before doing anything risky.

## What's new in this stage

You already built the tool loop (Stage 3) and the multi-server host (Stage 5).
This stage adds the three things that turn a script into a usable agent:

| New idea | What it means | Why it matters |
|---|---|---|
| **Memory** | The message list is kept between your messages | "Save **that** as a note" works, because the model can still see what "that" was |
| **System message** | Standing instructions at the start of the chat | Sets the agent's job and rules ("if a tool fails, fix your call") |
| **Approval** | The agent asks you before running tools that change data | A model can misunderstand. You stay in control of anything that matters. |

## The files

| File | What it is |
|---|---|
| `agent.py` | The chat agent: GPT + memory + approval. **The main file.** |
| `rule_agent.py` | The same loop with **no LLM**: a rule-based planner, for comparison. |
| `host.py` | The general host from Stage 5 (now also reads tool annotations). |
| `servers.json` | Which servers the host connects to. |
| `weather_server.py` | The weather server, with its tool marked read-only. |
| `notes_server.py` | The notes server, now with annotations and a `clear_notes` tool. |

---

## The most important thing to understand

**The model never talks to the servers directly.**

Think of a **manager and an assistant**:

- The **manager (the LLM)** reads the list of what the assistant can do, then
  gives instructions: "Check Tokyo's weather."
- The **assistant (the host)** actually picks up the phone, calls the weather
  server, and reports back. For anything risky, the assistant **checks with
  you first**.
- The manager reads the report and decides the next step: "Now save a note."

```
   you <--chat--> [ Agent ] <-----> OpenAI model
                      |
                      +--> host --MCP--> weather server
                                --MCP--> notes server
```

## How it works

### Memory

In earlier stages, every question started a fresh `messages` list. Here the
agent keeps one list for the whole chat:

```python
self.messages = [{"role": "system", "content": SYSTEM}]   # created once

async def ask(self, text):
    self.messages.append({"role": "user", "content": text})  # added to, never reset
    ...
```

Every reply, tool call and tool result is added to it. The model has no memory
of its own. **It only "remembers" because we send it the whole conversation
every time.** That also means long chats cost more, since every request carries
all the history.

### Approval, driven by MCP annotations

MCP lets a server attach **annotations** (hints) to each tool, saying what kind
of thing it does:

```python
@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def list_notes() -> list[str]: ...           # only reads: safe

@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False))
def add_note(text: str) -> str: ...          # changes data: ask first

@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True))
def clear_notes() -> str: ...                # deletes data: definitely ask first
```

The host reads these hints, and the agent follows one simple rule: **read-only
tools run automatically, everything else needs your "y"**. If you say no, the
model is told "The user declined to run this tool" and carries on without it.

Annotations are *hints* from the server, not guarantees. A badly written or
untrusted server could mark a dangerous tool as read-only. Real AI apps let
the user decide which servers to trust for exactly this reason.

### The loop

The same loop as Stage 3, with the two additions above:

1. Add your message to memory.
2. Send the whole memory plus the tool list to the model.
3. If it replies with plain text, that's the answer. Stop.
4. Otherwise, for each tool call: check approval, run it over MCP, add the
   result to memory.
5. Go back to step 2 (at most `max_rounds` times).

## Run it

> Needs an OpenAI API key. See [Set up your OpenAI key](../README.md#set-up-your-openai-key).

Chat with it:

```
cd stage7_agent
python agent.py
```

Or run a short scripted chat that auto-approves tools:

```
python agent.py --demo
```

## What you'll see

A chat session (your wording and the model's will differ):

```
model: gpt-5.4-mini
tools: weather__get_weather (read-only), notes__add_note, notes__list_notes (read-only), notes__clear_notes

Chat with the agent. Type 'quit' to leave.

you  : What's the weather in Tokyo?
  [tool] weather__get_weather({"city": "Tokyo"}) -> {"city": "Tokyo", "temp": 68, "condition": "rainy"}
agent: It's 68°F and rainy in Tokyo.

you  : Save that as a note, then show me my notes.
  allow notes__add_note({"text": "Tokyo: 68°F and rainy"})? [y/N] y
  [tool] notes__add_note({"text": "Tokyo: 68°F and rainy"}) -> saved note #1
  [tool] notes__list_notes({}) -> Tokyo: 68°F and rainy
agent: Saved! Your notes: "Tokyo: 68°F and rainy".

you  : Now delete all my notes.
  allow notes__clear_notes({})? [y/N] n
  [declined] notes__clear_notes({})
agent: Okay, I didn't delete anything. Your note is still saved.
```

Things to notice:

1. **Memory:** "Save **that**" worked. The model looked back at the weather
   result in the conversation.
2. **No approval needed** for `get_weather` and `list_notes`, because they're
   read-only.
3. **Approval asked** for `add_note` and `clear_notes`. Saying "n" stopped the
   delete, and the model adjusted its answer.

## LLM vs rules: compare with `rule_agent.py`

`rule_agent.py` drives the **same kind of loop** with a planner made of plain
Python rules: it matches words in your request against tool names and
descriptions, and fills arguments from `name=value` pairs. It needs no key:

```
python rule_agent.py
python rule_agent.py "Check the weather in London, then save a note"
```

Try the same requests on both:

| Request | `rule_agent.py` (rules) | `agent.py` (LLM) |
|---|---|---|
| "weather in Tokyo, then save a note" | Works | Works |
| "how warm is it in Tokyo?" | Fails: no word matches "weather" | Works: it knows "warm" is about weather |
| "save that as a note" (in a chat) | Can't: no memory of "that" | Works: it reads the conversation |
| "Compare Tokyo and London, save the warmer one" | Can't compare or decide | Works: it reasons over both results |
| Same request, run twice | Always identical | May word things differently |
| Cost and setup | Free, offline | Needs a key, costs per request |

Both talk to the servers through the same host and the same MCP calls. **MCP
doesn't change. Only the decision-maker does.** That's why an LLM is the usual
choice: it understands requests the rules never could.

## Try it yourself

1. Change `SYSTEM` in `agent.py` to "Always answer like a pirate." and chat
   again. The system message shapes every reply.
2. Mark `add_note` as `read_only_hint=True` in `notes_server.py`. The agent now
   saves notes without asking. (This is why annotations are only hints!)
3. Ask "Compare the weather in all the cities you have data for, then save a
   summary." Watch how many tool calls it plans.
4. Add the Stage 3 server to `servers.json` as
   `"typed": {"command": "python", "args": ["../stage3_typed_tools/weather_server.py"]}`
   and ask for a 10-day forecast. The `ToolError` retry from Stage 3 now
   happens inside a chat.

## Words to remember

- **Agent**: an LLM that uses tools in a loop until a task is done.
- **Memory**: the conversation history, re-sent to the model on every request.
- **System message**: standing instructions that set the agent's job and rules.
- **Annotations**: hints from a server about what each tool does (read-only, destructive...).
- **Human in the loop**: a person approves risky actions before they happen.

## You made it!

You've now built every piece of an AI app with MCP yourself: servers, clients,
the raw messages, typed tools, resources and prompts, a multi-server host, an
HTTP server, and a chat agent with memory and approvals. Real AI apps that
support MCP are bigger versions of exactly these ideas.

See the [main README](../README.md) for ideas on what to build next.
