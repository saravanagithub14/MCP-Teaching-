"""Stage 7 (comparison): the same agent loop with NO LLM. A rule-based planner.

Run agent.py for the LLM version. This file shows what the model is replacing.

    request -> [planner] <-> [host] <-> MCP server(s)

The planner never touches a server. It only sees the tool catalog the host
built from tools/list (names, descriptions, input schemas). Each turn it answers
either "call tool X with args Y" or "done". The host runs the call over MCP and
the result goes back to the planner. Loop until the planner says done.

The planner is plain Python rules. It has no tool names written into it:
  1. Split the request into steps on "then", ";", "." and "?".
  2. For each step, pick the tool whose name and description share the most
     words with the step.
  3. Fill the arguments from `name=value` pairs in the step, then from schema
     defaults, then from the previous step's result (like a pipe).

Any other planner with the same signature (request, history, catalog) -> action
plugs into the same loop unchanged.

Usage:
    python rule_agent.py
    python rule_agent.py "get the weather for city=London, then save a note"
"""
import asyncio, json, re, sys
from host import Host, one_line

STOPWORDS = {"a", "an", "the", "for", "of", "to", "in", "on", "at", "my", "me", "i",
             "please", "and", "then", "it", "its", "about", "is", "what", "whats",
             "s", "can", "you", "all", "every", "this", "that", "with", "get"}


# Different words people use for the same action. Plain English, not AI.
SYNONYMS = {"show": "list", "display": "list", "view": "list",
            "store": "save", "remember": "save", "write": "save", "record": "save"}


def roots(text: str) -> set[str]:
    """Lowercase words, minus filler words, plus simple word forms.

    "notes" also counts as "note", and "saved" also counts as "save", so a
    request and a description match even when the word endings differ.
    """
    out = set()
    for w in re.findall(r"[a-z]+", text.lower()):
        if w in STOPWORDS:
            continue
        w = SYNONYMS.get(w, w)
        if w.endswith("s") and len(w) > 3:
            w = w[:-1]                      # notes -> note
        out.add(w)
        if w.endswith("ed") and len(w) > 4:
            out |= {w[:-1], w[:-2]}         # saved -> save, listed -> list
    return out


def split_steps(request: str) -> list[str]:
    parts = re.split(r",?\s*\bthen\b|[;?!]|\.(?=\s|$)", request, flags=re.I)
    return [p.strip(" ,") for p in parts if p.strip(" ,")]


ARG = re.compile(r"""(\w+)\s*=\s*("[^"]*"|'[^']*'|[^\s,]+)""")


def parse_args(step: str) -> dict[str, str]:
    return {k: v.strip("\"'") for k, v in ARG.findall(step)}


def convert(value: str, kind: str):
    """Turn text into the type the schema asks for."""
    if kind == "integer":
        return int(value)
    if kind == "number":
        return float(value)
    if kind == "boolean":
        return value.lower() in ("true", "yes", "1")
    return value


def summarize(result: str) -> str:
    """Make a previous result short enough to pass along as text."""
    try:
        data = json.loads(result)
    except ValueError:
        return result.replace("\n", ", ")
    if isinstance(data, dict):
        return ", ".join(f"{k}={v}" for k, v in data.items())
    return str(data)


