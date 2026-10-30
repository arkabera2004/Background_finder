"""20 SYNTHETIC fixture profiles for the evaluation framework.

These are entirely made up — no real person's data. They exist to give
the eval runner (app/evals/run_eval.py) a fixed, reproducible input set so
results are comparable run-to-run. They say NOTHING about real-world
accuracy against actual LinkedIn profiles; see docs/EVALUATION_RESULTS.md
for that distinction spelled out.
"""

from dataclasses import dataclass


@dataclass
class Fixture:
    id: str
    expected_name: str
    pasted_text: str


FIXTURES: list[Fixture] = [
    Fixture(
        id=f"fixture-{i:02d}",
        expected_name=name,
        pasted_text=f"{name}\n{title} at {company}\n{bio}",
    )
    for i, (name, title, company, bio) in enumerate(
        [
            ("Alice Chen", "VP of Engineering", "Nimbus Data", "Leads a 40-person platform org."),
            ("Brian Okafor", "Head of Product", "Larkspur Health", "Focused on clinician workflows."),
            ("Carmen Diaz", "Senior Director of Sales", "Tidewater Logistics", "Runs enterprise EMEA sales."),
            ("David Kim", "CTO", "Pixelforge Studios", "Scaled infra from 1 to 50 engineers."),
            ("Elena Petrova", "VP of Marketing", "Glasswing Analytics", "Owns demand gen and brand."),
            ("Farid Haidari", "Director of Operations", "Cobalt Freight", "Oversees North America warehouses."),
            ("Grace Liu", "Principal Engineer", "Northstar Robotics", "Works on perception systems."),
            ("Hassan Malik", "Head of Data Science", "Fernbrook Insurance", "Builds underwriting models."),
            ("Ingrid Svensson", "VP of Customer Success", "Brightloop SaaS", "Manages renewals and NPS."),
            ("James Whitfield", "Founder & CEO", "Ashgrove Biotech", "Previously ran a diagnostics startup."),
            ("Keiko Tanaka", "Senior PM", "Mosaic Fintech", "Owns the payments roadmap."),
            ("Liam O'Brien", "VP of Engineering", "Driftwood Media", "Migrated the stack to Kubernetes."),
            ("Maya Singh", "Director of People", "Thornridge Consulting", "Scaled hiring 3x in two years."),
            ("Noah Fischer", "Head of Growth", "Evergreen Travel", "Runs lifecycle and SEO."),
            ("Olivia Bennett", "VP of Finance", "Hollow Creek Energy", "Oversees FP&A for a 500-person company."),
            ("Pavel Novak", "Staff Engineer", "Ironclad Security", "Specializes in threat detection."),
            ("Quinn Alston", "Director of Design", "Marrow Studio", "Leads a 10-person design team."),
            ("Rosa Mendez", "VP of Supply Chain", "Lantern Foods", "Manages supplier relationships globally."),
            ("Samuel Osei", "Head of Partnerships", "Rivermouth Media", "Negotiates distribution deals."),
            ("Tara Lindqvist", "CTO", "Solstice Robotics", "Co-founded the company in 2019."),
        ]
    )
]

assert len(FIXTURES) == 20
