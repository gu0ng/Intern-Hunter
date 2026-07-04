from app.services.resume_profiler import collect_resume_keywords, load_resume_profile


def test_load_resume_profile_sample():
    profile = load_resume_profile("data/resume/resume.yaml")

    assert profile.major == "网络空间安全"
    assert "Python" in profile.skills
    assert profile.projects


def test_collect_resume_keywords_contains_project_keywords():
    profile = load_resume_profile("data/resume/resume.yaml")
    keywords = collect_resume_keywords(profile)

    assert "AI安全" in keywords
    assert "Agent" in keywords

