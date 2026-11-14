# Design system reference

Contents: tokens · typography · spacing and layout · components · motion · UX and accessibility checks

A small, strict system beats a rich, loose one. Pick a handful of values, name them, and use only those.

## Tokens (starter `tokens.css`)

Adjust the brand hue to the project; keep the structure.

```css
:root {
  /* Brand: one primary, one neutral family, semantic colors */
  --color-primary-50:  #eef4ff;
  --color-primary-100: #dbe7ff;
  --color-primary-500: #3b6cf6;
  --color-primary-600: #2f57d4;   /* default button / link */
  --color-primary-700: #2646ab;   /* hover */

  --color-neutral-0:   #ffffff;
  --color-neutral-50:  #f8f9fb;
  --color-neutral-100: #f0f2f5;
  --color-neutral-200: #e2e6ec;   /* borders */
  --color-neutral-500: #667085;   /* secondary text */
  --color-neutral-700: #344054;
  --color-neutral-900: #101828;   /* body text */

  --color-success: #12805c;
  --color-warning: #b54708;
  --color-danger:  #c0362c;
  --color-info:    #1d6fb8;

  /* Semantic aliases: components use THESE, never raw palette values */
  --bg-page:      var(--color-neutral-50);
  --bg-surface:   var(--color-neutral-0);
  --text-body:    var(--color-neutral-900);
  --text-muted:   var(--color-neutral-500);
  --border-color: var(--color-neutral-200);
  --link-color:   var(--color-primary-600);
  --focus-ring:   0 0 0 3px color-mix(in srgb, var(--color-primary-500) 35%, transparent);

  /* Type */
  --font-sans: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-sans-fa: "Vazirmatn", "Inter", system-ui, sans-serif; /* RTL / Persian */
  --text-xs: .75rem; --text-sm: .875rem; --text-base: 1rem;
  --text-lg: 1.125rem; --text-xl: 1.25rem; --text-2xl: 1.5rem; --text-3xl: 1.875rem;
  --leading-tight: 1.25; --leading-normal: 1.6;

  /* Spacing: 4px base, use only these */
  --space-1: .25rem; --space-2: .5rem; --space-3: .75rem; --space-4: 1rem;
  --space-6: 1.5rem; --space-8: 2rem; --space-12: 3rem;

  /* Shape and depth */
  --radius-sm: 6px; --radius-md: 10px; --radius-lg: 16px; --radius-pill: 999px;
  --shadow-sm: 0 1px 2px rgb(16 24 40 / .06);
  --shadow-md: 0 4px 12px rgb(16 24 40 / .08);

  /* Motion */
  --ease: cubic-bezier(.2, .8, .2, 1);
  --dur-fast: 120ms; --dur: 200ms;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
}
```

Dark mode is optional. If wanted, redefine only the semantic aliases under `@media (prefers-color-scheme: dark)` or `[data-theme="dark"]`; components then need no changes. That is the reason to use aliases.

## Typography

- One sans family (plus a Persian/Arabic family for RTL). Two weights are enough in most UIs (400, 600).
- Body 16px minimum, line-height ~1.6 (Persian text often reads better at 1.7-1.8). Headings tight (~1.25).
- Limit line length to roughly 60-75 characters for reading text (`max-width: 65ch`).
- Load fonts with `font-display: swap`, self-host when possible (add to `static/fonts/`), preload the primary weight.

## Spacing and layout

- A single container (`max-width` 1100-1200px, horizontal padding `--space-4`, larger on desktop).
- Vertical rhythm from the spacing scale only; no one-off `margin-top: 13px`.
- Group related things closer than unrelated things (proximity does most of the visual work).
- Cards: surface background, 1px border or soft shadow (not both heavy), `--radius-md`, padding `--space-4` to `--space-6`.

## Components (one definition each)

| Component | Conventions |
|---|---|
| Button | Three variants only: primary (filled), secondary (outlined), danger. Same height, radius and padding across all. One primary per view/form. Disabled and loading states defined. |
| Link | Underline on hover or always for in-text links; distinct from body color. |
| Form control | Same height as buttons (40-44px), visible border, clear focus ring, label above field, help text muted, error text in `--color-danger` with an icon and `role="alert"` or `aria-describedby`. |
| Table | Header in muted small caps or semibold, zebra or row hover (not both), horizontal scroll wrapper on mobile, right-align numbers (left-align in RTL where appropriate). |
| Alert / message | Four semantic variants matching Django `messages` tags; icon + text, dismissible, readable color contrast. |
| Badge | Pill, small text, semantic colors only for status. |
| Pagination | Prev/Next with labels, current page clearly marked, large touch targets. |
| Empty state | Icon or illustration, one sentence explaining why it's empty, one primary action. |
| Modal | Focus trapped, closes with Esc, destructive confirmations name the object. |

## UX and accessibility checks

Go through these at the end; fix what is cheap, list what is not.

- **Contrast**: body text >= 4.5:1, large text and UI borders >= 3:1. Check muted text and text on colored buttons specifically.
- **Focus**: every interactive element has a visible `:focus-visible` style. Never `outline: none` without a replacement.
- **Targets**: tappable elements at least ~44x44px on mobile.
- **Responsive**: usable at 360px width with no horizontal scroll (except inside table wrappers); nav collapses sensibly.
- **Forms**: every input has a `<label for>`; correct `type`/`autocomplete`/`inputmode`; errors show next to the field and summarized at top for long forms; submit button shows a pending state to prevent double submits.
- **Feedback**: after every action the user sees a result (Django `messages`, redirect to a meaningful page).
- **Destructive actions**: confirmation step, danger styling, never adjacent to the primary action without spacing.
- **Navigation**: current page highlighted (`aria-current="page"`), logo links home, breadcrumbs on deep pages.
- **Images**: meaningful `alt`, empty `alt=""` for decorative, explicit `width`/`height` to avoid layout shift, `loading="lazy"` below the fold.
- **Language**: `<html lang>` matches content; `dir` set correctly.
- **Motion**: subtle (150-250ms), no motion required to understand state, respects `prefers-reduced-motion`.
