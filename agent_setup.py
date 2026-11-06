import config
import progress
from smolagents import OpenAIServerModel, ToolCallingAgent
from tools import read_lesson, run_python, scaffold_project, get_progress, web_search

PROMPT_PATH = config.BASE_DIR / "prompts" / "system.md"


def build_model() -> OpenAIServerModel:
    """Build the hosted NVIDIA NIM model client.

    Retries live here and only here: the OpenAI SDK performs up to three
    retries with exponential backoff. Tools never retry.
    """
    return OpenAIServerModel(
        model_id=config.MODEL_ID,
        api_base=config.API_BASE,
        api_key=config.NVIDIA_API_KEY,
        client_kwargs={"max_retries": 3, "timeout": config.API_TIMEOUT},
    )


def build_agent(extra_tools=None) -> ToolCallingAgent:
    """Create a fresh agent. /lesson calls this to reset in-session state."""
    instructions = (
        PROMPT_PATH.read_text(encoding="utf-8").strip()
        + "\n\nLearner progress: "
        + progress.summary()
    )
    tools = [read_lesson, run_python, scaffold_project, get_progress]
    if config.WEB_SEARCH_ENABLED:
        tools.append(web_search)
    if extra_tools:
        tools.extend(extra_tools)
    return ToolCallingAgent(
        tools=tools,
        model=build_model(),
        max_steps=config.MAX_STEPS,
        instructions=instructions,
    )


if __name__ == "__main__":
    print(build_agent().run("Teach lesson 01_project_structure"))
