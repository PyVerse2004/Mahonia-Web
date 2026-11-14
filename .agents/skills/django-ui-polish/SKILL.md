---
name: django-ui-polish
description: Audit and improve the frontend (UI/UX) of a Django project so it looks professional and consistent - unify icons with text labels, fix typography, spacing, colors, forms, buttons, navigation, messages, empty states, responsiveness, accessibility and RTL/Persian layout, all without touching models, views or business logic. Make sure to use this skill whenever the user mentions beautifying, redesigning, polishing, restyling or "fixing the look" of a Django site, templates, base.html, static CSS, Bootstrap/Tailwind in Django, icons that don't match their text, an ugly or inconsistent UI, UX problems in Django forms or pages, or Django admin theming - even if they don't say "UI/UX" explicitly and even if they write in Persian (e.g. ظاهر سایت، زیباسازی، فرانت جنگو، آیکون و متن).
---

# Django UI Polish

Make a Django project's frontend look intentional and feel coherent, while leaving the backend alone. The most common reasons a Django site looks "off" are not missing creativity but missing *consistency*: three icon sets, five button styles, random spacing, hardcoded colors, forms rendered with `{{ form.as_p }}`. So the job is mostly to establish one small design system and then apply it everywhere, rather than to decorate individual pages.

Reply in the language the user writes in (Persian is common here). Keep code, class names and file paths in English.

## Hard guardrails

These exist because template edits can silently break Django behavior:

- Never change models, views, URLs, migrations, form field names, context variable names, or `id`/`name`/`data-*` attributes that JavaScript or tests may rely on, unless the user asks.
- Preserve every template tag: `{% csrf_token %}`, `{% url %}`, `{% trans %}` / `{% blocktrans %}`, `{% load %}`, `{% block %}`/`{% extends %}`, `{% static %}`. Wrapping or re-ordering markup around them is fine; deleting them is not.
- Keep user-facing strings translatable if the project already uses i18n.
- Prefer small, reviewable diffs. If the project is a git repo, check `git status` first and tell the user what changed. Do not add a new frontend build toolchain (npm, webpack, Tailwind CLI) unless the project already has one or the user agrees; plain CSS with variables plus the framework already in use is the default.
- Do not add dependencies silently. Ask before adding a CDN, icon pack, or Python package.

## Workflow

### 1. Discover (read before you restyle)

1. Locate: `settings.py` (`TEMPLATES`, `STATICFILES_DIRS`, `STATIC_URL`, `LANGUAGE_CODE`, `LANGUAGES`), the base template (usually `templates/base.html`), and the static CSS/JS folders.
2. Identify what is already in use: CSS framework (Bootstrap / Tailwind / Bulma / none), icon library, fonts, crispy-forms or similar, django-allauth, Django admin customizations.
3. Run the audit script to get a factual inventory of problems:
   ```bash
   python /path/to/django-ui-polish/scripts/audit_frontend.py <project_root>
   ```
   It reports mixed icon libraries, icon-only buttons with no accessible name, hardcoded colors, inline styles, images without `alt`, missing `<html lang/dir>` and viewport meta, and button/class sprawl. Treat its output as a starting list, not the final truth; skim the real templates too.
4. Detect direction: if `LANGUAGE_CODE` is `fa`/`ar`/`he`/`ur` or templates contain Persian text, treat the site as RTL (see `references/django-specifics.md`, RTL section).

### 2. Decide the direction, asking as little as possible

Infer from the existing site (brand colors in the logo or CSS, the domain of the project) and state your assumptions in one or two lines. Ask the user only for things you cannot infer and that change the result a lot - typically: brand color or reference site, formal vs friendly tone, whether switching framework is allowed. One short question beats a questionnaire. If they do not answer, proceed with sensible defaults.

### 3. Build the design system first

Create or update one tokens file (for example `static/css/tokens.css`) and load it before everything else. Follow `references/design-system.md` for the scale of colors, type, spacing, radius, shadow and motion. If the project uses Bootstrap, map tokens onto Bootstrap's CSS variables (`--bs-primary`, etc.) instead of fighting it with `!important`. If it uses Tailwind, put tokens in the Tailwind config.

### 4. Apply it outside-in

Work in this order, because each layer inherits from the previous one:

1. `base.html`: `<html lang dir>`, viewport meta, font loading, header/nav, footer, main container width, messages area.
2. Global components: buttons, links, form controls, cards, tables, badges, alerts, pagination, modals.
3. Forms (highest UX payoff in Django): render fields individually or with a widget-styling mixin instead of `as_p`; show labels, help text and errors next to each field; one primary action per form.
4. Page-level templates: list pages, detail pages, dashboards, auth pages.
5. Empty, loading, error and success states for every list and form.

### 5. Harmonize icons and text

This is a core part of the request, so do it deliberately. Read `references/icons-and-text.md` for the full rules. In short:

- One icon library for the whole site; replace strays.
- Each concept gets exactly one icon and one verb everywhere (Edit is always the pencil and the word "Edit", never pencil on one page and gear on another).
- Icons are sized relative to the text (`1em`-based), vertically centered with `inline-flex` plus a `gap`, and inherit `currentColor`.
- Icon-only controls always get an accessible name (`aria-label` or visually hidden text) and a tooltip.
- Directional icons mirror in RTL; non-directional ones do not.
- Centralize it: an `{% icon "name" %}` template tag or an `includes/icon.html` partial, backed by one name-to-icon map, so changing an icon is a one-line edit.

### 6. Check UX and accessibility

Go through the checklist in `references/design-system.md` ("UX and accessibility checks"): contrast 4.5:1 for body text, visible focus rings, 44px touch targets, responsive at ~360px width, destructive actions confirmed, Django `messages` styled and dismissible, no layout shift from late-loading fonts or images, `prefers-reduced-motion` respected.

### 7. Verify

- `python manage.py check` and, if tests exist, run them. A template syntax error shows up as a 500 only on render, so also open or render at least the base page and one form page (`python manage.py shell` with `django.template.loader.get_template(...)` is a quick compile check; a dev-server request or headless screenshot is better when tools allow).
- Re-run the audit script and compare before/after counts.
- If a browser or screenshot tool is available, look at the result at desktop and ~375px mobile widths before declaring it done.

### 8. Report back

Finish with a short summary: what the design system now is (palette, font, icon library), which files changed, anything you deliberately left alone, and 2-3 optional next steps. Do not paste whole files into chat; point to them.

## Output habits

- Prefer editing the existing templates and CSS over creating parallel ones. New shared pieces go in predictable places: `static/css/tokens.css`, `static/css/components.css`, `templates/includes/`, `templatetags/ui.py`.
- Comment non-obvious CSS with *why*, not what.
- When two reasonable options exist (e.g. top navbar vs sidebar), pick one, say why in a sentence, and mention the alternative only if it is cheap to switch.

## Reference files

- `references/design-system.md` - tokens, scales, component conventions, UX/accessibility checklist. Read at step 3 and step 6.
- `references/icons-and-text.md` - icon/label pairing rules, concept-to-icon map, microcopy rules. Read at step 5.
- `references/django-specifics.md` - templates, static files, forms, messages, admin, i18n and RTL/Persian details, template-tag code. Read when touching forms, admin, or RTL.
- `scripts/audit_frontend.py` - static audit of templates and CSS. Run at step 1 and again at step 7.
