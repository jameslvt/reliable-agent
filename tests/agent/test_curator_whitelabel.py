"""White-label guards for background curator prompts."""

from agent.curator import CURATOR_REVIEW_PROMPT


def test_curator_prompt_uses_reliable_branding_when_enabled_by_default():
    assert "睿来智能体助手" in CURATOR_REVIEW_PROMPT
    assert "Hermes" not in CURATOR_REVIEW_PROMPT
    assert "Nous" not in CURATOR_REVIEW_PROMPT
