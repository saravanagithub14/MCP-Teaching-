# Stage 3: Smarter tools, and a model that fixes its own mistakes

## The big idea in one sentence

The more precisely you describe a tool's inputs, outputs and errors, the fewer
mistakes the LLM makes, and the faster it recovers from the ones it does make.

## Why this stage matters

A model only knows what your tool's description and schema tell it. If you say
"unit: any text", GPT might send `"kelvin"`, `"celsius"` or `"c"`. If you say
"unit: must be `C` or `F`", it knows exactly what's allowed.

Think of a **form on a website**. A dropdown menu is better than an empty text
box because people can't type something wrong. This stage gives your tools
dropdowns, neat answers and helpful error messages.

## The files

| File | Part | What it is |
|---|---|---|
| `weather_server.py` | both | A server with four tools, each showing one new idea. |
| `client.py` | 1 | Calls each tool directly and prints what happens. |
| `llm_client.py` | 2 | GPT uses the tools in a **loop**, and retries after an error. |

---

## Part 1: The four new ideas

### 1. Allowed values (`Literal`)

```python
def convert_temperature(temp: float, from_unit: Literal["C", "F"], to_unit: Literal["C", "F"]):
```

`Literal["C", "F"]` means "only `C` or `F` are allowed". MCP turns this into
an **enum** (a fixed list of choices) in the schema. The model sees the choices,
and if a bad value like `"K"` is sent anyway, MCP **rejects it before your code
even runs**.

### 2. Structured output (Pydantic models)

```python
class Weather(BaseModel):
    city: str
    temp_f: float = Field(description="Temperature in Fahrenheit")
    condition: str

def get_weather(city: str) -> Weather:
```

**Pydantic** is a library for describing the shape of data. When a tool returns
a `Weather` object, the client gets a clean, labeled answer
(`{'city': 'Tokyo', 'temp_f': 68.0, 'condition': 'rainy'}`) and also an
**output schema** that says what the answer will look like. The
`Field(description=...)` text helps the model understand each value, for
example that the temperature is in Fahrenheit.

### 3. Helpful errors (`ToolError`)

```python
if not 1 <= days <= 7:
    raise ToolError("days must be between 1 and 7")
```

When you can predict a mistake, raise `ToolError` with a clear message. **That
message goes back to the model**, which can read it, fix its call and try again.
You'll watch this happen in Part 2.

### 4. Hidden crashes (any other error)

```python
def buggy() -> str:
    return 1 / 0     # crashes on purpose
```

If your code crashes in a way you didn't plan for, MCP still reports "this
failed", but it **hides the details**. That's on purpose: crash messages can
reveal private stuff like file paths, passwords or database details, and
anything in a tool result ends up in front of the model (and possibly the user).
You only share error text you chose to share with `ToolError`.

### Run it

```
cd stage3_typed_tools
python client.py
```

### What you'll see (shortened)

```
== tools and their contracts ==
- convert_temperature
   input : {... "from_unit": {"enum": ["C", "F"], ...} ...}      <- the dropdown
...
== structured output ==
{'city': 'Tokyo', 'temp_f': 68.0, 'condition': 'rainy'}         <- neat, labeled answer

== bad argument (not in enum) ==
isError: True | ... from_unit   Input should b...               <- "K" was rejected

== error raised inside the tool ==
isError: True | Error executing tool forecast: days must be between 1 and 7   <- your message

== unexpected crash (details hidden from the caller) ==
isError: True | Error executing tool buggy                       <- no details leaked
```

`isError: True` is how MCP says "this call failed". The server doesn't crash;
it just returns a failed result.

---

## Part 2: The tool loop

> Needs an OpenAI API key. See [Set up your OpenAI key](../README.md#set-up-your-openai-key).

### Why we need a loop

In Stage 1 the model got **one** round of tool calls. That breaks down when:

- it needs a second tool after seeing the first result, or
- a tool says "you got that wrong" and the model needs another try.

So `llm_client.py` keeps going until the model stops asking for tools:

```python
for _ in range(max_rounds):
    reply = ask the model (messages + tools)
    if reply has no tool calls:
        return reply.content          # it's finished: this is the answer
    for each tool call:
        run it over MCP
        add the result to messages    # errors too! that's how it learns
```

`max_rounds` is a safety limit, so a confused model can't loop forever (and run
up your bill).

### Run it

```
python llm_client.py
```

### What you'll see

The wording will vary, but look at the **two forecast calls**:

```
The model sees from_unit as: {"enum": ["C", "F"], "title": "From Unit", "type": "string"}

you  : What is 100 degrees Celsius in Fahrenheit?
    convert_temperature({'temp': 100, 'from_unit': 'C', 'to_unit': 'F'}) -> [ok] {"value": 212.0, "unit": "F"}
model: 100°C is 212°F.

you  : Give me a 10-day forecast for London.
    forecast({'city': 'London', 'days': 10}) -> [ERROR] Error executing tool forecast: days must be between 1 and 7
    forecast({'city': 'London', 'days': 7}) -> [ok] {"city": "London", "temp_f": 59.0, ...} ...
model: I can only forecast up to 7 days, so here's the 7-day forecast for London: ...
```

1. The model used `"C"` and `"F"` exactly, because the enum told it to.
2. It asked for 10 days. Nothing in the schema said 10 was too many.
3. Your `ToolError` message came back, the model read it, and it **retried with 7**.
4. It even told the user about the limit.

The model reacted to your error message the way a person would. That's why
good error messages matter so much when an LLM is the caller.

Note that `buggy` is left out of the tools given to the model. It exists only to
show masked errors in Part 1.

## Try it yourself

1. Put the 1-to-7 limit in the schema itself: change `days: int = 3` to
   `days: Annotated[int, Field(ge=1, le=7)] = 3` (import `Annotated` from
   `typing`). Run `client.py`: the schema now shows `"minimum": 1, "maximum": 7`.
   Run `llm_client.py`: does the model still ask for 10 days, now that it can
   see the limit up front?
2. Change the `ToolError` text to something unhelpful like `"bad input"`. Does
   the model still recover?
3. Add `"K"` (Kelvin) to the `Literal` choices, handle it in the function, and
   ask "What is 300 Kelvin in Celsius?".

## Words to remember

- **Type hint**: a label like `str`, `int` or `float` that says what kind of value is expected.
- **Enum**: a fixed list of allowed values.
- **Structured output**: an answer with a known, labeled shape.
- **`isError`**: the flag that says a tool call failed.
- **Tool loop**: keep calling the model and running tools until it gives a final answer.

**Next:** [Stage 4](../stage4_resources_prompts/README.md) shows that MCP
servers can share more than tools: data the host can give the model, and
prompt templates the user can pick.
