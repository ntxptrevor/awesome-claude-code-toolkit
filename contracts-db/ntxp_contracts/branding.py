"""Branding resolver — finds the *most up-to-date* brand skill in Claude's
settings on every call and turns it into a palette + fonts the dashboard styles
itself from.

Why resolve at request time instead of baking colors in: the user asked that
the database "search for the most up to date Branding skill each time in
Claude's settings" so that whenever the NTXP brand skill is updated, every
screen this package renders picks the change up automatically — no redeploy.

Search order (first match per location, newest mtime wins across them):
  1. $CLAUDE_CONFIG_DIR/skills           (explicit override)
  2. ~/.claude/skills                    (user skills)
  3. ~/.config/claude/skills
  4. <repo>/skills                       (project skills, incl. this toolkit)
  5. ~/.claude/plugins/**/skills
  6. /mnt/skills (+ /mnt/skills/examples)  (managed skills)

A skill qualifies as a brand skill if its name/description/keywords mention
NTXP brand identity or generic branding. NTXP-specific skills outrank generic
ones; among equals, the most recently modified SKILL.md wins. If nothing is
found we fall back to documented NTXP defaults so the UI is never unstyled.
"""
from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

# --- NTXP fallback brand -----------------------------------------------------
# Web-safe fallback stack appended after whatever heading/body family a skill
# names (or the defaults below) — defined once so it can't drift.
_FALLBACK_STACK = ", 'Segoe UI', Arial, sans-serif"

# Placeholder defaults used only when no brand skill is discovered. They are
# intentionally neutral/professional; the real NTXP palette comes from the
# brand skill the moment one is present in Claude's settings.
NTXP_DEFAULTS = {
    "name": "NTXP",
    "source": "built-in default",
    "colors": {
        "dark": "#10243E",       # primary text / navy
        "light": "#F7F8FA",      # page background
        "surface": "#FFFFFF",    # cards / table
        "muted": "#6B7785",      # secondary text
        "border": "#DCE2EA",     # hairlines
        "primary": "#10243E",    # brand navy
        "accent": "#E2562B",     # safety orange
        "accent2": "#2F80ED",    # link blue
        "success": "#2E7D52",    # executed / good
        "warning": "#B7791F",    # expiring soon
        "danger": "#C0392B",     # unexecuted / expired
    },
    "fonts": {
        "heading": "Poppins" + _FALLBACK_STACK,
        "body": "Inter" + _FALLBACK_STACK,
    },
    "logo": None,
}

_HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")
# Map free-text color labels in a SKILL.md onto our semantic slots. Ordered:
# the first key found in a label wins, so specific words ("link", "signal")
# come before generic ones ("ink", "red") — e.g. "Link ink" is the link blue,
# "Accent Red" is the accent, "Signal Red" is the alert color, "Ink" is text.
_LABELS = (
    ("link", "accent2"), ("signal", "danger"), ("primary", "primary"), ("navy", "primary"),
    ("brand", "primary"), ("accent", "accent"), ("orange", "accent"), ("secondary", "accent2"),
    ("blue", "accent2"), ("success", "success"), ("green", "success"), ("warning", "warning"),
    ("amber", "warning"), ("danger", "danger"), ("error", "danger"), ("alert", "danger"),
    ("red", "danger"), ("muted", "muted"), ("gray", "muted"), ("grey", "muted"),
    ("border", "border"), ("edge", "border"), ("line", "border"), ("rule", "border"),
    ("surface", "surface"), ("background", "light"), ("light", "light"), ("paper", "light"),
    ("ink", "dark"), ("dark", "dark"), ("text", "dark"),
)
# A skill is a brand skill only if its own name/description is about branding.
_BRAND_WORDS = re.compile(
    r"\bbrand(?:ed|ing)?\b|brand-guidelines|visual identity|corporate identity|style guide|"
    r"document standard|design system|palette|typography")


