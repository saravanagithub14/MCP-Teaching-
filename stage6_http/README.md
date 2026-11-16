# Stage 6: Putting the server on the network (HTTP)

## The big idea in one sentence

The same server can run as a website-style service at a URL, so many clients
can connect to it, even from other computers.

## Two ways to connect

So far, the client **started the server itself** and talked to it through a
private pipe. That's called **stdio**. Now we'll use **HTTP**, the same thing
web browsers use.

Think of **a personal chef versus a restaurant**:

| | stdio (Stages 1 to 5) | HTTP (this stage) |
|---|---|---|
| Like... | A personal chef who works only for you, in your kitchen | A restaurant at an address that anyone can visit |
| Who starts it? | The client starts the server | The server runs by itself |
| How many clients? | One | Many, at the same time |
| Where? | Same computer only | Same computer or anywhere on a network |
| How to find it? | A file path (`my_server.py`) | A URL (`http://127.0.0.1:8765/mcp`) |

The word for "how messages travel" is **transport**. stdio and HTTP are two
different transports. **The tools don't change at all**, only how you reach them.

## The files

| File | Part | What it is |
|---|---|---|
| `http_server.py` | both | The weather server, now running over HTTP. It also counts how many calls it got. |
| `client.py` | 1 | Starts the server, then connects **two** clients (Alice and Bob) to it. |
| `llm_client.py` | 2 | GPT uses the same server, reached by URL. |

---

## Part 1: One server, shared over HTTP

### What changed in the server

Only the last line:

```python
# Stage 1 (stdio)
mcp.run(transport="stdio")

# Stage 6 (HTTP)
mcp.run(transport="streamable-http", host="127.0.0.1", port=port)
```

- `127.0.0.1` means "this computer" (also called *localhost*).
- `port` is like an apartment number at that address. We use `8765`.

The server also keeps a counter, `VISITS`, that goes up every time anyone calls
`get_weather`. That's how we'll prove both clients share one server.

### What changed in the client

Instead of a file path, the client gets a URL:

```python
async with Client(URL) as alice, Client(URL) as bob:
```

`client.py` starts the server for you in the background, waits until it's
ready, connects Alice and Bob, and shuts the server down at the end.

### Run it

```
cd stage6_http
python client.py
```

### What you'll see

```
Server is up at http://127.0.0.1:8765/mcp

alice: {   "city": "Tokyo",   "temp": 68,   "condition": "rainy",   "total_calls_on_server": 1 }
bob  : {   "city": "London",   "temp": 59,   "condition": "cloudy",   "total_calls_on_server": 2 }

The counter went 1 -> 2 across two clients: one shared server.
```

Alice's call made the counter 1. Bob's call made it 2. Two different clients,
**one shared server**.

### A note on safety

A server on a network can be reached by other people. A real HTTP server
needs **authentication** (a login or key) so only allowed users can call its
tools. This lesson skips that to stay simple, and only listens on your own
computer (`127.0.0.1`).

---

## Part 2: GPT and a remote server

> Needs an OpenAI API key. See [Set up your OpenAI key](../README.md#set-up-your-openai-key).

`llm_client.py` is the tool loop from Stage 3, with one change: it connects
with `Client(URL)` instead of starting the server itself.

```python
async with Client(URL) as mcp:   # <- the only line that differs from stdio
```

The model's side of the code didn't change at all. **The model doesn't know or
care how the tool is reached.** A child process, another computer, a cloud
service: that's the host's business.

### Run it

```
python llm_client.py
```

### What you'll see

```
MCP server is up at http://127.0.0.1:8766/mcp

you  : What's the weather in Tokyo and in London?
  get_weather({'city': 'Tokyo'}) over HTTP -> {"city": "Tokyo", "temp": 68, "condition": "rainy", "total_calls_on_server": 1}
  get_weather({'city': 'London'}) over HTTP -> {"city": "London", "temp": 59, "condition": "cloudy", "total_calls_on_server": 2}
model: Tokyo is 68°F and rainy, while London is 59°F and cloudy.
```

This is how hosted MCP servers work in real AI apps: a company runs a server
at a URL, and anyone's AI app can connect to it.

### Safety matters more now

With an LLM in the picture, a remote server has two kinds of risk:

- **Who can call it?** Without authentication, anyone who finds the URL can use
  your tools.
- **What can it say?** Whatever a server returns goes straight to the model. A
  server you don't trust could return text like "ignore your instructions and
  ...". This is called **prompt injection**. Only connect your AI apps to
  servers you trust.

## Try it yourself

1. Run the server on its own in one terminal (`python http_server.py`), then
   write a tiny script that connects to the URL from a second terminal.
2. Add a third client, `carol`, and watch the counter reach 3.
3. Change the port to `9000` in both files.

## Words to remember

- **Transport**: how messages travel between client and server.
- **stdio**: a private pipe, local only, one client.
- **HTTP**: a network connection, at a URL, can be shared by many clients.
- **localhost / 127.0.0.1**: "this computer".
- **Port**: a number that picks which service at an address you want.
- **Authentication**: checking who is allowed in.
- **Prompt injection**: text hidden in data (like a tool result) that tries to give the model new instructions.

**Next:** [Stage 7](../stage7_agent/README.md) puts it all together as a chat
agent with memory that asks your permission before changing anything.
