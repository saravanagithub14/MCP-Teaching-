"""Two independent clients, one server, connected by URL."""
import asyncio, subprocess, sys, time, socket
from pathlib import Path
from mcp import Client

PORT = 8765
URL = f"http://127.0.0.1:{PORT}/mcp"


def wait_for_port(port, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.2)
    raise RuntimeError("server did not start")


async def main():
    server = subprocess.Popen(
        [sys.executable, str(Path(__file__).with_name("http_server.py")), str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_port(PORT)
        print(f"Server is up at {URL}\n")
        async with Client(URL) as alice, Client(URL) as bob:
            r1 = await alice.call_tool("get_weather", {"city": "Tokyo"})
            r2 = await bob.call_tool("get_weather", {"city": "London"})
            print("alice:", r1.content[0].text.replace("\n", " "))
            print("bob  :", r2.content[0].text.replace("\n", " "))
            print("\nThe counter went 1 -> 2 across two clients: one shared server.")
    finally:
        server.terminate()
        server.wait(timeout=5)


asyncio.run(main())
