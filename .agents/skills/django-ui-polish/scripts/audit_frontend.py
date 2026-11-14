#!/usr/bin/env python3
"""Static audit of a Django project's frontend (templates + CSS).

Usage:
    python audit_frontend.py <project_root> [--json]

Reports (best-effort, regex based; treat as a starting list, not ground truth):
  - CSS framework(s) and icon library/libraries detected (flags mixing)
  - Icon-only <a>/<button> with no accessible name
  - <img> without alt
  - Hardcoded hex colors in CSS / <style> / style="" (outside variable definitions)
  - Inline style="" attribute count
  - Distinct button class variants
  - Base template checks: <html lang>, dir, viewport meta
  - Forms rendered with as_p / as_table / as_ul
  - Forms missing {% csrf_token %} (POST forms only)
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SKIP_DIRS = {
    ".git", ".hg", "node_modules", "venv", ".venv", "env", "__pycache__",
    "site-packages", "staticfiles", "static_root", "dist", "build", "migrations",
    ".tox", ".mypy_cache", ".pytest_cache",
}
SKIP_SUBPATHS = ("static/admin/", "static/debug_toolbar/", "static/rest_framework/")
MIN_VENDOR_MARKERS = (".min.css", ".min.js", "bootstrap.css", "bootstrap.rtl")

ICON_LIBS = {
    "Font Awesome": re.compile(r'\b(?:fa-(?:solid|regular|brands|light|duotone)|fas|far|fab|fal|fad)\b[^"\']*\bfa-[a-z0-9-]+|\bfa-[a-z]+(?:-[a-z0-9]+)*\b|font-?awesome', re.I),
    "Bootstrap Icons": re.compile(r'\bbi bi-[a-z0-9-]+|bootstrap-icons', re.I),
    "Material Icons/Symbols": re.compile(r'material-(?:icons|symbols)', re.I),
    "Feather": re.compile(r'data-feather|feather-icons|\bfeather\b[^"\']*icon', re.I),
    "Lucide": re.compile(r'data-lucide|lucide', re.I),
    "Heroicons": re.compile(r'heroicons', re.I),
    "Remix Icon": re.compile(r'\bri-[a-z0-9-]+-(?:line|fill)\b|remixicon', re.I),
    "Tabler Icons": re.compile(r'\bti ti-[a-z0-9-]+|tabler-icons', re.I),
    "Ionicons": re.compile(r'ion-icon|ionicons', re.I),
}
FRAMEWORKS = {
    "Bootstrap": re.compile(r'bootstrap(?:\.min)?\.(?:css|js)|\bbtn btn-(?:primary|secondary|outline)|class="[^"]*\bcontainer(?:-fluid)?\b[^"]*\brow\b', re.I),
    "Tailwind": re.compile(r'tailwind|class="[^"]*\b(?:flex|grid|px-\d|py-\d|text-(?:sm|lg|xl)|bg-[a-z]+-\d{2,3})\b', re.I),
    "Bulma": re.compile(r'bulma', re.I),
    "Foundation": re.compile(r'foundation(?:\.min)?\.css', re.I),
    "Materialize": re.compile(r'materialize', re.I),
}
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")

TAG_PAIR_RE = re.compile(r'<(a|button)\b([^>]*)>(.*?)</\1>', re.I | re.S)
IMG_RE = re.compile(r'<img\b([^>]*)>', re.I | re.S)
FORM_RE = re.compile(r'<form\b([^>]*)>(.*?)</form>', re.I | re.S)
STYLE_ATTR_RE = re.compile(r'\sstyle\s*=\s*"[^"]*"', re.I)
STYLE_BLOCK_RE = re.compile(r'<style\b[^>]*>(.*?)</style>', re.I | re.S)
HEX_RE = re.compile(r'(?<![\w&/])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b(?!\s*[{,>+~\[.:#])')
BTN_CLASS_RE = re.compile(r'\b(btn(?:-[a-z0-9]+)+|button(?:--[a-z0-9]+|-[a-z0-9]+)*)\b')


def iter_files(root: Path, suffixes):
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in suffixes:
            continue
        parts = set(p.parts)
        if parts & SKIP_DIRS:
            continue
        posix = p.as_posix()
        if any(s in posix for s in SKIP_SUBPATHS):
            continue
        if any(m in p.name for m in MIN_VENDOR_MARKERS):
            continue
        yield p


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def strip_markup(inner: str) -> str:
    """Return visible-ish text of an element body. Template tags/variables count as text."""
    no_comments = re.sub(r'<!--.*?-->|\{#.*?#\}', '', inner, flags=re.S)
    no_tags = re.sub(r'<[^>]+>', '', no_comments)
    # keep {% trans %} / {{ var }} content as text signal
    return re.sub(r'\s+', ' ', no_tags).strip()


def has_icon_markup(inner: str) -> bool:
    return bool(
        re.search(r'<i\b|<svg\b|<ion-icon\b|material-(?:icons|symbols)|\{%\s*icon\b|\{%\s*include\s+["\'][^"\']*icon', inner, re.I)
    )


CUSTOM_PROP_RE = re.compile(r'--[\w-]+\s*:[^;}]*')


def hex_in(line: str):
    return HEX_RE.findall(CUSTOM_PROP_RE.sub('', line))


def rel(p: Path, root: Path) -> str:
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return p.as_posix()


def audit(root: Path):
    templates = list(iter_files(root, {".html", ".htm", ".txt"}))
    templates = [t for t in templates if t.suffix.lower() in {".html", ".htm"}]
    css_files = list(iter_files(root, {".css", ".scss", ".sass", ".less"}))

    report = defaultdict(list)
    icon_hits = defaultdict(Counter)   # lib -> file -> count
    framework_hits = Counter()
    emoji_files = Counter()
    btn_variants = Counter()
    hex_counter = Counter()
    inline_style_total = 0
    as_p_forms = []
    csrf_missing = []
    img_no_alt = []
    icon_only_unnamed = []
    base_checks = {}

    for t in templates:
        text = read(t)
        name = rel(t, root)

        for lib, rx in ICON_LIBS.items():
            n = len(rx.findall(text))
            if n:
                icon_hits[lib][name] += n
        for fw, rx in FRAMEWORKS.items():
            if rx.search(text):
                framework_hits[fw] += 1
        if EMOJI_RE.search(text):
            emoji_files[name] += len(EMOJI_RE.findall(text))

        for cls_attr in re.findall(r'class\s*=\s*"([^"]*)"', text):
            for m in BTN_CLASS_RE.findall(cls_attr):
                btn_variants[m] += 1

        inline_style_total += len(STYLE_ATTR_RE.findall(text))

        for m in IMG_RE.finditer(text):
            if not re.search(r'\balt\s*=', m.group(1), re.I):
                line = text.count("\n", 0, m.start()) + 1
                img_no_alt.append(f"{name}:{line}")

        for m in TAG_PAIR_RE.finditer(text):
            attrs, inner = m.group(2), m.group(3)
            if not has_icon_markup(inner):
                continue
            if strip_markup(inner):
                continue  # has visible text
            if re.search(r'aria-label(?:ledby)?\s*=|\btitle\s*=|visually-hidden|sr-only|screen-reader', attrs + inner, re.I):
                continue
            line = text.count("\n", 0, m.start()) + 1
            icon_only_unnamed.append(f"{name}:{line}")

        for m in re.finditer(r'\{\{\s*[\w.]*form\s*\.\s*(as_p|as_table|as_ul)\b', text):
            line = text.count("\n", 0, m.start()) + 1
            as_p_forms.append(f"{name}:{line} ({m.group(1)})")

        for m in FORM_RE.finditer(text):
            attrs, inner = m.group(1), m.group(2)
            if re.search(r'method\s*=\s*["\']?post', attrs, re.I) and 'csrf_token' not in inner and 'csrf' not in attrs.lower():
                line = text.count("\n", 0, m.start()) + 1
                csrf_missing.append(f"{name}:{line}")

        # hardcoded colors in <style> blocks and style attributes
        chunks = STYLE_BLOCK_RE.findall(text) + STYLE_ATTR_RE.findall(text)
        for chunk in chunks:
            for line in chunk.splitlines():
                for h in hex_in(line):
                    hex_counter[h.lower()] += 1

        # base template checks
        if re.search(r'<html\b', text, re.I) and not re.search(r'\{%\s*extends', text):
            html_tag = re.search(r'<html\b[^>]*>', text, re.I).group(0)
            base_checks[name] = {
                "lang": bool(re.search(r'\blang\s*=', html_tag, re.I)),
                "dir": bool(re.search(r'\bdir\s*=', html_tag, re.I)),
                "viewport": bool(re.search(r'name\s*=\s*["\']viewport["\']', text, re.I)),
                "charset": bool(re.search(r'charset', text, re.I)),
            }

    for c in css_files:
        text = read(c)
        for line in text.splitlines():
            if re.match(r'\s*(\$[\w-]+|@[\w-]+)\s*:', line):
                continue  # Sass/Less variable definitions are fine
            for h in hex_in(line):
                hex_counter[h.lower()] += 1

    font_families = Counter()
    for c in css_files:
        for m in re.finditer(r'font-family\s*:\s*([^;}{]+)', read(c)):
            font_families[re.sub(r'\s+', ' ', m.group(1).strip())] += 1

    return {
        "templates_scanned": len(templates),
        "css_files_scanned": len(css_files),
        "frameworks": dict(framework_hits),
        "icon_libraries": {k: {"total": sum(v.values()), "files": len(v)} for k, v in icon_hits.items()},
        "emoji_in_templates": dict(emoji_files.most_common(10)),
        "icon_only_without_name": icon_only_unnamed,
        "img_without_alt": img_no_alt,
        "forms_using_as_p_table_ul": as_p_forms,
        "post_forms_missing_csrf": csrf_missing,
        "inline_style_attributes": inline_style_total,
        "hardcoded_hex_colors": {"distinct": len(hex_counter), "top": hex_counter.most_common(12)},
        "button_class_variants": dict(btn_variants.most_common(15)),
        "font_family_declarations": dict(font_families.most_common(8)),
        "base_template_checks": base_checks,
    }


def to_markdown(r) -> str:
    out = []
    add = out.append
    add("# Frontend audit\n")
    add(f"Scanned {r['templates_scanned']} templates and {r['css_files_scanned']} CSS files "
        f"(vendor/min files, venvs, migrations and admin static are skipped).\n")

    add("## Stack detected")
    fw = r["frameworks"]
    add("- CSS framework(s): " + (", ".join(f"{k} ({v} files)" for k, v in fw.items()) if fw else "none detected"))
    if len(fw) > 1:
        add("  - WARNING: more than one CSS framework signal; check for conflicting styles.")
    libs = r["icon_libraries"]
    add("- Icon library(ies): " + (", ".join(f"{k} ({v['total']} uses in {v['files']} files)" for k, v in libs.items()) if libs else "none detected"))
    if len(libs) > 1:
        add("  - WARNING: mixed icon libraries; consolidate to one (see references/icons-and-text.md).")
    if r["emoji_in_templates"]:
        add(f"- Emoji present in {len(r['emoji_in_templates'])}+ templates (check whether they are used as icons).")
    add("")

    add("## Icons and text")
    iu = r["icon_only_without_name"]
    add(f"- Icon-only links/buttons without accessible name: {len(iu)}")
    for x in iu[:15]:
        add(f"  - {x}")
    if len(iu) > 15:
        add(f"  - ... and {len(iu) - 15} more")
    add("")

    add("## Accessibility and structure")
    ia = r["img_without_alt"]
    add(f"- <img> without alt: {len(ia)}")
    for x in ia[:10]:
        add(f"  - {x}")
    bc = r["base_template_checks"]
    if bc:
        for name, c in bc.items():
            missing = [k for k, v in c.items() if not v]
            add(f"- {name}: " + ("OK (lang, dir, viewport, charset present)" if not missing else "missing " + ", ".join(missing)))
    else:
        add("- No standalone base template with <html> found (check manually).")
    add("")

    add("## Consistency")
    h = r["hardcoded_hex_colors"]
    add(f"- Hardcoded hex colors: {h['distinct']} distinct values" + (f"; most used: {', '.join(f'{c} x{n}' for c, n in h['top'][:8])}" if h["top"] else ""))
    add(f"- Inline style attributes: {r['inline_style_attributes']}")
    bv = r["button_class_variants"]
    add(f"- Button class variants in use: {len(bv)}" + (f" ({', '.join(list(bv)[:8])})" if bv else ""))
    ff = r["font_family_declarations"]
    add(f"- Distinct font-family declarations: {len(ff)}")
    for k, v in list(ff.items())[:5]:
        add(f"  - {k} (x{v})")
    add("")

    add("## Forms")
    fp = r["forms_using_as_p_table_ul"]
    add(f"- Forms rendered with as_p/as_table/as_ul: {len(fp)}")
    for x in fp[:10]:
        add(f"  - {x}")
    cs = r["post_forms_missing_csrf"]
    add(f"- POST forms without {{% csrf_token %}} (may be handled by an include; verify): {len(cs)}")
    for x in cs[:10]:
        add(f"  - {x}")
    add("")
    add("_Regex-based heuristics: confirm each finding in the actual template before editing._")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="Django project root (the folder with manage.py or templates/)")
    ap.add_argument("--json", action="store_true", help="print raw JSON instead of Markdown")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        sys.exit(2)
    result = audit(root)
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else to_markdown(result))


if __name__ == "__main__":
    main()
