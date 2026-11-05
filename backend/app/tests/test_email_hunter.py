from app.providers.email_verification_provider import EmailVerificationProvider, EmailVerificationResult
from app.services.email_hunter import generate_candidate_emails, select_best_candidate, verify_candidates


class FakeVerifier(EmailVerificationProvider):
    name = "fake"

    def __init__(self, status_by_email: dict[str, str]):
        self._status_by_email = status_by_email

    async def verify(self, email: str) -> EmailVerificationResult:
        status = self._status_by_email.get(email, "unknown")
        return EmailVerificationResult(status=status, confidence=0.9 if status != "unknown" else 0.0)


def test_generate_candidate_emails_covers_common_patterns():
    candidates = generate_candidate_emails("Jane Doe", "acme.com")

    emails = {c["email"] for c in candidates}
    assert emails == {
        "jane.doe@acme.com",
        "janedoe@acme.com",
        "j.doe@acme.com",
        "jdoe@acme.com",
        "jane@acme.com",
    }


def test_generate_candidate_emails_returns_empty_for_single_token_name():
    assert generate_candidate_emails("Madonna", "acme.com") == []


async def test_verify_candidates_maps_provider_status_to_policy():
    candidates = [{"email": "jane.doe@acme.com", "pattern": "first.last"}]
    verifier = FakeVerifier({"jane.doe@acme.com": "valid"})

    results = await verify_candidates(verifier, candidates)

    assert results[0]["verification_status"] == "valid"
    assert results[0]["confidence"] == 0.9


async def test_verify_candidates_unknown_becomes_needs_review():
    candidates = [{"email": "jane.doe@acme.com", "pattern": "first.last"}]
    verifier = FakeVerifier({})  # no entry -> "unknown"

    results = await verify_candidates(verifier, candidates)

    assert results[0]["verification_status"] == "needs_review"
    assert results[0]["confidence"] == 0.0


def test_select_best_candidate_prefers_valid_over_needs_review():
    candidates = [
        {"email": "a", "verification_status": "needs_review", "confidence": 0.9},
        {"email": "b", "verification_status": "valid", "confidence": 0.5},
    ]

    assert select_best_candidate(candidates)["email"] == "b"


def test_select_best_candidate_returns_none_when_all_rejected():
    candidates = [{"email": "a", "verification_status": "rejected", "confidence": 0.9}]

    assert select_best_candidate(candidates) is None
