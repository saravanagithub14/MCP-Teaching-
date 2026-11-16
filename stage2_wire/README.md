# Stage 2: What's really being sent

## The big idea in one sentence

MCP is just short text messages (in JSON format) passed back and forth, and
you can write them by hand.

## Why this stage matters

In Stage 1 the `mcp` library hid all the details. That can make MCP feel like
magic. In this stage we **don't use the library on the client side at all**.
We type the messages ourselves, so you can see exactly what goes on.

## Some quick background

- **JSON** is a common way to write data as text. It looks like a Python
  dictionary: `{"city": "London"}`.
- **JSON-RPC** is a simple rule for sending requests as JSON. Each request
  says *what to do* (`"method"`) and gives a number (`"id"`) so the reply can be
  matched to it.
- **A pipe** is a connection between two programs. One writes text in, the
  other reads it out. Here the client writes into the server's input and reads
  the server's output.

## The files

| File | Part | What it is |
|---|---|---|
| `my_server.py` | both | The exact same server as Stage 1. Nothing changed. |
| `raw_wire_client.py` | 1 | A client with **no MCP library**. It writes the JSON messages by hand. |
| `llm_to_wire.py` | 2 | Shows GPT's raw tool request next to the MCP message built from it. |

---

## Part 1: The raw MCP messages

### The conversation, step by step

Think of it like a phone call:

| Step | Phone call | MCP message |
|---|---|---|
| 1 | "Hi, I'm Sam." / "Hi Sam, I'm the weather line. I can do X, Y, Z." | `initialize` (the **handshake**) |
| 2 | "Great, let's start." (no reply needed) | `notifications/initialized` |
| 3 | "What can you help me with?" | `tools/list` |
| 4 | "Please check London's weather." | `tools/call` |

Two things to notice:

- **The handshake comes first.** The client and server introduce themselves and
  share what features they support. Nothing else happens until this is done.
- **A message with no `id` gets no reply.** Step 2 has no `id`, so it's a
  *notification*: "just letting you know". Messages with an `id` are requests,
  and the server answers using the same `id`.

### Run it

```
cd stage2_wire
python raw_wire_client.py
```

### What you'll see

`->` means "the client sent this". `<-` means "the server replied with this".

```
-> {"jsonrpc": "2.0", "id": 1, "method": "initialize", ...}
<- {"jsonrpc":"2.0","id":1,"result":{"capabilities":{...},"serverInfo":{"name":"my-first-server",...}}}
-> {"jsonrpc": "2.0", "method": "notifications/initialized"}
-> {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
<- {"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"get_weather","description":"Get the current weather for a city.","inputSchema":{...}}]}}
-> {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "get_weather", "arguments": {"city": "London"}}}
<- {"jsonrpc":"2.0","id":3,"result":{"content":[{"text":"{ \"city\": \"London\", \"temp\": 59, \"condition\": \"cloudy\" }","type":"text"}],"isError":false}}
```

Check these:

- Every reply has the **same `id`** as the request it answers.
- The notification (no `id`) has **no** `<-` line after it.
- The `tools/list` reply contains the same name, description and schema you saw
  in Stage 1. That's where the client got them.

### Try it yourself

1. Change `"London"` to `"Tokyo"` in the `tools/call` message.
2. Ask for a tool that doesn't exist (`"name": "get_pizza"`) and read the error
   reply.
3. Delete the `initialize` step and see what the server does when you skip the
   handshake.

---

## Part 2: From GPT's request to an MCP message

> Needs an OpenAI API key. See [Set up your OpenAI key](../README.md#set-up-your-openai-key).

In Stage 1, the SDK quietly turned GPT's tool request into an MCP call. Here we
do it by hand, so you can see there's nothing hidden. `llm_to_wire.py` still
uses no MCP library. It does the handshake and `tools/list` over the raw pipe,
asks GPT a question, and then **builds the `tools/call` message from GPT's
reply itself**.

### The two translations

**1. MCP tool to OpenAI tool** (so GPT can read the menu). Only the wrapper and
one key name change: MCP says `inputSchema`, OpenAI says `parameters`.

```
MCP    : {"name": "get_weather", "description": "...", "inputSchema": {...}}
OpenAI : {"type": "function", "function": {"name": "get_weather", "description": "...", "parameters": {...}}}
```

**2. GPT's tool call to an MCP request** (so the server can run it). Copy the
name, and turn the arguments from text into JSON.

```
GPT said : {"id": "call_1", "type": "function",
            "function": {"name": "get_weather", "arguments": "{\"city\": \"London\"}"}}
we send  : {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "get_weather", "arguments": {"city": "London"}}}
```

Notice that GPT sends `arguments` as **a string of text** that contains JSON,
while MCP wants a real JSON object. That's why the code calls `json.loads()`.

### Run it

```
python llm_to_wire.py
```

### What you'll see (shortened)

```
== 1. MCP handshake and discovery (same as raw_wire_client.py) ==
  MCP -> {"jsonrpc": "2.0", "id": 1, "method": "initialize", ...}
  ...
== 3. Ask the model ==
  you: Should I take an umbrella in London today?

== 4. The model's raw request ==
  model said: {"id": "call_...", "function": {"arguments": "{\"city\":\"London\"}", "name": "get_weather"}, "type": "function"}

== 5. The same request as an MCP message ==
  MCP -> {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "get_weather", "arguments": {"city": "London"}}}
  MCP <- {"jsonrpc":"2.0","id":3,"result":{"content":[{"text":"{ ... \"condition\": \"cloudy\" }","type":"text"}],"isError":false}}

== 6. Hand the result back to the model ==
  model: It's cloudy and 59°F in London. An umbrella is a good idea, just in case.
```

There are two separate conversations here: **you and GPT** (the OpenAI API) and
**the host and the server** (MCP). The host is the bridge between them.

## Words to remember

- **JSON-RPC**: the message format MCP uses.
- **Handshake (`initialize`)**: the first message, where both sides introduce
  themselves.
- **Request**: a message with an `id`, which gets a reply.
- **Notification**: a message without an `id`, which gets no reply.
- **Host**: the program in the middle that talks to both the LLM and the servers.

**Next:** [Stage 3](../stage3_typed_tools/README.md) makes tools smarter with
better inputs, structured outputs and error messages the model can learn from.
