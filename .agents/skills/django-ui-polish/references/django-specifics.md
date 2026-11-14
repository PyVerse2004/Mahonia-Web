# Django-specific notes

Contents: base template skeleton · static files · forms · messages · icon template tag · admin · i18n and RTL/Persian · common pitfalls

## Base template skeleton

```django
{% load static i18n %}
{% get_current_language as LANGUAGE_CODE %}
{% get_current_language_bidi as LANGUAGE_BIDI %}
<!doctype html>
<html lang="{{ LANGUAGE_CODE }}" dir="{% if LANGUAGE_BIDI %}rtl{% else %}ltr{% endif %}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}{% endblock %} | Site name</title>
  <link rel="stylesheet" href="{% static 'css/tokens.css' %}">
  {# framework CSS here, after tokens so overrides stay simple #}
  <link rel="stylesheet" href="{% static 'css/components.css' %}">
  {% block extra_head %}{% endblock %}
</head>
<body>
  <a class="skip-link" href="#main">{% trans "Skip to content" %}</a>
  {% include "includes/navbar.html" %}
  {% include "includes/messages.html" %}
  <main id="main" class="container">
    {% block content %}{% endblock %}
  </main>
  {% include "includes/footer.html" %}
  {% block extra_js %}{% endblock %}
</body>
</html>
```

If the project is monolingual and not Django-i18n-based, hardcode `lang` and `dir` instead of the tags above. Keep existing block names so child templates keep working.

## Static files

- Check `STATICFILES_DIRS` and `STATIC_URL`; put new CSS where existing CSS lives.
- In production with `collectstatic`/WhiteNoise, a missing file referenced with `{% static %}` can raise an error (manifest storage). Run `python manage.py collectstatic --dry-run --noinput` or at least confirm each new file exists on disk.
- Self-host fonts and icons under `static/` when feasible; add `font-display: swap`.
- Cache-busting: do not rename existing files without updating every reference.

## Forms (largest UX payoff)

Replace `{{ form.as_p }}` / `{{ form.as_table }}` with per-field rendering via a reusable include:

```django
{# templates/includes/field.html #}
<div class="field{% if field.errors %} has-error{% endif %}">
  <label class="field-label" for="{{ field.id_for_label }}">
    {{ field.label }}{% if field.field.required %}<span class="req" aria-hidden="true">*</span>{% endif %}
  </label>
  {{ field }}
  {% if field.help_text %}<p class="field-help" id="{{ field.id_for_label }}_help">{{ field.help_text }}</p>{% endif %}
  {% for error in field.errors %}
    <p class="field-error" role="alert">{% icon "error" %} {{ error }}</p>
  {% endfor %}
</div>
```

Use it with `{% for field in form %}{% include "includes/field.html" %}{% endfor %}` and render `form.non_field_errors` at the top.

To style widgets without touching templates per field, either use the project's existing crispy-forms/widget-tweaks setup, or add a mixin. Changing a form class is a frontend-only change here, as long as fields, validation and `Meta` are untouched:

```python
class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css = widget.attrs.get("class", "")
            if widget.input_type in ("checkbox", "radio"):
                widget.attrs["class"] = f"{css} form-check-input".strip()
            else:
                widget.attrs["class"] = f"{css} form-control".strip()
```

Prefer `widget_tweaks` (`{% render_field field class="form-control" %}`) if it is already installed. Ask before adding a new package.

Also check: `autocomplete` and `inputmode` attributes on common fields (email, tel, one-time-code), `type="date"` where appropriate, a `disabled` pending state on submit (small inline JS is fine).

## Django messages

Map Django's tags (`debug, info, success, warning, error`) to semantic alert styles. `error` maps to danger. If using Bootstrap, add in `settings.py`:

```python
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {messages.ERROR: "danger"}
```

Message partial: icon from the icon map + text + dismiss button with an accessible name; container uses `role="status"` (and `role="alert"` for errors).

## Icon template tag (single source of truth)

