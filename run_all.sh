#!/usr/bin/env bash
# Runs every stage. Part 1 of each stage (plain MCP) always runs.
# Part 2 (the OpenAI model) runs only when OPENAI_API_KEY is in .env or the environment.
set -e
cd "$(dirname "$0")"
PY=$(command -v python3 || command -v python)  # python3 on macOS/Linux, python on Windows
run() { echo; echo "################ $1/$2 ################"; (cd "$1" && "$PY" "${@:2}"); }
llm() { if [ -n "$OPENAI_API_KEY" ] || grep -qs "^OPENAI_API_KEY=." .env; then run "$@"; else echo; echo "(skipping $1/$2: add OPENAI_API_KEY to .env to run it)"; fi; }

run stage1_weather test_client.py;            llm stage1_weather llm_chat.py
run stage2_wire raw_wire_client.py;           llm stage2_wire llm_to_wire.py
run stage3_typed_tools client.py 2>/dev/null; llm stage3_typed_tools llm_client.py
run stage4_resources_prompts client.py;       llm stage4_resources_prompts llm_client.py
run stage5_multi_server host.py;              llm stage5_multi_server chat.py
run stage6_http client.py;                    llm stage6_http llm_client.py
run stage7_agent rule_agent.py;               llm stage7_agent agent.py --demo
