import os

import pytest

import agent_setup


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("NVIDIA_API_KEY"), reason="requires NVIDIA_API_KEY")
def test_nim_roundtrip() -> None:
    model = agent_setup.build_model()
    message = model.generate(
        [{"role": "user", "content": "Reply with the single word OK."}],
        max_tokens=512,
    )
    assert (message.content or "").strip()
