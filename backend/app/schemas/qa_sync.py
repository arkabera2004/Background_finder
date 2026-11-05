"""Agent 07 — QA and Sync: human approval decision shape."""

from pydantic import BaseModel


class QAApprovalDecision(BaseModel):
    approve: bool
