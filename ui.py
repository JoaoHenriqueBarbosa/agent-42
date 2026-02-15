"""Interface de usuário — terminal. Substituível por API, TUI, etc."""

import json
import sys


def welcome():
    print("agent-42 (ctrl+c para sair)\n")


def goodbye():
    print("\nbye")
    sys.exit(0)


def get_user_input():
    return input("> ")


def show_chunk(text):
    print(text, end="", flush=True)


def show_response_end():
    print("\n")


def show_tool_call(name, args):
    print(f"\n[{name}] {json.dumps(args, ensure_ascii=False)}")


def show_info(message):
    print(message)


def choose_provider(providers):
    names = list(providers)
    print("Provider:")
    for i, name in enumerate(names, 1):
        print(f"  {i}) {name}")
    while True:
        choice = input(f"Escolha [1-{len(names)}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(names):
            selected = names[int(choice) - 1]
            print(f"→ {selected}\n")
            return providers[selected]
