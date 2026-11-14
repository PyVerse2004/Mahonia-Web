# Icons and text harmony

Contents: why it matters · choosing the library · pairing rules · concept-to-icon map · sizing and alignment CSS · icon-only controls · RTL · microcopy rules

An icon and its label are one unit. When they disagree (wrong metaphor, different weights, misaligned baselines, inconsistent wording), the UI feels amateur even if each piece looks fine alone. The goal is that a user never has to wonder what an icon means or why the same action looks different on another page.

## Choosing the library

1. If the project already uses one (Font Awesome, Bootstrap Icons, Material Symbols, Heroicons, Lucide, Feather), keep it and remove the strays. Switching is only worth it when the existing one is incomplete or visually clashes with the chosen typography.
2. If there is none, pick one with a consistent stroke style. Good defaults: **Bootstrap Icons** if the site uses Bootstrap, **Lucide/Heroicons** (outline) for Tailwind or custom CSS.
3. Never mix filled and outlined styles, or two libraries, in one interface. Emoji used as icons count as a separate library; replace them in UI chrome (they render differently per OS).
4. Ask before adding a CDN; prefer vendoring the SVG sprite or font into `static/`.

## Pairing rules

- **One concept, one icon, one word.** Edit = pencil + "Edit" everywhere. Delete = trash + "Delete". Never gear for edit on one page and pencil on another.
- **Icon + label by default** for primary and secondary actions. Icon-only is acceptable for universally understood, space-constrained controls (close, search, menu, copy), and always needs an accessible name.
- **Icon position is consistent**: leading icon before the label for actions (`[+ Add item]`); trailing icon only for direction/disclosure (`Next >`, dropdown caret, external link). In RTL, "leading" flips automatically if you use flex with logical `gap` and do not hardcode left/right margins.
- **Match visual weight**: a 400-weight 16px label pairs with a 1.5px-stroke icon at 1em-1.25em. Do not put a heavy filled icon next to light text.
- **Color**: icons inherit `currentColor` from the text. Use a different icon color only for semantic status (success/warning/danger) and keep it in the same hue family as the text color of that status.
- **Decorative vs meaningful**: if the label already says it, the icon is decorative (`aria-hidden="true"`). If the icon is the only content, it is meaningful and needs a name.
- **Avoid icon overload**: if every table cell, menu item and heading has an icon, none of them carry information. Use icons on actions, status, and navigation; leave plain headings and body text alone.

## Concept-to-icon map (starting point)

Keep this in one place (template tag dict or partial) so it is a one-line change. Names below are Bootstrap Icons; translate to the chosen library.

| Concept | Icon | Label (verb-first) |
|---|---|---|
| Create / add | `plus-lg` | Add / Create |
| Edit | `pencil` | Edit |
| Delete | `trash3` | Delete |
| Save / confirm | `check-lg` | Save |
| Cancel / close | `x-lg` | Cancel / Close |
| View / details | `eye` | View |
| Search | `search` | Search |
| Filter | `funnel` | Filter |
| Download | `download` | Download |
| Upload | `upload` | Upload |
| Settings | `gear` | Settings |
| Profile / account | `person` | Profile |
| Log in / out | `box-arrow-in-right` / `box-arrow-right` | Log in / Log out |
| Home | `house` | Home |
| Back / next | `arrow-left` / `arrow-right` (mirror in RTL) | Back / Next |
| Success / warning / error / info | `check-circle` / `exclamation-triangle` / `x-octagon` / `info-circle` | (message text) |
| External link | `box-arrow-up-right` | (link text) |
| Copy | `clipboard` | Copy |

Audit the project's actual vocabulary first (what does it call things: "Remove" or "Delete"?) and keep its terms; just make them consistent.

## Sizing and alignment CSS

```css
.icon {
  width: 1.25em;            /* scales with the surrounding font-size */
  height: 1.25em;
  flex: none;               /* never let flex squash it */
  vertical-align: -0.2em;   /* fallback when not in a flex container */
  fill: none;
  stroke: currentColor;     /* for SVG icons; for icon fonts use color: inherit */
}

/* Icon + label unit */
.btn, .nav-link, .menu-item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

/* Icon-only button: square, same height as text buttons */
.btn-icon { width: 2.5rem; height: 2.5rem; padding: 0; justify-content: center; }
.btn-icon .icon { width: 1.25rem; height: 1.25rem; }

/* Mirror directional icons in RTL */
[dir="rtl"] .icon-directional { transform: scaleX(-1); }
```

Use em-based sizes so the icon scales with the label when a button is made `--small` or `--large`. Do not size each icon with ad-hoc pixel values.

## Icon-only controls

Every icon-only `<a>` or `<button>` needs both:

```html
<button type="button" class="btn btn-icon" aria-label="{% trans 'Delete' %}" title="{% trans 'Delete' %}">
  {% icon "delete" %}
</button>
```

Or visually hidden text (`<span class="visually-hidden">Delete</span>`), which also gets translated with the rest of the page. The audit script flags icon-only controls that have neither.

## RTL

- Mirror: arrows, chevrons, back/forward, "reply", list indents, progress direction, anything that implies reading direction.
- Do not mirror: search magnifier, check, plus, trash, gear, clocks, play (media controls conventionally keep direction), brand logos, anything with text in the glyph.
- Use logical properties (`margin-inline-start`, `padding-inline-end`, `inset-inline-start`) so the icon-to-label gap works in both directions with no extra rules.

## Microcopy rules (the text side)

- Buttons are verb-first and specific: "Save changes", "Send message", not "Submit", "OK", "Click here".
- Same action, same wording on every page and in confirmations: if the button says "Delete", the dialog says "Delete this project?" and the success message says "Project deleted."
- Sentence case everywhere (or Title Case everywhere); pick one.
- Error messages say what happened and what to do next, near the field, without blame: "Enter an email like name@example.com", not "Invalid input".
- Empty states explain and offer the next step: "No invoices yet. Create your first invoice."
- Keep labels short enough to avoid wrapping next to an icon (about 1-3 words); move detail to help text or a tooltip.
- In Persian UI, prefer natural phrasing over literal translation, and be consistent with the project's existing terminology (for example, "حذف" vs "پاک کردن"). Use proper ZWNJ (نیم‌فاصله) in compound words and keep digits consistent (all Persian or all Latin) per the project's convention.
