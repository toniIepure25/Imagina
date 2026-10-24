"""Claim-envelope and local-capability invariants for the Studio product."""
from __future__ import annotations

import pytest

from app.core.animus.studio.claims import (
    STUDIO_FORBIDDEN_PHRASES,
    StudioClaimError,
    capability_envelope,
    claim_envelope,
    enforce_studio_text,
)

pytestmark = pytest.mark.core


def test_claim_ceiling_is_l1():
    envelope = claim_envelope()
    assert envelope["claim_level"] == "L1_BEHAVIORAL_ASSISTED"
    assert envelope["claim_ceiling"] == "L1_BEHAVIORAL_ASSISTED"


def test_neural_dream_and_image_generation_are_not_available():
    capabilities = capability_envelope()
    assert capabilities["neural_content"] == "UNAUTHORIZED"
    assert capabilities["dream_content"] == "UNAUTHORIZED"
    assert capabilities["neural_reconstruction"] == "UNAUTHORIZED"
    assert capabilities["image_generation"] == "DISABLED"


def test_network_and_uploads_are_disabled():
    capabilities = capability_envelope()
    assert capabilities["network_calls"] == "DISABLED"
    assert capabilities["uploads"] == "DISABLED"
    assert capabilities["privacy_scope"] == "local_only"


def test_scene_graph_and_renderer_are_the_product_surface():
    capabilities = capability_envelope()
    assert capabilities["scene_graph"] == "ANIMUS-SG-v1"
    assert capabilities["renderer"] == "procedural-local"


@pytest.mark.parametrize("phrase", sorted(STUDIO_FORBIDDEN_PHRASES)[:6])
def test_known_decoding_claims_are_rejected(phrase):
    with pytest.raises(StudioClaimError):
        enforce_studio_text(f"This product does this: {phrase}", field="copy")


def test_allowed_behavioral_copy_passes():
    text = (
        "Describe a scene, see a procedural candidate, correct it, lock what is right, "
        "and keep or explore a variation. This is a behavioural scaffold, not a decoder."
    )
    assert enforce_studio_text(text, field="copy") == text


def test_case_and_whitespace_do_not_bypass_the_guard():
    with pytest.raises(StudioClaimError):
        enforce_studio_text("  MIND   READING  demo  ", field="title")


def test_claim_error_names_the_field_for_debuggable_ui():
    with pytest.raises(StudioClaimError) as caught:
        enforce_studio_text("decode your dreams", field="world description")
    assert "world description" in str(caught.value)
