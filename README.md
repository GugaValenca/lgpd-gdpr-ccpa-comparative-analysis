# LGPD · GDPR · CCPA Comparative Analysis

[![GitHub](https://img.shields.io/badge/GitHub-GugaValenca-181717?style=flat&logo=github&logoColor=white)](https://github.com/GugaValenca)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-gugavalenca-0A66C2?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/gugavalenca/)

A small Django web app that lets you explore and compare three major privacy
law frameworks — Brazil's **LGPD**, the EU's **GDPR**, and California's
**CCPA/CPRA** — side by side, and generate a downloadable PDF summary of
which frameworks apply to a hypothetical business.

The goal wasn't to write another comparison article. It was to show that legal
requirements can be modeled as structured, queryable data and turned into a tool
someone could actually use.

## Why this project

Most public "LGPD vs. GDPR vs. CCPA" content is a static table or blog post.
That's useful for reading, but it doesn't reflect how compliance work
actually happens: a business describes its situation, and someone (a
person or a tool) has to map that situation to the specific obligations
that apply. This project does that mapping directly:

- Legal content lives in a **Django data model** (`Category` × `Law` →
  `ComparisonEntry`), editable through the Django admin — not hardcoded into
  templates.
- A **"Generate compliance summary"** feature takes a few yes/no answers
  about a hypothetical business and outputs a downloadable PDF stating
  which frameworks are triggered and why, plus the key obligations under
  each one.
- A **search and category filter** make the comparison content easy to
  browse instead of scrolling one long page.

## ⚠️ A note on legal accuracy

This is a demonstration project, not a compliance product — nothing on the site
is legal advice. That said, accuracy was treated as a first-class
requirement, not an afterthought:

Every one of the 21 seeded `ComparisonEntry` rows (7 categories × 3 laws)
was checked against a primary or regulatory source — planalto.gov.br
(LGPD), eur-lex.europa.eu (GDPR), leginfo.legislature.ca.gov and cppa.ca.gov
(CCPA/CPRA) — as of **September 1, 2026**, and is seeded with
`is_verified = True`, a `source_url` pointing to the specific source used,
and a `verification_notes` field recording exactly what was checked and
when. Every specific figure — article/section citations, fine caps,
percentages, response deadlines — was confirmed against that source rather
than recalled from memory; see `comparison/management/commands/seed_data.py`
for the full citation trail.

A handful of CCPA/CPRA figures are adjusted for inflation by the CPPA every
odd-numbered year (the revenue threshold, administrative fine amounts, and
private-right-of-action statutory damages). Those entries stay accurate as
snapshots but are explicitly flagged with the next scheduled adjustment
date (January 1, 2027) so a future reader knows to recheck
[cppa.ca.gov](https://cppa.ca.gov/regulations/cpi_adjustment.html) rather
than assume the number is permanent.

If you extend the seed data yourself, follow the same discipline: any new
entry with a specific number that hasn't been checked against a current
primary source should be seeded with `is_verified = False` and a
`verification_notes` value starting with `TODO: VERIFY...` — never marked
verified on the strength of general knowledge alone. You can find every
unverified entry in the Django admin by filtering `ComparisonEntry` on
**Is verified = No**.

## Tech stack

| Layer            | Choice                                   | Why |
|-------------------|-------------------------------------------|-----|
| Backend framework  | Django 5.2                                | Clean ORM + built-in admin for reviewing/editing legal content without writing a CMS. |
| Data model         | `Law`, `Category`, `ComparisonEntry`, `ScenarioQuestion`, `ScenarioRule` | Comparison content and the applicability questionnaire are both data, not code — new categories, laws, or questions can be added from the admin. |
| Frontend           | Django templates + plain CSS + a little vanilla JS | Kept deliberately simple and dependency-free so every line is easy to explain and maintain. Search runs server-side (works with JS disabled); category filtering is layered on with ~25 lines of vanilla JS. |
| PDF generation     | [ReportLab](https://pypi.org/project/reportlab/) | Pure-Python, no system dependencies — chosen over WeasyPrint specifically to avoid WeasyPrint's GTK runtime requirement on Windows. |
| Database           | SQLite locally, Postgres in production    | SQLite needs zero setup for local development. Setting `DATABASE_URL` (or Vercel's `POSTGRES_URL`) switches to Postgres via `dj-database-url` with no code changes. |
| Hosting            | [Vercel](https://vercel.com) + [WhiteNoise](https://whitenoise.readthedocs.io/) | Python/WSGI runtime; WhiteNoise serves static files from the app itself because serverless functions have no separate static server. See **Deployment** below. |

## Project structure

```
api/index.py               # WSGI entrypoint Vercel's Python runtime routes into
vercel.json                # Vercel build/route config
pyproject.toml             # Minimal [project] table Vercel's build needs (requirements.txt is the source of truth), plus black/isort/ruff config
requirements-dev.txt       # Formatting, lint and audit tooling (not needed to run the app)
privacy_compare/           # Django project settings/urls
comparison/                # The one app
  models.py                 # Law, Category, ComparisonEntry, ScenarioQuestion, ScenarioRule
  admin.py                  # Admin config for reviewing/editing content
  views.py                  # Comparison page, About, scenario form/result/PDF
  services.py                # Applicability logic (kept out of views for testability)
  pdf.py                     # ReportLab PDF builder for the compliance summary
  forms.py                   # Dynamic Yes/No form built from ScenarioQuestion rows
  templates/comparison/      # HTML templates
  static/comparison/         # CSS + filter.js
  management/commands/
    seed_data.py              # Idempotent seed script — the actual legal content
  tests.py                    # Smoke tests: pages load, PDF generates, scenario logic
```

## Running it locally

Requires Python 3.12+ (built and tested on Python 3.13).

```bash
# from the project root
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

python manage.py migrate
python manage.py seed_data          # loads the three laws + comparison content
python manage.py createsuperuser    # optional, to log into /admin/
python manage.py runserver
```

Then visit:

- `http://127.0.0.1:8000/` — the comparison view
- `http://127.0.0.1:8000/compliance-summary/` — the questionnaire → PDF feature
- `http://127.0.0.1:8000/about/` — About/author section
- `http://127.0.0.1:8000/admin/` — review/edit the legal content

By default the app runs with a development-only fallback secret key and
`DEBUG=True`, so the steps above work with zero configuration. To override
them (required before any real deployment — see **Security notes** below),
copy `.env.example` to `.env` and fill in real values, or set
`DJANGO_SECRET_KEY` / `DJANGO_DEBUG` / `DJANGO_ALLOWED_HOSTS` as real
environment variables.

Run the test suite with:

```bash
python manage.py test comparison
```

Formatting and lint (black, isort, ruff) are configured in `pyproject.toml`:

```bash
pip install -r requirements-dev.txt
black . && isort . && ruff check .
```

## How the "compliance summary" logic works

Each `Law` has one or more `ScenarioRule` rows pointing at `ScenarioQuestion`
rows. Rules are split into two groups per law:

- **Required (AND) rules** — every one must be answered "Yes" for the law to
  apply. Used for CCPA/CPRA's baseline "does business in California"
  condition.
- **Optional (OR) rules** — any single "Yes" is enough. Used for simple
  triggers like GDPR's extraterritorial-scope question, and for "meets at
  least one threshold" conditions (revenue, data volume, revenue-from-sale)
  under CCPA/CPRA.

This mirrors, at a structural level, how each law's applicability actually
works, without hardcoding law-specific `if` statements — the logic lives in
`comparison/services.py::evaluate_scenario`, driven entirely by the
`ScenarioRule` data. Both the HTML result page and the PDF are built from
the same `build_summary_context()` call, so they can never drift apart.

## Security notes

- `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS` are read from environment
  variables with dev-only fallbacks (`privacy_compare/settings.py`,
  `.env.example`). Because this repo is public, the fallback key is public
  too, so the app **refuses to start** with `DJANGO_DEBUG=False` unless
  `DJANGO_SECRET_KEY` is set. Never commit a real `.env` file (it's
  git-ignored).
- With `DJANGO_DEBUG=False` the app turns on HTTPS redirect, secure
  cookies, and HSTS; `python manage.py check --deploy` reports no issues in
  that configuration.
- There is no admin account bundled with this repo or its seed data —
  `createsuperuser` is interactive and always asks you to set your own
  username/password. `db.sqlite3` is git-ignored, and all legal content
  lives in `comparison/management/commands/seed_data.py`, not in the
  database file.

## Deployment (Vercel)

The app is set up to deploy on Vercel's Python runtime — `vercel.json` +
`api/index.py` route every request into the Django WSGI app, and
`privacy_compare/settings.py` switches from SQLite to Postgres
automatically whenever a `DATABASE_URL`/`POSTGRES_URL` is present.
Vercel's serverless functions have no persistent disk, so production needs
a real Postgres database: SQLite's file wouldn't survive between requests,
and the questionnaire's session state is stored in the database too.

1. **Connect the repo**: in the Vercel dashboard, *Add New… → Project*,
   import `GugaValenca/lgpd-gdpr-ccpa-comparative-analysis` from GitHub.
2. **Add a Postgres database**: Project → *Storage* tab → *Create
   Database* → Postgres (a Neon-backed instance; it injects `POSTGRES_URL`
   into the project's environment variables automatically).
3. **Set the remaining environment variables** (Project → *Settings →
   Environment Variables*):
   - `DJANGO_SECRET_KEY` — a freshly generated key (command in
     `.env.example`)
   - `DJANGO_DEBUG` — `False`
   - `DJANGO_ALLOWED_HOSTS` — only needed for a custom domain; the
     `*.vercel.app` URL is trusted automatically
4. **Run migrations and load the content against the production
   database** (one-time, and again after any future model change —
   Vercel's build step doesn't run this for you):
   ```bash
   DATABASE_URL="<value from Vercel's Storage tab>" python manage.py migrate
   DATABASE_URL="<same value>" python manage.py seed_data
   DATABASE_URL="<same value>" python manage.py createsuperuser
   ```
   `seed_data` is idempotent, so re-running it after editing the seed
   file updates the rows in place.
5. **Deploy**: `vercel --prod`, or push to the connected branch.

What has been checked so far: the Vercel entrypoint (`api/index.py`) was
exercised locally with production environment variables and
`DJANGO_DEBUG=False` — every page, the app's and the admin's static
files, host-header rejection, and the full questionnaire → result → PDF
flow with CSRF enabled — and the Postgres switch was confirmed to resolve
to the `postgresql` engine. It has not yet been run against a live
Postgres instance or a live Vercel deployment.

## About the author

Gustavo Valença is a Brazilian-trained lawyer with legal team leadership
experience, working across Python/Django development and data privacy law
(LGPD, GDPR, CCPA). This project reflects that combination directly: legal
requirements modeled as structured, tested, source-cited data rather than a
static comparison table.

This is one of four related privacy tools built around the same fictional company:

1. **LGPD-GDPR-CCPA-Comparative-Analysis** (this project) — comparing the underlying legal frameworks side by side.
2. [Data-Mapping-ROPA](https://github.com/GugaValenca/data-mapping-ropa) — recording processing activities already running.
3. [DPIA-Privacy-Impact-Assessment](https://github.com/GugaValenca/dpia-privacy-impact-assessment) — assessing a new one before it launches.
4. [Incident-Breach-Response](https://github.com/GugaValenca/incident-breach-response) — handling what happens when something goes wrong.

[![GitHub](https://img.shields.io/badge/GitHub-GugaValenca-181717?style=flat&logo=github&logoColor=white)](https://github.com/GugaValenca)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-gugavalenca-0A66C2?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/gugavalenca/)
