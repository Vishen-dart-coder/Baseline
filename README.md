# Baseline

Single-file landing page for **Baseline**, a members' tennis club & academy. No build step, no framework — one HTML file with inline CSS and vanilla JS.

![Baseline hero section](docs/hero.jpg)

## Run it

Browsers block `file://` module imports (used for the Lenis smooth-scroll import map), so serve it over HTTP:

```bash
python3 -m http.server 8000
# open http://localhost:8000/index-cdn.html
```

Any static server works (`npx serve`, `php -S`, etc.) — the only requirement is HTTP, not `file://`.

## Stack

- **No build tooling.** Everything — markup, styles, animation logic — lives in `index-cdn.html`.
- **[Lenis](https://github.com/darkroomengineering/lenis)** for smooth scrolling, loaded straight from jsDelivr via an import map (no npm install).
- **Onest** typeface from Google Fonts.
- A small hand-rolled spring/animation engine (`mkSpring`, scroll-triggered reveals, word-clip text transitions) — no GSAP or Framer Motion.
- Fluid type scale via viewport-relative root `font-size` breakpoints (`html{font-size:...vw}`), so most sizing is in `rem` and scales continuously rather than jumping at breakpoints.

## Structure

Sections in `index-cdn.html`, top to bottom:

| Section | Purpose |
|---|---|
| Hero | Headline, hero video/image, quick stats, court-series promo |
| Trust | Club credibility stats + coach carousel |
| Programs | Training program list (Junior Development, Performance Squad, Adult Clinics, Private Coaching) |
| Facilities | Court gallery |
| Stats | Club numbers |
| Testimonials | Member quotes |
| Footer / CTA | Booking CTA, sitemap, social, contact |

Plus a slide-in mobile menu overlay and a "Book a Visit" modal, both driven by the same spring engine.

## Accessibility notes

- Global `:focus-visible` ring on all interactive elements.
- All motion gated behind `prefers-reduced-motion`.
- The mobile menu is a real modal: `role="dialog"` + `aria-modal="true"`, and `<main>` is set `inert` while it's open so keyboard/screen-reader users can't reach background content.
- Touch targets sized ≥44px (hamburger, carousel arrows, pill buttons).

## Known limitations

- Content (copy, stats, testimonial names, image URLs) is placeholder — swap before shipping to production.
- No true 320px-viewport verification has been done yet; re-check at that width before launch.
- Single-file architecture is intentional for this stage (prototype/demo) — if this grows, it's a good candidate to split into partials with a lightweight build step.
