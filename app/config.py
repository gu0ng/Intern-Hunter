from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os


load_dotenv()


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/internship_pilot.db")
    resume_text_dir: str = os.getenv("RESUME_TEXT_DIR", "data/resume/texts")
    current_resume_text_path: str = os.getenv("CURRENT_RESUME_TEXT_PATH", "data/resume/current_resume.txt")
    current_resume_meta_path: str = os.getenv("CURRENT_RESUME_META_PATH", "data/resume/current_resume.json")
    enable_llm_parsing: bool = os.getenv("ENABLE_LLM_PARSING", "true").lower() == "true"
    api_base_url: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    enable_redis_cache: bool = os.getenv("ENABLE_REDIS_CACHE", "true").lower() == "true"
    job_cache_ttl_seconds: int = int(os.getenv("JOB_CACHE_TTL_SECONDS", "604800"))

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return self.project_root / path


settings = Settings()
