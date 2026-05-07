import pytest

from app.signals import get_provider, list_providers


@pytest.mark.asyncio
async def test_simulated_provider_deterministic():
    p1 = get_provider("simulated.default")
    p2 = get_provider("simulated.default")
    assert p1 is not None and p2 is not None
    await p1.start("s1")
    await p2.start("s2")
    fv1 = await p1.next_window("s1", 0)
    fv2 = await p2.next_window("s2", 0)
    assert fv1.theta_power == fv2.theta_power


@pytest.mark.asyncio
async def test_manual_provider_safe_default():
    provider = get_provider("manual.self_report_only")
    assert provider is not None
    fv = await provider.next_window("manual", 0)
    assert 0 <= fv.signal_quality <= 1


def test_lsl_stub_fails_gracefully():
    provider = get_provider("lsl.stub")
    assert provider is not None
    health = provider.health()
    assert "available" in health
    assert health["status"] in {"available", "not_available"}


def test_provider_registry_lists_providers():
    ids = {provider.provider_id for provider in list_providers()}
    assert {"simulated.default", "manual.self_report_only", "replay.event_log", "lsl.stub"} <= ids
