from datetime import date

from app.schemas.profile import Experience


def _parse_month(value: str | None) -> date | None:
    if not value:
        return None
    year, month = value.split("-")
    return date(int(year), int(month), 1)


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


class CareerInsights:
    def __init__(
        self,
        total_months_experience: int,
        gaps_months: list[tuple[str, str]],
        company_switches: int,
        current_role_months: int | None,
    ):
        self.total_months_experience = total_months_experience
        self.gaps_months = gaps_months
        self.company_switches = company_switches
        self.current_role_months = current_role_months


def analyse_career(experiences: list[Experience], today: date | None = None) -> CareerInsights:
    """Deterministic, rule-based career math. No AI call — this never
    needs credentials and is exact, unlike an LLM summary would be."""
    today = today or date.today()

    dated = []
    for exp in experiences:
        start = _parse_month(exp.start_date)
        if start is None:
            continue
        end = _parse_month(exp.end_date) or today
        dated.append((start, end, exp))

    dated.sort(key=lambda t: t[0])

    total_months = sum(months_between(start, end) for start, end, _ in dated)

    gaps: list[tuple[str, str]] = []
    for i in range(1, len(dated)):
        prev_end = dated[i - 1][1]
        cur_start = dated[i][0]
        gap_months = months_between(prev_end, cur_start)
        if gap_months >= 2:
            gaps.append((prev_end.isoformat()[:7], cur_start.isoformat()[:7]))

    companies = [exp.company for _, _, exp in dated]
    switches = sum(1 for i in range(1, len(companies)) if companies[i] != companies[i - 1])

    current_role_months = None
    for start, end, exp in dated:
        if exp.end_date is None:
            current_role_months = months_between(start, today)

    return CareerInsights(
        total_months_experience=total_months,
        gaps_months=gaps,
        company_switches=switches,
        current_role_months=current_role_months,
    )
