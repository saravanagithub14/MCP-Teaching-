# Stage 4: Tools, resources and prompts

## The big idea in one sentence

An MCP server can offer three kinds of things, and the difference between them
is **who decides when they're used**: the model, the app or the user.

## The three kinds

Think of a **cooking class**:

| MCP name | Cooking class | Who decides? | Used for |
|---|---|---|---|
| **Tool** | The student grabs the oven or the mixer when needed | The **model** | Doing actions |
| **Resource** | The teacher hands out a recipe sheet before class | The **app (host)** | Background data to read |
| **Prompt** | You pick "Today: make pasta" from a list of lessons | The **user (you)** | Ready-made instructions |

- **Tool**: the LLM chooses to call it in the middle of answering
  ("I need the weather, so I'll call `get_weather`").
- **Resource**: read-only data, like a file. The app chooses to read it and
  give it to the model as context. The model doesn't ask for it. Resources have
  addresses that look like web links, for example `weather://cities`.
- **Prompt**: a saved message template. In AI apps, these often appear as a
  menu or a slash command (`/travel_advice`) that you pick yourself. The
  filled-in template becomes your message to the model.

Same server, three different "owners" of the decision.

## The files

| File | Part | What it is |
|---|---|---|
| `weather_server.py` | both | One server with a tool, two resources and a prompt. |
| `client.py` | 1 | Lists and uses each of the three kinds directly. No LLM. |
| `llm_client.py` | 2 | Uses all three the way an AI app does, with GPT. |

---

## Part 1: The three kinds, without an LLM

### How the server works

```python
@mcp.tool()                          # TOOL: the model calls it
def get_weather(city: str) -> dict: ...

@mcp.resource("weather://cities")     # RESOURCE: a fixed address
def list_cities() -> str: ...

@mcp.resource("weather://city/{name}")  # RESOURCE TEMPLATE: an address with a blank to fill in
def city_report(name: str) -> str: ...

@mcp.prompt()                        # PROMPT: a reusable message for the user to pick
def travel_advice(city: str, days: int = 3) -> str: ...
```

A **resource template** is like a fill-in-the-blank address. `{name}` is the
blank. Reading `weather://city/tokyo` fills the blank with `tokyo`, so
`city_report("tokyo")` runs.

A **prompt** doesn't run the model by itself. It just fills in a template and
returns the text. The app then sends that text to the model.

### Run it

```
cd stage4_resources_prompts
python client.py
```

### What you'll see

```
== TOOLS (model decides) ==
['get_weather']

== RESOURCES (app attaches) ==
- weather://cities
- template: weather://city/{name}
read weather://cities -> london, new york, tokyo
read weather://city/tokyo -> Tokyo: 68F and rainy

== PROMPTS (user picks) ==
- travel_advice ['city', 'days']
rendered -> I'm visiting London for 2 days. Use the get_weather tool to check the weather there, then tell me what to pack. Keep it under 80 words.
```

Notice the prompt tells the model to use the `get_weather` tool. Prompts and
tools often work together: you pick the prompt, and the model then calls the tool.

---

## Part 2: All three, with GPT

> Needs an OpenAI API key. See [Set up your OpenAI key](../README.md#set-up-your-openai-key).

`llm_client.py` acts like a small AI app. Each primitive is decided by a
different party:

| Step | Who decides | What happens in the code |
|---|---|---|
| 1 | **You** pick a prompt | `get_prompt("travel_advice", {"city": "Tokyo", "days": "3"})` fills the template. The result becomes the user message. |
| 2 | **The host** adds a resource | It reads `weather://cities` and puts the list into the **system message**: "Weather data exists only for these cities: ..." |
| 3 | **The model** calls a tool | While answering, GPT decides it needs `get_weather` and asks for it. |

A **system message** is a message at the very start of the conversation that
sets the model's job and rules. Users don't see it. It's a common place for an
app to put resource data.

One detail: prompt arguments always travel as **text**, so `days` is sent as
`"3"`, not `3`. The server converts it back to a number.

### Run it

```
python llm_client.py
python llm_client.py London 2
python llm_client.py Paris 4
```

### What you'll see

```
[PROMPT, user picked]   travel_advice(city=Tokyo, days=3)
                        -> "I'm visiting Tokyo for 3 days. Use the get_weather tool to check the weather there, then tell me what to pack. Keep it under 80 words."
[RESOURCE, host added]  weather://cities -> ['london', 'new york', 'tokyo']
  [TOOL, model decided]  get_weather({'city': 'Tokyo'}) -> {   "city": "Tokyo",   "temp": 68,   "condition": "rainy" }

model: Tokyo will be around 68°F and rainy. Pack a light rain jacket, an umbrella,
       comfortable waterproof shoes and a couple of layers for the evenings.
```

Try `Paris`. The server has no data for it, and the resource told the model so.
A good model will say it has no data instead of making up the weather. That's
the resource doing its job: giving the model facts it couldn't know otherwise.

## Try it yourself

1. Add a resource `weather://hottest` that returns the hottest city, and add it
   to the system message too. Ask a question that needs it.
2. Write a second prompt, `compare_cities(city_a, city_b)`, and change
   `llm_client.py` to use it.
3. Remove the resource from the system message and ask about Paris again. Does
   the model behave differently?

## Words to remember

- **Tool**: an action the model decides to take.
- **Resource**: data the app decides to give the model as context.
- **Resource template**: a resource address with a blank in it, like `{name}`.
- **Prompt**: a message template the user picks.
- **System message**: hidden instructions at the start of a chat that set the model's job.
- **URI**: an address for a resource, like `weather://cities`.

**Next:** [Stage 5](../stage5_multi_server/README.md) connects one model to
**several** servers at once. That's where MCP really pays off.
