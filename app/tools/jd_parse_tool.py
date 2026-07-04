from app.schemas.job import JobStructured
from app.services.jd_parser import parse_jd, parse_jd_with_deepseek, parse_jd_with_rules


class JdParseTool:
    name = "jd_parse_tool"
    description = "Use DeepSeek to parse pasted internship JD text into JobStructured, with rule fallback."

    def run(self, jd_text: str) -> JobStructured:
        return parse_jd(jd_text)


__all__ = ["JdParseTool", "parse_jd", "parse_jd_with_deepseek", "parse_jd_with_rules"]
