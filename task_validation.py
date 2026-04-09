from __future__ import annotations

import argparse
import re
import sys
import tokenize
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator, List, Sequence


SOURCE_EXTENSIONS = {".py"}
TEXT_EXTENSIONS = {".json", ".yaml", ".yml", ".txt"}
SKIP_DIRS = {".git", ".venv", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
DECIMAL_PATTERN = re.compile(
    r"(?<![\w.])[+-]?(?:\d+\.\d*|\.\d+|\d+(?:\.\d*)?[eE][+-]?\d+)(?![\w.])"
)


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    token: str
    value: str


def is_decimal_token(token: str) -> bool:
    return "." in token or "e" in token.lower()


def parse_decimal(token: str) -> Decimal | None:
    try:
        return Decimal(token)
    except (InvalidOperation, ValueError):
        return None


def boundary_check(token: str) -> bool:
    value = parse_decimal(token)
    return value is not None and value in {Decimal(0), Decimal(1)}


def scan_python_file(path: Path) -> List[Finding]:
    findings: List[Finding] = []
    try:
        with tokenize.open(path) as handle:
            tokens = tokenize.generate_tokens(handle.readline)
            for tok_type, tok_str, start, _, _ in tokens:
                if tok_type != tokenize.NUMBER:
                    continue
                if not is_decimal_token(tok_str):
                    continue
                if boundary_check(tok_str):
                    value = parse_decimal(tok_str)
                    findings.append(Finding(path=path, line=start[0], token=tok_str, value=str(value)))
    except (OSError, SyntaxError, tokenize.TokenError) as exc:
        findings.append(Finding(path=path, line=1, token="<parse-error>", value=str(exc)))
    return findings


def scan_text_file(path: Path) -> List[Finding]:
    findings: List[Finding] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [Finding(path=path, line=1, token="<read-error>", value=str(exc))]

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if path.suffix in {".yaml", ".yml"} and stripped.startswith("#"):
            continue
        for match in DECIMAL_PATTERN.finditer(line):
            token = match.group(0)
            if boundary_check(token):
                value = parse_decimal(token)
                findings.append(Finding(path=path, line=line_number, token=token, value=str(value)))
    return findings


def iter_target_files(root: Path) -> Iterator[Path]:
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix in SOURCE_EXTENSIONS or path.suffix in TEXT_EXTENSIONS:
            yield path


def collect_findings(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    for path in sorted(iter_target_files(root)):
        if path.suffix in SOURCE_EXTENSIONS:
            findings.extend(scan_python_file(path))
        else:
            findings.extend(scan_text_file(path))
    return findings


def format_findings(findings: Sequence[Finding], root: Path) -> str:
    lines = []
    for finding in findings:
        lines.append(f"{finding.path.relative_to(root)}:{finding.line}: boundary decimal {finding.token} -> {finding.value}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate that decimal literals do not touch 0 or 1.")
    parser.add_argument("path", nargs="?", default=".", help="Repository path to scan")
    args = parser.parse_args(argv)

    root = Path(args.path).resolve()
    findings = collect_findings(root)

    if findings:
        print("Task validation failed: boundary-touching decimals found.", file=sys.stderr)
        print(format_findings(findings, root), file=sys.stderr)
        return 1

    print("Task validation passed: no decimal literals touch 0 or 1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())