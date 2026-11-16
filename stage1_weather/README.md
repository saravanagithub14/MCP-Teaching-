# Stage 1: Your first MCP server, and your first LLM using it

## The big idea in one sentence

You write a normal Python function, MCP shares it, and an LLM like GPT can then
use it to answer questions it couldn't answer on its own.

## First, what is MCP?

An LLM on its own can only write text. Ask GPT "what's the weather in Tokyo
right now?" and it has to guess, because it has no way to look anything up.

**MCP (Model Context Protocol)** is a set of rules that lets AI apps connect
models to outside programs, called **servers**, that *can* do things.

Think of a **restaurant**:

| Restaurant | MCP |
|---|---|
| The kitchen, which can cook dishes | The **server**, which has tools (functions) |
| The menu, which lists the dishes | The **tool list**, which says what the server can do |
| The waiter, who takes orders to the kitchen | The **client/host**, the program in the middle |
| The customer, who reads the menu and orders | The **LLM**, which reads the tool list and asks for a tool |

The customer never walks into the kitchen. They read the menu and order, and
the waiter does the rest. The LLM works the same way.

## The files

| File | Part | What it is |
|---|---|---|
| `my_server.py` | 1 | The **server**, the kitchen. It has one tool: `get_weather`. |
| `test_client.py` | 1 | A **client**. It asks what tools exist, then uses one. No LLM. |
| `llm_chat.py` | 2 | The same, but **GPT** decides when to use the tool. |

---

## Part 1: The server and a client (no LLM)

### How the server works

```python
mcp = MCPServer("my-first-server")      # 1. Make a server and give it a name

@mcp.tool()                             # 2. This line turns the function into a tool
def get_weather(city: str) -> dict:
    """Get the current weather for a city."""   # 3. This text becomes the tool's description
    ...

mcp.run(transport="stdio")              # 4. Start the server and wait for requests
```

That's all it takes. Some notes:

- **`@mcp.tool()`** is a *decorator*. It's a tag that says "share this
  function with clients".
- **The docstring** (the text in triple quotes) becomes the tool's
  description. In Part 2 you'll see that **the LLM reads it to decide whether
  to use the tool**, so write it as clearly as you'd explain it to a person.
- **`city: str`** is a *type hint*. MCP reads it and tells the client "this
  tool needs a `city`, and it must be text". You never write that rule by hand.
- The weather data is **fake** (made up in a dictionary), so you don't need a
  weather API.

### How the client works

1. **Connect.** It starts `my_server.py` as a background program and talks to
   it through its input and output. This is called **stdio**.
2. **Discover.** It asks the server "what tools do you have?" (`list_tools`).
3. **Call.** It runs a tool by name: `call_tool("get_weather", {"city": "New york"})`.

### Run it

```
cd stage1_weather
python test_client.py
```

You don't need to start the server yourself. The client starts it for you.

### What you'll see

```
Available tools:
  - get_weather: Get the current weather for a city.
    input schema: {'city': {'title': 'City', 'type': 'string'}}

==================================================

Weather result: {
  "city": "New york",
  "temp": 72,
  "condition": "sunny"
}
```

Look at the `input schema` line. Nobody wrote it. MCP built it from
`city: str`. Notice also that **we** chose to call `get_weather` and **we**
typed "New york". Part 2 hands those decisions to the model.

---

## Part 2: Let GPT use the tool

> Needs an OpenAI API key. See [Set up your OpenAI key](../README.md#set-up-your-openai-key).

### What happens, step by step

```
 1. llm_chat.py asks the server for its tools                 (MCP: tools/list)
 2. It sends GPT the question + the tool list                 (OpenAI API)
 3. GPT replies: "please call get_weather with city=Tokyo"    (a "tool call")
 4. llm_chat.py runs that call on the server                  (MCP: tools/call)
 5. It sends the result back to GPT                           (OpenAI API)
 6. GPT writes the final answer in plain English
```

**GPT never runs anything.** In step 3 it only *asks*. Our script is the
waiter: it takes the order to the kitchen (the MCP server) and brings the food
back.

### The translation

MCP and OpenAI both describe a tool with the same three facts (a name, a
description and a JSON schema for the inputs), just wrapped differently. So
connecting them takes a few lines:

```python
def to_openai_tool(tool):
    return {"type": "function", "function": {
        "name": tool.name,                  # what to call
        "description": tool.description,    # when to call it (the model reads this!)
        "parameters": tool.input_schema,    # what inputs it needs
    }}
```

### Run it

```
python llm_chat.py
python llm_chat.py "Is it sunny in New York?"
```

### What you'll see

The model's wording will differ each time, but the shape is always this:

```
tools given to the model: ['get_weather']

you  : What's the weather like in Tokyo right now?
  model asks for get_weather({'city': 'Tokyo'})
  MCP server replied {   "city": "Tokyo",   "temp": 68,   "condition": "rainy" }
model: It's currently 68°F and rainy in Tokyo, so bring an umbrella!
```

GPT chose the tool, filled in `city` itself, and turned the raw data into a
friendly sentence.

## Try it yourself

1. Add `"paris"` to `weather_data`, then ask `python llm_chat.py "Weather in Paris?"`.
2. Ask something unrelated: `python llm_chat.py "Tell me a joke"`. The model
   answers without the tool. It only uses tools when they help.
3. Change the docstring to `"Does stuff."` and ask about Tokyo again. Does the
   model still find the tool? This is why descriptions matter.
4. Add a second tool, like `def add(a: int, b: int) -> int`, and ask
   "what is 1234 + 5678?".

## Words to remember

- **Server**: the program that has the tools.
- **Client**: the program that connects to a server and calls its tools.
- **LLM**: a large language model, such as GPT. It reads and writes text.
- **Tool**: a function the server shares.
- **Schema**: a description of what inputs a tool needs (made from type hints).
- **Tool call**: the model's request to run a tool. It's a request, not an action.

**Next:** [Stage 2](../stage2_wire/README.md) looks under the hood at the raw
messages, including what GPT's tool call looks like before it becomes MCP.
