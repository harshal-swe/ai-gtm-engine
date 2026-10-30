"""Local mock of a Band room for demos: the real GTM Gym agent, no Band account needed.

Type messages as you would in Band; the trained model and simulated buyer are real,
only the Band connection is mocked.

    .venv/bin/python -m gtm_sim.band_demo
    you> @gtm-gym prospect 1000004
    you> approve

Hands-free for screen recording (types the scenes below by itself):

    .venv/bin/python -m gtm_sim.band_demo --auto
"""

import asyncio
import os
import sys
import time
import types

from .band_agent import GTMGymAdapter

DIM, BOLD, ORANGE, BLUE, RESET = "\033[2m", "\033[1m", "\033[38;5;209m", "\033[38;5;75m", "\033[0m"


# (caption, message, human decision): a bad fit skipped, a good fit drafted, a mistake caught by the human.
SCENES = [
    ("Scene 1 · A bad-fit lead: the agent should skip it", "@gtm-gym prospect 1000002", "approve"),
    ("Scene 2 · A good-fit lead: the agent drafts the first touch", "@gtm-gym prospect 1000004", "approve"),
    ("Scene 3 · The agent gets one wrong; the human gate catches it", "@gtm-gym prospect 1000000", "reject"),
]


def type_out(prompt, text, delay=0.05):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()


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
    if "--auto" in sys.argv:
        await autoplay(agent, tools, user)
        return
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


async def autoplay(agent, tools, user):
    prompt = f"{BLUE}{BOLD}{user}{RESET}> "
    say = lambda text: agent.on_message(types.SimpleNamespace(content=text, sender_name=user, room_id="gtm-demo"),
                                        tools, [], None, None, is_session_bootstrap=False, room_id="gtm-demo")
    time.sleep(2)
    for caption, message, verdict in SCENES:
        print(f"{DIM}── {caption} ──{RESET}\n")
        time.sleep(1.5)
        type_out(prompt, message)
        await say(message)
        time.sleep(6)  # time to read the draft and the buyer's verdict
        type_out(prompt, verdict)
        await say(verdict)
        time.sleep(3)
    print(f"{DIM}── End of demo · local mock of a Band room · fictional prospects, nothing sent ──{RESET}")


if __name__ == "__main__":
    asyncio.run(main())
