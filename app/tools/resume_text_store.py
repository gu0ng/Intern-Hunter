import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings


def save_resume_text(raw_text: str, source_filename: str = "resume.pdf") -> dict[str, Any]:
    cleaned = raw_text.strip()
    if not cleaned:
        raise ValueError("Resume text is empty; PDF extraction produced no usable text.")

    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
    saved_at = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    safe_name = _safe_filename(source_filename)
    snapshot_dir = settings.resolve_path(settings.resume_text_dir)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / f"{saved_at}_{digest[:12]}_{safe_name}.txt"
    snapshot_path.write_text(cleaned, encoding="utf-8")

    current_path = settings.resolve_path(settings.current_resume_text_path)
    current_path.parent.mkdir(parents=True, exist_ok=True)
    current_path.write_text(cleaned, encoding="utf-8")

    meta = {
        "source_filename": source_filename,
        "saved_at": saved_at,
        "sha256": digest,
        "char_count": len(cleaned),
        "snapshot_path": str(snapshot_path.relative_to(settings.project_root)),
        "current_path": str(current_path.relative_to(settings.project_root)),
    }
    meta_path = settings.resolve_path(settings.current_resume_meta_path)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def load_current_resume_text() -> str:
    path = settings.resolve_path(settings.current_resume_text_path)
    if not path.exists():
        raise FileNotFoundError(f"Current resume text not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise FileNotFoundError(f"Current resume text is empty: {path}")
    return text


def load_current_resume_meta() -> dict[str, Any]:
    path = settings.resolve_path(settings.current_resume_meta_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def list_saved_resume_texts() -> list[dict[str, Any]]:
    snapshot_dir = settings.resolve_path(settings.resume_text_dir)
    if not snapshot_dir.exists():
        return []
    rows = []
    for path in sorted(snapshot_dir.glob("*.txt"), key=lambda item: item.stat().st_mtime, reverse=True):
        text = path.read_text(encoding="utf-8", errors="ignore")
        rows.append(
            {
                "path": str(path.relative_to(settings.project_root)),
                "filename": path.name,
                "char_count": len(text),
                "updated_at": datetime.utcfromtimestamp(path.stat().st_mtime).isoformat(),
            }
        )
    return rows


def _safe_filename(filename: str) -> str:
    name = Path(filename or "resume.pdf").stem or "resume"
    safe = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "_", name).strip("_")
    return safe[:40] or "resume"