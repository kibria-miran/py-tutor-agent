import config
from smolagents import OpenAIServerModel, ToolCallingAgent


def build_model():
    return OpenAIServerModel(
        model_id=config.MODEL_ID,
        api_base=config.API_BASE,
        api_key=config.NVIDIA_API_KEY,
        client_kwargs={"max_retries": 3, "timeout": config.API_TIMEOUT},
    )


def build_agent(tools=None):
    return ToolCallingAgent(tools=tools or [], model=build_model(), max_steps=config.MAX_STEPS)


if __name__ == "__main__":
    print(build_agent().run("In one sentence, what is a Python package?"))
