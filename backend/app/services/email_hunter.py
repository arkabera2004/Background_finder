"""Agent 05 — Email Hunter: generate candidate addresses, verify, decide.

Pattern-generated addresses are exactly that — candidates, never claimed
as real until a verification provider actually checks them. With no
provider configured (the default), every candidate stays "unknown" and
is routed to manual review rather than asserted as valid or sent to.
"""

import re

from app.providers.email_verification_provider import EmailVerificationProvider

_NAME_TOKEN_RE = re.compile(r"[a-z]+")


def _name_parts(full_name: str) -> tuple[str, str] | None:
    tokens = _NAME_TOKEN_RE.findall(full_name.lower())
    if len(tokens) < 2:
        return None
    return tokens[0], tokens[-1]


def generate_candidate_emails(full_name: str, domain: str) -> list[dict]:
    """Common professional email patterns for a name+domain. Returns an
    empty list for a name that doesn't parse into first+last — never
    guesses from partial information."""
    parts = _name_parts(full_name)
    if parts is None:
        return []
    first, last = parts

    patterns = {
        "first.last": f"{first}.{last}@{domain}",
        "firstlast": f"{first}{last}@{domain}",
        "f.last": f"{first[0]}.{last}@{domain}",
        "flast": f"{first[0]}{last}@{domain}",
        "first": f"{first}@{domain}",
    }
    return [{"email": email, "pattern": pattern} for pattern, email in patterns.items()]


async def verify_candidates(verifier: EmailVerificationProvider, candidates: list[dict]) -> list[dict]:
    """Verifies each candidate and applies the accept/reject/review policy:
    "valid" -> accepted, "invalid" -> rejected, "unknown" -> manual review.
    Never upgrades an unverified guess to "valid" on its own."""
    results = []
    for candidate in candidates:
        verification = await verifier.verify(candidate["email"])
        status = {"valid": "valid", "invalid": "rejected"}.get(verification.status, "needs_review")
        results.append(
            {
                "email": candidate["email"],
                "pattern": candidate["pattern"],
                "verification_status": status,
                "confidence": verification.confidence,
            }
        )
    return results


def select_best_candidate(verified_candidates: list[dict]) -> dict | None:
    """One email per person: prefer a confirmed "valid" address; otherwise
    the highest-confidence "needs_review" candidate so there's still
    something for a human to check. Returns None if every pattern was
    actively rejected."""
    valid = [c for c in verified_candidates if c["verification_status"] == "valid"]
    if valid:
        return max(valid, key=lambda c: c["confidence"])
    reviewable = [c for c in verified_candidates if c["verification_status"] == "needs_review"]
    if reviewable:
        return max(reviewable, key=lambda c: c["confidence"])
    return None