# ---------- the planner: rules only, no AI ----------
class RulePlanner:
    def __call__(self, request: str, history: list[dict], catalog: list[dict]) -> dict:
        steps = split_steps(request)
        if history and history[-1]["result"].startswith("ERROR:"):
            # Don't carry on after a failure: later steps may depend on this one
            return {"type": "done", "text": f"Stopped: {history[-1]['tool']} failed. {history[-1]['result']}"}
        if len(history) >= len(steps):
            done = ", ".join(h["tool"] for h in history)
            return {"type": "done", "text": f"Finished {len(history)} step(s): {done}."}

        step = steps[len(history)]
        tools, matched = self.pick_tool(step, catalog)
        if not tools:
            return {"type": "done", "text": f"Stopped: no tool matches the step '{step}'."}
        if len(tools) > 1:  # a tie: guessing could do the wrong thing, so ask instead
            names = " or ".join(t["name"] for t in tools)
            return {"type": "done", "text": f"Stopped: '{step}' could mean {names}. Please be more specific."}
        tool = tools[0]

        args, missing = self.fill_args(step, tool["input_schema"], history)
        if missing:
            return {"type": "done",
                    "text": f"Stopped: {tool['name']} needs {', '.join(missing)}. "
                            f"Add it to the step, like {missing[0]}=..."}
        why = f"step '{step}' matched words {sorted(matched)}"
        return {"type": "call", "tool": tool["name"], "args": args, "why": why}

    def pick_tool(self, step: str, catalog: list[dict]):
        """Score every tool by shared words. Return the top tool(s) and the words that matched."""
        words = roots(re.sub(ARG, " ", step)) | roots(" ".join(parse_args(step)))
        best, best_score, best_matched = [], 0, set()
        for t in catalog:
            name_words = roots(t["name"].split("__")[-1].replace("_", " "))
            desc_words = roots(t["description"])
            # A word in the tool's name counts double: names are the strongest hint
            score = sum(2 * (w in name_words) + (w in desc_words) for w in words)
            if score > best_score:
                best, best_score, best_matched = [t], score, words & (name_words | desc_words)
            elif score == best_score and score > 0:
                best.append(t)
        return best, best_matched

    def fill_args(self, step: str, schema: dict, history: list[dict]):
        """Fill each argument, trying these sources in order:
        1. name=value written in the step         (city=Tokyo)
        2. the schema's default                   (days defaults to 3)
        3. a Capitalized name in the step         ("weather in Paris" -> Paris)
        4. the previous step's result, as text    (like a pipe in a terminal)
        """
        props = schema.get("properties", {})
        given = parse_args(step)
        names = capitalized_names(re.sub(ARG, " ", step))
        piped = summarize(history[-1]["result"]) if history else None
        args, missing = {}, []
        for name, spec in props.items():
            kind = spec.get("type", "string")
            if name in given:
                args[name] = convert(given[name], kind)
            elif "default" in spec:
                continue  # the server fills in its own default
            elif kind == "string" and names:
                args[name] = names.pop(0)
            elif kind == "string" and piped is not None:
                args[name], piped = piped, None  # only one argument gets the pipe
            elif name in schema.get("required", []):
                missing.append(name)
        return args, missing


def capitalized_names(step: str) -> list[str]:
    """Find names like "Paris" or "New York". The step's first word doesn't count,
    because it is capitalized anyway."""
    words = step.split()[1:]
    text = " ".join(w.strip("?,.!\"'") for w in words)
    return re.findall(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)*\b", text)


# ---------- the agent loop ----------
async def run_agent(request: str, planner, host: Host, max_steps: int = 10) -> str:
    history: list[dict] = []
    for step in range(max_steps):
        action = planner(request, history, host.catalog)
        if action["type"] == "done":
            return action["text"]
        print(f"  step {step + 1}: planner picks {action['tool']}({json.dumps(action['args'])})")
        print(f"          because {action['why']}")
        result = await host.call(action["tool"], action["args"])  # <- the MCP hop
        print(f"          server replied {one_line(result)[:90]}")
        history.append({"tool": action["tool"], "args": action["args"], "result": result})
    return "Stopped: too many steps."


async def main():
    request = " ".join(sys.argv[1:]) or (
        "What is the weather in Tokyo? Then save a note, then show my notes.")
    host = Host()
    await host.start()
    try:
        print(f"tools available: {[t['name'] for t in host.catalog]}\n")
        print("request:", request)
        print("agent  :", await run_agent(request, RulePlanner(), host))
    finally:
        await host.close()


if __name__ == "__main__":
    asyncio.run(main())
