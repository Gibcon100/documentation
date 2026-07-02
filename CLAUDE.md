# CLAUDE.md

Guidance for AI assistants (and humans) working in this repository.

## What this repository is

This is the **HACS documentation site** — the source for <https://hacs.xyz>. HACS
(Home Assistant Community Store) is a custom integration for Home Assistant; this
repo contains only its **documentation**, not the integration code (that lives at
<https://github.com/hacs/integration>).

It is a static site built with **[MkDocs](https://www.mkdocs.org/)** using the
**[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)** theme,
written in Markdown, and deployed to **Cloudflare Pages**.

## Tech stack

- **Python 3.13** (pinned in `.python-version` / `runtime.txt`)
- **MkDocs Material** (`mkdocs-material[imaging]`) — see `requirements.txt`
- **mkdocs-macros-plugin** — Jinja-style macros in Markdown
- System dependency: `libcairo2` (needed for the `imaging`/`social` card generation)

## Common commands

Scripts live in `scripts/` and are the canonical entry points:

```bash
scripts/setup      # Install libcairo2 + pip install -r requirements.txt
scripts/develop    # mkdocs serve — live-reloading preview at http://localhost:8000
scripts/build      # mkdocs build — produces the static site in build/
```

Additional:

```bash
pre-commit run --all-files          # Runs codespell (the only lint step)
python scripts/compress_images.py   # Re-compress PNGs under source/assets/images
```

The easiest way to work locally is the **devcontainer** (`.devcontainer.json`,
Python 3.13 image), which runs `scripts/setup` automatically on create.

## Repository layout

```
mkdocs.yml              # Site config: theme, plugins, markdown extensions, and the nav tree
requirements.txt        # Python dependencies
.python-version         # Python version (3.13)
.pre-commit-config.yaml # codespell config
scripts/                # setup / develop / build / compress_images.py
source/                 # docs_dir — ALL site content lives here
├── index.md            # Home page (uses templates/home.html)
├── _redirects          # Cloudflare Pages redirect rules
├── macros.py           # mkdocs-macros: defines hacsui() and coreui() macros
├── docs/               # Main content, grouped by audience
│   ├── use/            # End-user docs (download, configure, repositories, troubleshooting)
│   ├── publish/        # For authors publishing repositories to HACS
│   ├── contribute/     # For contributors to HACS itself
│   ├── faq/            # Frequently asked questions
│   └── help/           # Help & support
├── assets/             # images/ and stylesheets/ (extra.css)
├── includes/           # abbreviations.md — auto-appended to every page
├── hooks/              # MkDocs build hooks (see below)
└── overrides/          # Theme template overrides (partials, 404, home template)
build/                  # Generated output (gitignored) — never edit or commit
.github/workflows/      # CI (actions.yml)
```

## Key conventions

### Adding or editing pages
1. Create/edit a `.md` file under `source/docs/` in the subdirectory matching its audience.
2. **Register it in the `nav:` tree in `mkdocs.yml`** — pages are not auto-discovered
   (except those listed under `not_in_nav`). An unlisted page triggers a `nav` warning.
3. Every page starts with front matter:
   ```yaml
   ---
   title: Page title (also used in the sidebar)
   description: "A summary of the page contents"
   ---
   ```

### Links and images
- **Internal links** use absolute paths from `source/` and keep the `.md` extension:
  `[Features](/docs/contribute/features.md)`. MkDocs validation resolves these
  (`validation.links.absolute_links: relative_to_docs`).
- **Images** use absolute paths too: `![image](/assets/images/features.png)`.
- **External links** use the full URL. A build hook automatically adds
  `target="_blank"` + `rel="noopener"` to external links and `loading="lazy"` to images.

### Screenshots
- Capture at **1440x900**, PNG format.
- Provide **both light and dark** variants.
- Store under `source/assets/images/screenshots/name_of_screenshot/{light,dark}.png`
  (lowercase, underscores between words).

### Macros (mkdocs-macros-plugin)
`source/macros.py` fetches the live HACS and Home Assistant frontend translation
files (cached under `.cache/translations/`) and exposes two macros so docs can
reference real UI strings:
- `{{ hacsui("some.translation.key") }}` — HACS frontend strings
- `{{ coreui("some.translation.key") }}` — Home Assistant core frontend strings

An unknown key raises an error (`on_undefined: strict`), which **fails the build**.

### Custom shortcode
`source/hooks/shortcodes.py` implements a `my` shortcode for
[my.home-assistant.io](https://my.home-assistant.io) redirect links:
```md
<!-- hacs:my redirect_name title="Link text" -->
```

### Snippets & abbreviations
- `pymdownx.snippets` is enabled; `source/includes/abbreviations.md` is auto-appended
  to every page (defines abbreviations like HACS).
- Content can be pulled in with `--8<-- "path"` syntax (see `source/index.md`).

## Build strictness

`mkdocs.yml` sets `strict: true` and enables link/anchor/nav validation. Broken
internal links, missing anchors, unregistered nav files, and undefined macro keys
will **fail the build**. Always run `scripts/build` (or at least `scripts/develop`)
before pushing to catch these.

## CI and deployment

- **CI** (`.github/workflows/actions.yml`) runs on PRs to `main`/`next` and pushes to `main`:
  1. `lint` — `pre-commit` (codespell)
  2. `build` — `scripts/setup` then `scripts/build` (only runs if lint passes)
- **Deployment** is handled by **Cloudflare Pages**. The site's working/target branch
  is `next` (`remote_branch` in `mkdocs.yml`); documentation changes should target it.
- `source/_redirects` defines Cloudflare Pages redirect rules — edit it when moving
  or renaming pages so old URLs keep working.

## Installed Agent Skills

- **`.claude/skills/frontend-design/`** — Anthropic's official `frontend-design`
  skill (from [anthropics/skills](https://github.com/anthropics/skills), Apache-2.0).
  Vendored into the repo so it is available in every Claude Code session on this
  project. It guides distinctive, intentional visual design (typography, color,
  motion, layout) and activates automatically for frontend/UI work.

## Notes for AI assistants

- This repo is **documentation content** — do not add application/integration code here.
- Keep changes scoped to Markdown, assets, `mkdocs.yml` nav, and the small Python
  helpers in `source/macros.py` / `source/hooks/`.
- When you move or rename a page, update **both** the `nav:` in `mkdocs.yml` **and**
  add a redirect in `source/_redirects`.
- Never edit files in `build/` (generated, gitignored).
- Respect the codespell allow-list (e.g. `hass` is intentionally allowed).
