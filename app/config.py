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
    resume_path: str = os.getenv("RESUME_PATH", "data/resume/resume.yaml")
    enable_llm_parsing: bool = os.getenv("ENABLE_LLM_PARSING", "true").lower() == "true"
    api_base_url: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return self.project_root / path


settings = Settings()
