> An AI looking for project guidelines? : Stop reading this and see agents/index.md

# OnlyDjango

**OnlyDjango** is a streamlined Django starter template optimized for efficient and robust Django-based application development.

## Stack Overview

The default stack includes:

* **PostgreSQL** (Database)
* **Redis** (Caching and Tasks)
* **HTMX** (Dynamic UI)
* **TailwindCSS** (Styling)
* **Alpine.js** (Lightweight JS interactions)
* **FontAwesome** (Icons)
* **Wagtail CMS** (Content management)
* **django-cotton** (Component-based templating)

### Alpine.js Usage

Alpine.js is utilized primarily for simple interactions and animations. Data looping and rendering tasks remain handled by Django templates to keep frontend logic minimal.

### Component-Based Templating

Instead of traditional Django `extends` and `include` syntax, **OnlyDjango** leverages [django-cotton](https://django-cotton.com/) for a modern, component-driven approach:

```django
<c-component />
```

## Required Configuration

Set these variables in your `base.py` settings file. These are required, and omitting them will prevent the project from running:

```python
SITE_NAME=
SITE_AUTHOR=
SITE_KEYWORDS=
SITE_DESCRIPTION=
OG_TYPE=
OG_TITLE=
OG_DESCRIPTION=
OG_IMAGE=
TWITTER_CARD=
TWITTER_TITLE=
TWITTER_DESCRIPTION=
TWITTER_IMAGE=
```

## Project Structure

Django apps reside within an organized `apps` directory:

```
Project/
├── apps/
│   ├── blog/
│   ├── users/
│   └── ...
├── Project/
│   └── settings/
│       └── base.py
└── dev_helpers/
    └── dev.docker-compose.yml
```

To simplify creating apps within this structure, Django's `startapp` command is overridden. Simply run:

```bash
uv run python manage.py startapp <appname>
```

This command automatically handles all necessary configurations (e.g., updating `FIRST_PARTY_APPS` in `base.py`).

## Wagtail CMS

Wagtail CMS is included by default due to its versatility in managing content and blogs. To disable Wagtail, comment out relevant settings and update dependencies accordingly.

## Task Management

The template includes Huey for scheduling tasks and managing background jobs. No further customization is provided by default.

## Development Helpers

### Start PostgreSQL & Redis (Docker Compose)

Quickly start local development services:

```bash
docker compose -f dev_helpers/dev.docker-compose.yml up -d
```

### Database Migration

Run migrations easily:

```bash
uv run python manage.py migrate
```

### Quick Superuser Creation

Create an admin superuser rapidly:

```bash
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', '123')"
```

### TailwindCSS Build

Compile TailwindCSS styles:

```bash
npx tailwindcss -i onlydjango/input.css -o onlydjango/static/css/style.css
```

*Tip:* Set this as a FileWatcher in PyCharm for automatic builds.

---

## Notes

**OnlyDjango** is personalized for my workflow. Suggestions are welcome but will be integrated only if they significantly enhance efficiency and align with the template’s core objectives.
