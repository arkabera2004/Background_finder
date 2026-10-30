from app.schemas.brief import Claim, Hook, ProspectBrief, Source
from app.services.citation_validator import has_enough_hooks, validate_brief


def _brief(**kwargs) -> ProspectBrief:
    return ProspectBrief(prospect_name="Jane Doe", **kwargs)


def test_drops_unsourced_factual_claim():
    brief = _brief(
        sources=[Source(id="s1", url="https://example.com")],
        snapshot=[Claim(text="Works at Acme", source_ids=["s1"]), Claim(text="Made up fact")],
    )
    cleaned = validate_brief(brief)
    assert len(cleaned.snapshot) == 1
    assert cleaned.snapshot[0].text == "Works at Acme"


def test_keeps_inference_without_source():
    brief = _brief(
        likely_priorities=[Claim(text="Likely cares about growth", is_inference=True)]
    )
    cleaned = validate_brief(brief)
    assert len(cleaned.likely_priorities) == 1


def test_drops_claim_with_unknown_source_id():
    brief = _brief(snapshot=[Claim(text="X", source_ids=["nonexistent"])])
    cleaned = validate_brief(brief)
    assert len(cleaned.snapshot) == 0


def test_drops_hook_without_valid_source():
    brief = _brief(
        sources=[Source(id="s1", url="https://example.com")],
        hooks=[
            Hook(text="Good hook", source_ids=["s1"]),
            Hook(text="Bad hook", source_ids=["missing"]),
        ],
    )
    cleaned = validate_brief(brief)
    assert len(cleaned.hooks) == 1
    assert cleaned.hooks[0].text == "Good hook"


def test_has_enough_hooks():
    brief = _brief(
        sources=[Source(id="s1", url="https://example.com")],
        hooks=[Hook(text=f"h{i}", source_ids=["s1"]) for i in range(3)],
    )
    assert has_enough_hooks(brief) is True
    assert has_enough_hooks(_brief()) is False
