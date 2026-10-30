"""Local mock of a Band room for demos: the real GTM Gym agent, no Band account needed.

Type messages as you would in Band; the trained model and simulated buyer are real,
only the Band connection is mocked.

    .venv/bin/python -m gtm_sim.band_demo
    you> @gtm-gym prospect 1000004
    you> approve
"""

import asyncio
import os
import types

from .band_agent import GTMGymAdapter

DIM, BOLD, ORANGE, BLUE, RESET = "\033[2m", "\033[1m", "\033[38;5;209m", "\033[38;5;75m", "\033[0m"


class MockRoomTools:
    async def send_message(self, content, mentions=None):
        text = content.replace("**", "")
        print(f"\n{ORANGE}{BOLD}gtm-gym{RESET} {DIM}(agent){RESET}")
        for line in text.splitlines():
            print(f"  {line}")
        print()


async def main():
    user = os.environ.get("USER", "you")
    print(f"{DIM}Loading the trained model…{RESET}")
    agent = GTMGymAdapter()
    print(f"\n{BOLD}# gtm-demo{RESET}  {DIM}local mock of a Band room · members: {user}, gtm-gym{RESET}")
    print(f"{DIM}Try: @gtm-gym prospect 1000004   ·   @gtm-gym next   ·   approve / reject   ·   quit{RESET}\n")
    tools = MockRoomTools()
    while True:
        try:
            text = input(f"{BLUE}{BOLD}{user}{RESET}> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in ("quit", "exit"):
            break
        if not text:
            continue
        msg = types.SimpleNamespace(content=text, sender_name=user, room_id="gtm-demo")
        await agent.on_message(msg, tools, [], None, None, is_session_bootstrap=False, room_id="gtm-demo")


if __name__ == "__main__":
    asyncio.run(main())
