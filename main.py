"""
Terminal entry point. No UI required for the app to be fully usable -
this was the original interface before app.py (Streamlit) was added on top.
"""
from models import AgentState
from agent import bootstrap, handle


def main():
    print("=" * 60)
    print("Recruitment System Chatbot (terminal agent)")
    print("=" * 60)
    state = AgentState()

    try:
        print(bootstrap(state))
    except Exception as e:
        print(f"\nStartup failed: {e}")
        print(
            "This is almost always either a missing/invalid GEMINI_API_KEY in "
            ".env, or no internet access for the one-time embedding model download."
        )
        return
    print()

    while True:
        try:
            query = input("\nrecruiter> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not query:
            continue
        if query.lower() in ("exit", "quit"):
            print("Goodbye.")
            break
        try:
            print(handle(state, query))
        except Exception as e:
            print(f"Something went wrong handling that: {e}")


if __name__ == "__main__":
    main()