```python
# <app>/templatetags/ui.py
from django import template
from django.utils.html import format_html

register = template.Library()

# Concept -> Bootstrap Icons name. Change an icon here and it changes site-wide.
ICONS = {
    "add": "plus-lg", "edit": "pencil", "delete": "trash3", "save": "check-lg",
    "close": "x-lg", "view": "eye", "search": "search", "filter": "funnel",
    "download": "download", "upload": "upload", "settings": "gear",
    "profile": "person", "home": "house", "back": "arrow-left", "next": "arrow-right",
    "success": "check-circle", "warning": "exclamation-triangle",
    "error": "x-octagon", "info": "info-circle", "external": "box-arrow-up-right",
}
DIRECTIONAL = {"back", "next"}

@register.simple_tag
def icon(name, extra_class=""):
    glyph = ICONS.get(name, "dot")
    cls = f"bi bi-{glyph} icon"
    if name in DIRECTIONAL:
        cls += " icon-directional"
    if extra_class:
        cls += f" {extra_class}"
    return format_html('<i class="{}" aria-hidden="true"></i>', cls)
```

Usage: `{% load ui %}` then `{% icon "edit" %}`. Adapt the glyph markup if the project uses inline SVG or a sprite (`<svg class="icon"><use href="{% static 'icons.svg' %}#pencil"/></svg>`). If the project has no suitable app for `templatetags`, put it in the main app and make sure that app is in `INSTALLED_APPS`, and that the folder has an `__init__.py`.

## Django admin

Only touch the admin if the user asks or the project clearly customizes it.

- Override via `templates/admin/base_site.html` (extends `admin/base_site.html`) and extra CSS in `{% block extrastyle %}`; do not edit installed packages.
- Admin has its own CSS variables (`--primary`, `--secondary`, `--body-fg`, `--link-fg` ...); override these in `:root` rather than restyling selectors.
- For a full modern admin theme, mention django-unfold or django-jazzmin as options and ask before adding.

## i18n and RTL / Persian

- Detect with `LANGUAGE_CODE` (`fa`, `fa-ir`, `ar`, `he`, `ur`) and `get_current_language_bidi`.
- Use **CSS logical properties** everywhere: `margin-inline-start/end`, `padding-inline`, `border-inline-start`, `text-align: start`, `inset-inline-*`. They make one stylesheet work for both directions.
- If using Bootstrap in RTL, load the RTL build (`bootstrap.rtl.min.css`) conditionally; Tailwind has `rtl:` / `ltr:` variants and logical utilities (`ms-*`, `me-*`, `ps-*`, `pe-*`).
- Font: Vazirmatn is a good default for Persian (supports Latin glyphs too, so mixed text stays harmonious). Set `font-family: var(--font-sans-fa)` when `[dir="rtl"]` or `:lang(fa)`. Use slightly larger line-height (1.7-1.8) for Persian.
- Mixed-direction snippets (English product names, emails, URLs, phone numbers inside Persian text): wrap in `<bdi>` or set `dir="ltr"` on inputs of type email/url/tel/number with `text-align: end` so they remain readable.
- Digits: follow the project's convention. Either keep Latin digits or convert to Persian digits consistently (a small template filter, not scattered replaces). Do not mix in the same view.
- Dates: if the project shows Jalali dates, keep using its existing library (jdatetime / django-jalali); only change presentation.
- Mirror directional icons (see `icons-and-text.md`); check that dropdowns, tooltips, toasts and offcanvas panels open on the correct side.
- Carousels, sliders, progress bars and step indicators should run right-to-left.

## Common pitfalls

- Editing a template that is overridden elsewhere (app templates vs project `templates/` order in `TEMPLATES["DIRS"]`/`APP_DIRS`): confirm which file actually renders (`{% extends %}` chain, `django-debug-toolbar` or a quick `get_template(...).origin`).
- `{% static %}` in CSS files does not work; use relative `url()` paths in static CSS.
- Inline `<style>` inside child templates silently overrides the design system; move rules into the shared CSS.
- Third-party packages (allauth, crispy templates, admin) render their own templates; style them by overriding the template in the project's `templates/` with the same path, not by editing site-packages.
- JavaScript that selects by class (`.btn-delete`) or id will break if classes are renamed; search the JS before renaming.
