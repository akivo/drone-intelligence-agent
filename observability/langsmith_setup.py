import os
from dotenv import load_dotenv

load_dotenv()


def configure_langsmith() -> bool:
    """
    Validates LangSmith env vars and prints connection status.
    Returns True if tracing is enabled.
    """
    api_key = os.getenv("LANGCHAIN_API_KEY")
    project = os.getenv("LANGCHAIN_PROJECT", "drone-fleet-agent")
    tracing = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"

    if not api_key:
        print("[OBSERVABILITY] LANGCHAIN_API_KEY not set - LangSmith tracing disabled")
        return False

    if not tracing:
        print("[OBSERVABILITY] LANGCHAIN_TRACING_V2 is not 'true' - tracing disabled")
        return False

    # LangChain reads these vars automatically; we just confirm they are set
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = project

    print(f"[OBSERVABILITY] LangSmith tracing enabled -> project: '{project}'")
    print(f"[OBSERVABILITY] Dashboard: https://smith.langchain.com/projects/{project}")
    return True
