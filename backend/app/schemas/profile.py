from pydantic import BaseModel


class Experience(BaseModel):
    title: str
    company: str
    start_date: str | None = None  # "YYYY-MM"
    end_date: str | None = None  # "YYYY-MM" or None if current
    description: str | None = None


class Post(BaseModel):
    text: str
    posted_at: str | None = None
    is_repost: bool = False
    url: str | None = None


class EducationRecord(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None  # "YYYY-MM" or "YYYY"
    end_date: str | None = None


class Person(BaseModel):
    full_name: str
    headline: str | None = None
    current_company: str | None = None
    linkedin_url: str | None = None
    experiences: list[Experience] = []
    education: list[EducationRecord] = []
    posts: list[Post] = []
    source: str  # provider name that produced this record
