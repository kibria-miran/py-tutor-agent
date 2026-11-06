import agent_setup
import config


def test_model_forwards_retry_and_timeout(monkeypatch) -> None:
    monkeypatch.setattr(config, "NVIDIA_API_KEY", "dummy")
    monkeypatch.setattr(config, "MODEL_ID", "test/model")
    model = agent_setup.build_model()
    assert model.client.max_retries == 3
    assert model.client.timeout == config.API_TIMEOUT
    assert model.retryer.max_attempts == 1


def test_agent_registers_expected_tools(monkeypatch) -> None:
    monkeypatch.setattr(config, "NVIDIA_API_KEY", "dummy")
    monkeypatch.setattr(config, "MODEL_ID", "test/model")
    monkeypatch.setattr(config, "WEB_SEARCH_ENABLED", False)
    agent = agent_setup.build_agent()
    names = set(agent.tools)
    assert {"read_lesson", "run_python", "scaffold_project", "get_progress"} <= names
    assert "save_progress" not in names
    assert "web_search" not in names
    assert agent.logger.level.name == "ERROR"


def test_web_search_registered_only_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr(config, "NVIDIA_API_KEY", "dummy")
    monkeypatch.setattr(config, "MODEL_ID", "test/model")
    monkeypatch.setattr(config, "WEB_SEARCH_ENABLED", True)
    agent = agent_setup.build_agent()
    assert "web_search" in set(agent.tools)


def test_instructions_include_progress_summary(monkeypatch) -> None:
    monkeypatch.setattr(config, "NVIDIA_API_KEY", "dummy")
    monkeypatch.setattr(config, "MODEL_ID", "test/model")
    agent = agent_setup.build_agent()
    assert "Learner progress:" in agent.instructions
    assert "Completed" in agent.instructions
    assert "Available lesson slugs:" in agent.instructions
    assert "02_env_and_config" in agent.instructions
