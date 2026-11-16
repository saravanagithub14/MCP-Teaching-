# Stage 5: One app, many servers

## The big idea in one sentence

One app (the **host**) can connect to many MCP servers at the same time,
combine all their tools into one list, and give that whole list to the model.

## Why this is the whole point of MCP

Think of **phone chargers**. Years ago, every phone brand had its own plug,
so you needed a different cable for every phone. Then USB-C came along: one
plug that works with everything.

MCP is a USB-C plug for AI apps:

- **Without MCP:** every AI app needs special code for every service. 5 apps and
  10 services means 5 x 10 = **50** custom connections.
- **With MCP:** each AI app learns MCP once, and each service learns MCP once.
  5 + 10 = **15** pieces of work, and everything works with everything.

## New word: host

So far we've had a **client** talking to a **server**. Now there's a third role:

- **Host**: the AI app the user actually runs (a chat app, a code editor...).
  It holds **one client for each server** and manages them all.

```
              +--> client --> weather server
   HOST ------|
              +--> client --> notes server
```

## The files

| File | Part | What it is |
|---|---|---|
| `servers.json` | both | The **config file**: which servers to start, and how. |
| `weather_server.py` | both | The weather server from Stage 4. |
| `notes_server.py` | both | A new, unrelated server that saves short notes. |
| `host.py` | 1 | A small, general host. It reads the config, connects to every server and merges their tools. |
| `chat.py` | 2 | Gives the merged tool list to GPT, which mixes tools from both servers. |

---

## Part 1: A host for many servers

### The config file

The host doesn't have any server names written into its code. It reads them
from `servers.json`:

```json
{
  "servers": {
    "weather": { "command": "python", "args": ["weather_server.py"] },
    "notes":   { "command": "python", "args": ["notes_server.py"] }
  }
}
```

Each entry says: "to start this server, run this **command** with these
**args**". Most real MCP host apps use a config file shaped just like this.
To add a server, you add a line here. **You don't touch the host's code.**

### How the host works

1. **Read the config.** `load_config()` turns each entry into launch settings.
   `"python"` is swapped for the exact Python that's running the host, so it
   works inside any virtual environment.

2. **Connect and collect.** For each server, the host starts a client, asks for
   its tools (`tools/list`), and adds them to one big list (the **catalog**).

3. **Add a prefix to each name.** What if two servers both have a tool called
   `search`? To avoid a mix-up, the host puts the server's name in front:
   `weather__get_weather`, `notes__add_note`. This is called **namespacing**.

4. **Send each call to the right place.** When someone calls
   `notes__add_note`, the host looks up the prefix, sees `notes`, and passes the
   call to the notes server. This is called **routing**.

5. **Return the whole result.** A result can hold several pieces (a list of
   notes comes back as one piece per note), so the host joins them all. If the
   server reports a failure, the host adds `ERROR:` in front so the caller can
   tell.

The host doesn't know what weather or notes are. It only speaks MCP.

### Run it

```
cd stage5_multi_server
python host.py
```

### What you'll see

```
Connected to 2 servers from servers.json

Merged tool catalog:
  weather__get_weather   Get the current weather for a city.
  notes__add_note        Save a short note.
  notes__list_notes      List every note.

Routing calls to different servers:
  weather__get_weather   -> {"city": "London", "temp": 59, "condition": "cloudy"}
  notes__add_note        -> saved note #1
  notes__add_note        -> saved note #2
  notes__list_notes      -> pack an umbrella | charge the phone
```

Three tools from two different servers, all in one list, and each call went to
the right server.

---

## Part 2: One model, two servers

> Needs an OpenAI API key. See [Set up your OpenAI key](../README.md#set-up-your-openai-key).

`chat.py` takes the host's merged catalog, translates it into OpenAI tools (the
same `to_openai_tool` as before), and runs the tool loop from Stage 3. When the
model asks for a tool, the host's `call()` routes it to the right server.

**The model has no idea there are two servers.** It just sees one list of
tools. The prefix (`weather__`, `notes__`) is the only hint, and the host
handles all the routing.

### Run it

```
python chat.py
python chat.py "Compare London and Tokyo, then save the warmer city as a note"
```

### What you'll see

```
tools the model can use: ['weather__get_weather', 'notes__add_note', 'notes__list_notes']

you  : What's the weather in London and Tokyo? Save a note comparing them, then show me all my notes.
  weather__get_weather({'city': 'London'})  --routed to 'weather' server--> {"city": "London", "temp": 59, ...}
  weather__get_weather({'city': 'Tokyo'})  --routed to 'weather' server--> {"city": "Tokyo", "temp": 68, ...}
  notes__add_note({'text': 'Tokyo (68F, rainy) is warmer than London (59F, cloudy).'})  --routed to 'notes' server--> saved note #1
  notes__list_notes({})  --routed to 'notes' server--> Tokyo (68F, rainy) is warmer than London (59F, cloudy).
model: Tokyo is warmer at 68°F (rainy) vs London's 59°F (cloudy). I saved a note comparing them. ...
```

Look at three things:

1. **Two weather calls at once.** The model can ask for several tools in a
   single reply (a *parallel tool call*). The loop runs each one.
2. **It wrote the note text itself.** It read both weather results and summed
   them up. No code of ours did that.
3. **Tools from two servers, in one plan.** That's MCP's M + N promise working.

## Try it yourself

1. Write a third server (for example `calculator_server.py` with an `add` tool),
   add it to `servers.json`, and run again. It shows up in the catalog with no
   code changes. Then ask `chat.py` a question that needs all three servers.
2. Point a config entry at a server in another folder, for example
   `"args": ["../stage3_typed_tools/weather_server.py"]`, under a new name like
   `"typed"`. Both weather servers now work side by side, thanks to the
   prefixes.
3. Stop and restart `host.py`. Are the notes still there? (Hint: notes are kept
   in memory, so they disappear when the server stops.)

## Words to remember

- **Host**: the app that manages many clients.
- **Config file**: the list of servers the host should start.
- **Catalog**: the combined list of tools from all servers.
- **Namespacing**: adding a prefix (`weather__`) so tool names don't clash.
- **Routing**: sending each call to the server that owns the tool.

**Next:** [Stage 6](../stage6_http/README.md) moves a server onto the network,
so many clients can share it.
