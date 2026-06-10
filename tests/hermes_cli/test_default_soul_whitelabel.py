"""White-label guards for the seeded default SOUL.md template."""

from hermes_cli.default_soul import DEFAULT_SOUL_MD


def test_default_soul_uses_reliable_branding():
    assert "睿来智能体助手" in DEFAULT_SOUL_MD
    assert "Hermes" not in DEFAULT_SOUL_MD
    assert "Nous" not in DEFAULT_SOUL_MD