@dataclass
class Brand:
    name: str
    source: str
    colors: dict
    fonts: dict
    logo: str | None = None
    skill_path: str | None = None
    keywords: list = field(default_factory=list)
    skill_name: str | None = None
    # public asset name -> absolute file path (logo, font files) inside the skill
    assets: dict = field(default_factory=dict)
    font_faces: list = field(default_factory=list)  # [{family, file, weight, style}]

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("assets")
        # Browsers can't load filesystem paths — point at the web server's
        # allow-listed asset route instead.
        d["logo_url"] = f"/api/branding/asset/{Path(self.logo).name}" if self.logo else None
        d["font_faces"] = [dict(f, url=f"/api/branding/asset/{f['file']}") for f in self.font_faces]
        return d


def _candidate_skill_dirs() -> list[Path]:
    dirs: list[Path] = []
    cfg = os.environ.get("CLAUDE_CONFIG_DIR")
    if cfg:
        dirs.append(Path(cfg) / "skills")
    home = Path.home()
    dirs += [
        home / ".claude" / "skills",
        home / ".config" / "claude" / "skills",
        Path(__file__).resolve().parents[2] / "skills",   # <repo>/skills
        home / ".claude" / "plugins",
        Path("/mnt/skills"),   # recursive — covers /mnt/skills/examples too
    ]
    extra = os.environ.get("NTXP_BRANDING_PATH")
    if extra:
        dirs.append(Path(extra).expanduser())
    return [d for d in dirs if d.exists()]


def _iter_skill_files() -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for d in _candidate_skill_dirs():
        for sk in d.rglob("SKILL.md"):
            rp = sk.resolve()
            if rp not in seen:
                seen.add(rp)
                out.append(sk)
    return out


def _score_brand_skill(text: str) -> float:
    """Higher = more likely the intended brand skill; 0 = not a brand skill.

    Qualifies only when the skill's own name/description is about branding AND
    it defines a palette — a skill that merely produces "NTXP-branded" output
    without defining the brand doesn't count. Among brand skills, an NTXP one
    wins, then one whose *name* is about branding, then the richer palette."""
    fm = _parse_frontmatter(text)
    name = fm.get("name", "").strip("'\"").lower()
    about = f"{name} {fm.get('description', '')}".lower()
    palette = len({h.lower() for h in _HEX_RE.findall(text)})
    if palette < 2 or not _BRAND_WORDS.search(about):
        return 0
    score = 10.0 if "ntxp" in about else 0.0
    if _BRAND_WORDS.search(name):
        score += 6
    return score + min(palette, 20) / 4


def _parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    fm: dict = {}
    if not m:
        return fm
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip().lower()] = v.strip()
    return fm


def _parse_colors(text: str) -> dict:
    """Pull labelled hex colors out of a SKILL.md body.

    Matches lines like ``- Orange: `#d97757` - Primary accent`` or
    ``Primary: #10243E`` and maps the label onto our semantic slots.
    """
    colors: dict = {}
    for line in text.splitlines():
        hexes = _HEX_RE.findall(line)
        if not hexes:
            continue
        label_part = line.split(hexes[0])[0].lower()
        slot = next((mapped for key, mapped in _LABELS if key in label_part), None)
        if slot and slot not in colors:
            colors[slot] = hexes[0]
    return colors


# Only a labelled line counts ("- Headings: Poppins", "| Body text | Inter |"),
# never prose that merely mentions headings.
_FONT_PATTERNS = (
    ("heading", r"^[\s\-*|]*\**head(?:ing|line)s?\**\s*[:|]\s*`?([A-Za-z][\w '\-]{1,38})"),
    ("body", r"^[\s\-*|]*\**body(?:\s*text)?\**\s*[:|]\s*`?([A-Za-z][\w '\-]{1,38})"),
)


