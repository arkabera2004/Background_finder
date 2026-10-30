from datetime import date

from app.schemas.profile import Experience
from app.services.career_analysis import analyse_career


def test_total_months_sums_non_overlapping_roles():
    exps = [
        Experience(title="Eng", company="A", start_date="2018-01", end_date="2020-01"),
        Experience(title="Sr Eng", company="B", start_date="2020-02", end_date="2022-02"),
    ]
    insights = analyse_career(exps, today=date(2024, 1, 1))
    assert insights.total_months_experience == 24 + 24


def test_detects_employment_gap():
    exps = [
        Experience(title="Eng", company="A", start_date="2018-01", end_date="2019-01"),
        Experience(title="Eng", company="B", start_date="2019-06", end_date="2020-01"),
    ]
    insights = analyse_career(exps, today=date(2024, 1, 1))
    assert insights.gaps_months == [("2019-01", "2019-06")]


def test_no_gap_for_back_to_back_roles():
    exps = [
        Experience(title="Eng", company="A", start_date="2018-01", end_date="2019-01"),
        Experience(title="Eng", company="B", start_date="2019-01", end_date="2020-01"),
    ]
    insights = analyse_career(exps, today=date(2024, 1, 1))
    assert insights.gaps_months == []


def test_counts_company_switches():
    exps = [
        Experience(title="Eng", company="A", start_date="2018-01", end_date="2019-01"),
        Experience(title="Sr Eng", company="A", start_date="2019-01", end_date="2020-01"),
        Experience(title="Eng", company="B", start_date="2020-01", end_date="2021-01"),
    ]
    insights = analyse_career(exps, today=date(2024, 1, 1))
    assert insights.company_switches == 1


def test_current_role_uses_today_when_no_end_date():
    exps = [Experience(title="Eng", company="A", start_date="2023-01", end_date=None)]
    insights = analyse_career(exps, today=date(2024, 1, 1))
    assert insights.current_role_months == 12


def test_experience_missing_start_date_is_ignored():
    exps = [Experience(title="Eng", company="A", start_date=None, end_date=None)]
    insights = analyse_career(exps, today=date(2024, 1, 1))
    assert insights.total_months_experience == 0
