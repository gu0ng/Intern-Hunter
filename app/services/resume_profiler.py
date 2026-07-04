from pathlib import Path

import yaml

from app.config import settings
from app.schemas.resume import ResumeProfile
from app.tools.resume_parse_tool import parse_resume_text
from app.tools.resume_text_store import load_current_resume_text


def load_resume_profile(path: str | Path | None = None) -> ResumeProfile:
    if path is not None:
        return _load_yaml_resume_profile(path)

    raw_text = load_current_resume_text()
    return parse_resume_text(raw_text, save=False, source_filename="current_resume.txt").profile




def collect_resume_keywords(profile: ResumeProfile) -> set[str]:
    keywords: set[str] = set(profile.skills)
    keywords.update(profile.target_roles)
    keywords.update(profile.research_direction)
    for project in profile.projects:
        keywords.add(project.name)
        keywords.update(project.keywords)
        for highlight in project.highlights:
            keywords.update(_split_keywords(highlight))
    return {keyword.strip() for keyword in keywords if keyword and keyword.strip()}


def _load_yaml_resume_profile(path: str | Path) -> ResumeProfile:
    resume_path = settings.resolve_path(str(path))
    if not resume_path.exists():
        raise FileNotFoundError(f"Resume profile not found: {resume_path}")

    with resume_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    return ResumeProfile.model_validate(data)


def _split_keywords(text: str) -> list[str]:
    separators = ["、", ",", "，", "/", " "]
    result = [text]
    for separator in separators:
        result = [piece for item in result for piece in item.split(separator)]
    return [item.strip() for item in result if len(item.strip()) >= 2]
