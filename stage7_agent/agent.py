"""Stage 7: a real chat agent. OpenAI model + host + MCP servers.

    you <--chat--> [ Agent ] <--> OpenAI model
                       |
                       +--> host --> weather server
                                 --> notes server

New vs earlier stages:
  - MEMORY: the conversation is kept between your messages, so "save that"
    works because the model can still see what "that" was.
  - APPROVAL: before running a tool that changes or deletes data, the agent
    asks you. It reads each tool's annotations (read_only_hint) to decide.
  - A SYSTEM MESSAGE sets the model's job and rules for the whole chat.

Usage:
    python agent.py           chat with it (type 'quit' to leave)
    python agent.py --demo    run a short scripted chat, auto-approving tools
"""
import asyncio, json, os, sys

from openai import AsyncOpenAI
from host import Host, one_line

MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
SYSTEM = (
    "You are a helpful assistant with access to tools. Use a tool whenever it gives "
    "a better answer than guessing. If a tool returns an error, read it and fix your "
    "call. If the user declines a tool, don't retry it; say what you couldn't do. "
    "Keep answers short."
)


def to_openai_tool(entry: dict) -> dict:
    return {"type": "function", "function": {
        "name": entry["name"], "description": entry["description"], "parameters": entry["input_schema"]}}


class Agent:
    def __init__(self, llm: AsyncOpenAI, host: Host, approve, max_rounds: int = 8):
        self.llm, self.host, self.approve, self.max_rounds = llm, host, approve, max_rounds
        self.tools = [to_openai_tool(t) for t in host.catalog]
        self.read_only = {t["name"]: t["read_only"] for t in host.catalog}
        self.messages = [{"role": "system", "content": SYSTEM}]  # the memory

    async def ask(self, text: str) -> str:
        self.messages.append({"role": "user", "content": text})
        for _ in range(self.max_rounds):
            reply = (await self.llm.chat.completions.create(
                model=MODEL, messages=self.messages, tools=self.tools)).choices[0].message
            self.messages.append(reply.model_dump(include={"role", "content", "tool_calls"}, exclude_none=True))  # keep every turn
            if not reply.tool_calls:
                return reply.content
            for call in reply.tool_calls:
                result = await self.run_tool(call.function.name, call.function.arguments)
                self.messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
        return "(stopped: too many rounds)"

    async def run_tool(self, name: str, raw_args: str) -> str:
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError:
            return "ERROR: the arguments were not valid JSON"  # models can slip; let it retry
        label = f"{name}({json.dumps(args)})"
        if not self.read_only.get(name, False) and not await self.approve(label):
            print(f"  [declined] {label}")
            return "The user declined to run this tool."
        result = await self.host.call(name, args)  # <- the MCP hop
        print(f"  [tool] {label} -> {one_line(result)[:80]}")
        return result


async def ask_user(label: str) -> bool:
    answer = await asyncio.to_thread(input, f"  allow {label}? [y/N] ")
    return answer.strip().lower() in ("y", "yes")


async def auto_approve(label: str) -> bool:
    print(f"  [auto-approved for the demo] {label}")
    return True


async def main():
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("Set OPENAI_API_KEY first. See 'Set up your OpenAI key' in the main README.")
    demo = "--demo" in sys.argv
    host = Host()
    await host.start()
    try:
        agent = Agent(AsyncOpenAI(), host, auto_approve if demo else ask_user)
        print("model:", MODEL)
        print("tools:", ", ".join(f"{t['name']}{' (read-only)' if t['read_only'] else ''}"
                                   for t in host.catalog), "\n")
        if demo:
            for text in ["What's the weather in Tokyo?",
                         "Save that as a note, then show me all my notes."]:  # "that" needs memory
                print("you  :", text)
                print("agent:", await agent.ask(text), "\n")
            return
        print("Chat with the agent. Type 'quit' to leave.\n")
        while True:
            text = (await asyncio.to_thread(input, "you  : ")).strip()
            if text.lower() in ("", "quit", "exit"):
                break
            print("agent:", await agent.ask(text), "\n")
    finally:
        await host.close()


if __name__ == "__main__":
    asyncio.run(main())
