# Mandate site

The landing page for Mandate: one page, no tracking, no email collection.
Its call to action is the public repository and the git install line.

```bash
npm install
npm run dev
```

```bash
npm run typecheck
npm run lint
npm run build
```

No environment variables are needed.

## What it's built on

[Once UI](https://github.com/once-ui-system) (`@once-ui-system/core`, MIT) and
the MIT-licensed shell from Once UI Stack: the root layout, providers and
theme config. `LICENSE` in this folder lists those files.
The landing page itself is in `src/app/(site)` and `src/content`. The mark,
favicon and social image in `public/brand` and `src/app/favicon.ico` are
copies of the repository's `assets/`; fonts and colours follow
`assets/guidelines/BRAND_GUIDE.md` and are set in
`src/resources/once-ui.config.js`.

## Where things are

- **Sections:** `src/app/(site)/components/`, composed in `src/app/(site)/page.tsx`
  in this order: Hero, Decisions, Approvals, Guarantees, Fit, Faq, FollowAlong.
- **FAQ copy:** `src/content/faq.tsx`.
- **Links and install line:** `src/resources/project.ts`.
- **Theme and brand:** `src/resources/once-ui.config.js`.
- **SEO:** `src/resources/seo.js`.

## Before it goes live

- [ ] Replace `https://mandate.example` in `src/resources/once-ui.config.js`
      (`baseURL`) and `src/resources/seo.js` with the real domain.
- [ ] Keep the early-release notice in `src/app/(site)/layout.tsx` until
      the guarantees on the page are backed by released code and tests (see
      `../POSITIONING.md` §7).

## When the API changes

The hero and approvals code samples are written against 0.1.0 and were run
against it. Update them with the API, and switch `installCommand` in
`src/resources/project.ts` to a PyPI install once the distribution has a
name that is free there.
