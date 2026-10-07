"""Cross-check narrative-doc numbers against audited claim expectations.

The audit pins artifact values, but nothing checked the docs themselves:
synthesis.md quoted pre-fix panel numbers (and README pre-correction
tourist figures) while the audit stayed green. This script inverts the
check: every result-like number in the covered docs must match some
audited claim (expected +/- tol) or an explicit allowlist entry.

Covered docs are the narrative surface (synthesis + README), where
cross-cutting edits drift from script-local fixes. Historical-record
files (review_brief, and struck-through vintage sections) are excluded
by design — they intentionally quote superseded numbers. Add explorer
docs to COVERED_DOCS only with a built allowlist.

Run: make audit-docs (also runs as part of `make audit`).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import audit_claims  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

COVERED_DOCS = ["docs/synthesis.md", "README.md"]

# Numbers that are structural, not results: doc/page counts, ports, sizes,
# parameters, census anchors quoted for provenance rather than as findings.
# Each entry: (value, reason). Years 1990-2030 are skipped globally.
ALLOW = {
    "docs/synthesis.md": [
        (18083692, "2011 census household anchor (provenance, not a finding)"),
        (310, "municipios with tourist data (coverage count)"),
        (90, "affordability reference dwelling size (assumption, methods 2)"),
        (30, "'30 pinned sources' doc count"),
        (20, "'20 mart tables' (verified: 20 tables in marts.duckdb)"),
        (24, "'24 explorations' doc count"),
        (13, "'13 years' Santa Coloma starts window"),
        (514, "Santa Coloma starts 2012-24 (printed at verify; coverage fact)"),
        (10000, "'10k tourist flats' rounded coverage count"),
        (28, "'28 in Santa Coloma' coverage count"),
        (18, "'in 18y' window length"),
        (0.34, "quoted inside dated correction notes as superseded pre-repair vintage"),
        (1.04, "quoted inside dated correction notes as superseded pre-repair vintage"),
        (1000, "per-1000 unit label (viv/1000, dwellings/1000)"),
        (59531, "INE table identifier (electricity vacancy)"),
        (2.11, "principales-as-households proxy tolerance (build-time validation)"),
        (650, "rounded interior-range low end (pinned exact: Galicia 652.85)"),
        (770, "rounded interior-range high end (pinned exact: CyL 770.67)"),
    ],
    "README.md": [
        (90, "affordability reference dwelling size (assumption)"),
        (2555, "SERPAVI municipio coverage (also a claim; kept as count)"),
        (52, "52-provincia coverage count"),
        (2.6, "GIS probe data size (ancillary)"),
        (3.11, "Python version requirement"),
        (30, "gate runtime estimates (author-measured, not results)"),
        (26, "26 fetch endpoints in the fetch target"),
        (60, "gate runtime estimates (author-measured, not results)"),
        (8091, "preview dashboard port"),
        (56945, "INE table identifier (blocked provincial ECP)"),
        (1000, "per-1000 unit label"),
    ],
}


def claim_expectations() -> list[tuple[float, float]]:
    """All (expected, tol) pairs the audit checks. Single source of truth.

    Parsed from audit_claims.py with ast (robust to formatting): every
    tuple literal ending in two numbers is a claim, regardless of arity
    (mart 5-tuples, path 4-tuples, computed-got 4-tuples). Freshness
    entries have no numbers and are excluded by construction. The count
    guard below fails loudly if a new tuple shape appears.
    """
    import ast

    src = (ROOT / "scripts" / "audit_claims.py").read_text()
    tree = ast.parse(src)
    out: list[tuple[float, float]] = []

    def number(e: ast.expr) -> float | None:
        if isinstance(e, ast.Constant) and isinstance(e.value, (int, float)):
            return float(e.value)
        if (
            isinstance(e, ast.UnaryOp)
            and isinstance(e.op, (ast.USub, ast.UAdd))
            and isinstance(e.operand, ast.Constant)
            and isinstance(e.operand.value, (int, float))
        ):
            return -float(e.operand.value) if isinstance(e.op, ast.USub) else float(e.operand.value)
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.Tuple) or len(node.elts) < 4:
            continue
        vals = [number(e) for e in node.elts[-2:]]
        if all(v is not None for v in vals):
            out.append((vals[0], vals[1]))
    # The saiz_gis_probe land-area anchor is an ad-hoc check (+ 1 in the
    # audit total), not a tuple: pin it here, failing if it ever leaves.
    assert "503189.7" in src, "land anchor literal moved; update this pin"
    out.append((503189.7, 2.0))
    return out


def audit_total() -> int:
    """Recompute the audit's own printed claim total.

    Mirrors main(): the initial assignment plus every `total +=`, EXCLUDING
    `len(MODEL_FRESHNESS)` — that line runs after the "claims hold" print,
    so the printed total covers value claims only.
    """
    src = (ROOT / "scripts" / "audit_claims.py").read_text()
    scope = {
        "CLAIMS": audit_claims.CLAIMS,
        "IV_CLAIMS": audit_claims.IV_CLAIMS,
        "PROBE_CLAIMS": audit_claims.PROBE_CLAIMS,
        "SENSITIVITY_CLAIMS": audit_claims.SENSITIVITY_CLAIMS,
        "PANEL_SAIZ_CLAIMS": audit_claims.PANEL_SAIZ_CLAIMS,
        "PANEL_SAIZ_MUNI_CLAIMS": audit_claims.PANEL_SAIZ_MUNI_CLAIMS,
    }
    total = 0
    seen_lists: set[str] = set()
    for line in src.splitlines():
        sline = line.strip()
        if not sline.startswith("total"):
            continue
        for n in re.findall(r"total \+= (\d+)", sline):
            total += int(n)
        for name in re.findall(r"len\((\w+)\)", sline):
            if name == "MODEL_FRESHNESS" or name in seen_lists:
                continue
            seen_lists.add(name)
            total += len(scope[name])
        if "+=" not in sline:
            for n in re.findall(r"(?<![\w.])\d+(?![\w.])", sline.split("=", 1)[1]):
                if f"len({n})" not in sline:
                    total += int(n)
    return total


def doc_numbers(text: str) -> list[tuple[float, float, str]]:
    """Extract (value, rounding-slack, context-line) triples from markdown.

    Normalizes unicode signs, splits ranges/arrows into endpoints, drops
    code spans/urls, list markers, age-band labels (20-34), and two-digit
    year fragments (2021-25 keeps 2021). Slack is half the token's last
    decimal place (scaled by k/M) so honest doc rounding passes while
    real drift still fails.
    """
    text = re.sub(r"```.*?```", " ", text, flags=re.S)  # fenced code
    text = re.sub(r"`[^`]*`", " ", text)  # inline code (ports, commands)
    text = re.sub(r"https?://\S+", " ", text)  # urls
    # Non-result identifiers: ISO dates, project jargon, regressor labels,
    # decade labels (2000s), integer year-counts (18y -- decimal 6.2y is a
    # real value and is kept by stripping only the y).
    text = re.sub(r"\b(19|20)\d{2}-\d{2}(-\d{2})?\b", " ", text)
    text = re.sub(r"\bmilestone-\d+\b", " ", text)
    text = re.sub(r"\bL\d+\b", " ", text)
    text = re.sub(r"\b(19|20)\d0s\b", " ", text)
    text = re.sub(r"\b(\d+\.\d+)y\b", r"\1 ", text)
    text = re.sub(r"\b(\d+)y\b", " ", text)
    out = []
    for line in text.splitlines():
        line = re.sub(r"^\s*\d+\.\s+", "", line)  # ordered-list markers
        # age-band labels and 2-digit year fragments are not results
        line = re.sub(r"\b20\s*[-–]\s*34\b", " ", line)
        line = re.sub(r"\b(19|20)\d{2}\s*[-–]\s*\d{2}\b", lambda m: m.group(0)[:4] + " ", line)
        norm = (
            line.replace("−", "-")
            .replace("–", " ")
            .replace("—", " ")
            .replace("→", " ")
            .replace("×", " ")
            .replace("~", " ")
            .replace("±", " ")
            .replace("…", " ")
            .replace("†", " ")
            .replace("²", " ")
        )
        # split digit-digit ranges on leftover hyphens: 2001-2025 -> pair
        norm = re.sub(r"(\d)-(\d)", r"\1 \2", norm)
        for m in re.finditer(r"[-+]?\d[\d,]*\.?\d*\s*[kM%]?(?![A-Za-z])", norm):
            tok = m.group(0).strip()
            # skip tokens glued to a preceding letter: SHA-256, pre-2021,
            # post-2021 (identifiers, not measurements)
            if m.start() > 0 and norm[m.start() - 1].isalpha():
                continue
            mult = 1.0
            if tok and tok[-1] in "kM%":
                if tok[-1] == "k":
                    mult = 1e3
                elif tok[-1] == "M":
                    mult = 1e6
                tok = tok[:-1].strip()
            try:
                digits = tok.replace(",", "")
                val = float(digits) * mult
            except ValueError:
                continue
            # half the last decimal place, scaled by k/M
            slack = 0.5 * 10 ** (-len(digits.split(".")[1])) * mult if "." in digits else 0.5 * mult
            out.append((val, slack, line.strip()[:120]))
    return out


def main() -> int:
    claims = claim_expectations()
    want = audit_total()
    if len(claims) != want:
        print(
            f"FAIL: extracted {len(claims)} claim expectations but the audit "
            f"prints {want} — a new claim tuple shape appeared; "
            "teach claim_expectations() the new shape"
        )
        return 1
    print(f"claim expectations extracted: {len(claims)} (matches audit value claims)")
    failures = 0
    for rel in COVERED_DOCS:
        text = (ROOT / rel).read_text()
        allowed = [(v, why) for v, why in ALLOW.get(rel, [])]
        unmatched = []
        for val, slack, ctx in doc_numbers(text):
            if val == int(val) and 1990 <= val <= 2030:
                continue  # calendar years are not results
            if any(abs(val - e) <= t + slack for e, t in claims):
                continue
            if any(abs(val - v) <= 1e-9 for v, _ in allowed):
                continue
            unmatched.append((val, ctx))
        if unmatched:
            print(f"[FAIL] {rel}: {len(unmatched)} numbers match no claim/allowlist entry")
            for val, ctx in unmatched:
                print(f"    {val:g} :: {ctx}")
            failures += len(unmatched)
        else:
            print(f"[OK] {rel}: all numbers match claims or allowlist")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