def _parse_fonts(text: str) -> dict:
    fonts: dict = {}
    for slot, pattern in _FONT_PATTERNS:
        m = re.search(pattern, text, re.I | re.M)
        if m:
            fonts[slot] = m.group(1).split("(")[0].strip().rstrip(".") + _FALLBACK_STACK
    return fonts


_LOGO_EXT = (".svg", ".png", ".webp", ".jpg")
_FONT_EXT = (".woff2", ".woff", ".ttf", ".otf")
_WEIGHTS = {"thin": 100, "extralight": 200, "light": 300, "regular": 400, "medium": 500,
            "semibold": 600, "bold": 700, "extrabold": 800, "black": 900}


def _find_logo(root: Path) -> Path | None:
    """A logo shipped with the skill. The top bar is dark, so prefer a
    reversed / white / light variant when there is one."""
    logos = [p for p in root.rglob("*") if p.suffix.lower() in _LOGO_EXT
             and "logo" in p.stem.lower() and "example" not in str(p).lower()]
    if not logos:
        return None
    logos.sort(key=lambda p: (not re.search(r"revers|white|light|knock", p.stem, re.I),
                              len(str(p))))
    return logos[0]


def _font_faces(root: Path) -> list[dict]:
    """Font files shipped with the skill, e.g. OpenSans-SemiboldItalic.ttf ->
    family "Open Sans", weight 600, italic."""
    faces = []
    for f in sorted(root.rglob("*")):
        if f.suffix.lower() not in _FONT_EXT:
            continue
        fam, _, var = f.stem.partition("-")
        family = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", fam)
        v = var.lower()
        style = "italic" if "italic" in v else "normal"
        weight = _WEIGHTS.get(v.replace("italic", "") or "regular", 400)
        faces.append({"family": family, "file": f.name, "weight": weight, "style": style})
    return faces


def resolve_brand() -> Brand:
    """Scan Claude's settings for the freshest brand skill and build a Brand.
    Always returns something usable (NTXP defaults if no skill is found)."""
    best: tuple[int, float, Path, str] | None = None
    for sk in _iter_skill_files():
        try:
            text = sk.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        score = _score_brand_skill(text)
        if score <= 0:
            continue
        mtime = sk.stat().st_mtime
        if best is None or (score, mtime) > (best[0], best[1]):
            best = (score, mtime, sk, text)   # keep the text — no second read

    if best is None:
        return Brand(**NTXP_DEFAULTS)

    sk, text = best[2], best[3]
    fm = _parse_frontmatter(text)

    parsed = _parse_colors(text)
    colors = dict(NTXP_DEFAULTS["colors"])
    colors.update(parsed)
    # Let the skill drive the primary brand color: prefer an explicit primary,
    # else the skill's dark, else its accent — only then the built-in default.
    if "primary" not in parsed:
        colors["primary"] = parsed.get("dark") or parsed.get("accent") \
            or NTXP_DEFAULTS["colors"]["primary"]

    fonts = dict(NTXP_DEFAULTS["fonts"])
    fonts.update(_parse_fonts(text))
    faces = _font_faces(sk.parent)
    if faces and not _parse_fonts(text):
        # The skill ships its typeface: use it for headings and body.
        stack = f"'{faces[0]['family']}'" + _FALLBACK_STACK
        fonts = {"heading": stack, "body": stack}

    logo = _find_logo(sk.parent)
    assets = {f["file"]: str(next(sk.parent.rglob(f["file"]))) for f in faces}
    if logo:
        assets[logo.name] = str(logo)

    return Brand(
        name=NTXP_DEFAULTS["name"],          # the company, not the skill's name
        source=f"skill: {sk}",
        colors=colors,
        fonts=fonts,
        logo=str(logo) if logo else None,
        skill_path=str(sk),
        keywords=[w.strip() for w in fm.get("description", "").split(",") if w.strip()][:6],
        skill_name=fm.get("name", "").strip("'\"") or None,
        assets=assets,
        font_faces=faces,
    )
