# AGENTS.md

## Change Request Flow (HLD Alignment)
For every user-requested change:
- Read `HLD.md` and explicitly state whether the request is a bug fix or a feature gap relative to HLD.
- Ask any clarifying questions needed before proceeding.
- Update `HLD.md` if required to align requirements.
- Wait for explicit final confirmation before making any code changes.
- If it is a bug, investigate why the existing tests did not prevent the issue.

## Project Overview

Shodan is a Karate Dojo Management System built with Django 5.1. It manages dojos, students, training sessions, attendance (with geo-verification), memberships, and financial tracking (sales/expenses). The system supports multiple dojos with hostname-based tenant resolution.

## Project Structure

```
shodan/                     # Project root (git repo: dojo-operations)
  shodan/                   # Core Django app: Student, Session, Attendance
    models.py               # Student, StudentDocument, Session, Attendance
    admin.py                # Django admin config + custom admin actions
    service.py              # autocreate_sessions_for_dojo()
    middleware.py            # Timezone, DojoPermissions, DojoConfiguration middleware
    logging_telegram.py     # TelegramHandler for production error alerts
    forms.py                # AdminSessionForm
    tests/                  # test_session.py, test_attendance.py
  dojoconf/                 # Dojo configuration app: Dojo, Address, Classes, Event
    models.py
    admin.py                # DojoFkFilterModelAdmin base class (dojo-scoped permissions)
    tests/
  financial/                # Financial app: MembershipProduct, Membership, Sale, Expense, Category
    models.py
    admin.py                # Sale admin + auto-generate sales from memberships
    service.py              # autocreate_sales_from_memberships_for_dojo()
  web/                      # Student-facing web portal
    views.py                # Landing page, student login, session picker, attendance
    urls.py                 # URL routes for student portal
    forms.py                # EmailForm (student login)
  templates/                # Project-level templates
    base.html
    landing_page.html
    bad_configuration.html
    student/                # Student portal templates
    admin/                  # Custom admin change_list templates
  static/                   # Project-level static files
    admin/                  # Admin-specific JS
  fixtures/                 # Test/dev fixtures (auth, dojoconf)
  manage.py
  Makefile                  # All common commands
  requirements.txt
  debian-installer.sh       # Debian 12 production installer (gunicorn + nginx + postgres)
```

## Commands

All commands use the virtualenv at `venv/`. The Makefile wraps common operations.

| Task | Command |
|------|---------|
| Create venv + install deps | `make prepare` |
| Make + run migrations | `make migrations` |
| Create superuser | `make create_test_admin_user` |
| Reset database (flush) | `make database_reset` |
| Delete all migrations + reset DB | `make reset-database` |
| Collect static files | `make collectstatic` |
| Generate secret key | `make create_secret_key` |
| Pull latest from git | `make update` |
| Restart gunicorn (prod) | `make restart_gunicorn` |
| Full prod update | `make update_project` (pull + prepare + collectstatic + restart) |
| Clear expired sessions | `make clearsessions` |
| Load prod fixtures (groups) | `make load_prod_fixtures` |
| Load dev fixtures (auth + dojoconf) | `make load_dev_fixtures` |
| Freeze requirements | `make freeze` |

### Running tests

```bash
./venv/bin/python3 manage.py test shodan.tests
./venv/bin/python3 manage.py test dojoconf.tests
```

Tests use Django's `TestCase` with fixtures from `fixtures/`. Test database is `shodan_test`.

### Running the dev server

```bash
./venv/bin/python3 manage.py runserver
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Django secret key (required for production) |
| `DJANGO_DEBUG` | Enable debug mode (any value = True) |
| `AWS_ACCESS_KEY_ID` | S3 file storage |
| `AWS_SECRET_ACCESS_KEY` | S3 file storage |
| `AWS_STORAGE_BUCKET_NAME` | S3 bucket name |
| `AWS_S3_REGION_NAME` | S3 region |
| `TELEGRAM_CHAT_ID` | Telegram chat for production error alerts |
| `TELEGRAM_CHAT_TOKEN` | Telegram bot token for error alerts |

## Code Conventions

- Django apps are organized by bounded context: `shodan` (core), `dojoconf` (configuration), `financial` (money), `web` (student portal).
- All models that belong to a dojo have a `dojo` ForeignKey. Cross-app FK references are used (e.g., `financial` imports from `shodan.models` and `dojoconf.models`).
- Admin classes extend `DojoFkFilterModelAdmin` (from `dojoconf/admin.py`) for dojo-scoped queryset filtering and FK restriction for non-superuser staff.
- Custom admin actions use `get_urls()` to add custom endpoints (e.g., `autosession`, `membership` auto-generation).
- Templates extend `base.html` (student portal) or `admin/change_list.html` (admin customizations).
- Soft-delete pattern: models have `created_at`, `updated_at`, `deleted_at` DateTimeFields (soft delete is modelled but deletion is via Django admin standard delete).
- Session model auto-populates `time_from`, `time_to`, `duration`, and `name` from the related `Classes` or `Event` in `save()`.
- Attendance `save()` auto-updates the student's `hours` total (in minutes).
- Production errors are sent to a Telegram bot via a custom logging handler (`shodan/logging_telegram.py`).

## Frontend Conventions

- All public-facing pages use **TailwindCSS** (Play CDN) with dark mode auto-following the OS (`prefers-color-scheme`).
- Every public page must look modern, clean, and professional — as if created by a Big Tech company. No raw unstyled HTML.
- **Dark mode is mandatory** on all public pages. Every colour must have a `dark:` variant. Always test in both light and dark.
- `base.html` contains a global `<style type="text/tailwindcss">` block that auto-styles all native form elements (inputs, selects, textareas, checkboxes, radios). Do not add per-field CSS classes in form definitions — rely on the global layer.
- Accent colour is **red** (`red-600`) for primary actions. Success = green, warning = amber, error = red.
- Pages are **mobile-first responsive**. Students use phones. Use `grid-cols-1 sm:grid-cols-2` patterns and touch-friendly targets.
- Content is wrapped in **card sections** (`rounded-xl border shadow-sm bg-white dark:bg-gray-800`) within the `max-w-4xl` container from `base.html`.
- Admin pages (`/admin/`) use Django's built-in admin CSS and are NOT styled with Tailwind.

## Multi-Tenant Architecture

- Each `Dojo` has a `hostname` field. The `DojoConfigurationMiddleware` resolves the hostname from the request and stores `dojo_id` in the session.
- `DojoPermissionsMiddleware` filters dojos accessible to the logged-in staff user (stored in session as `user_dojos`).
- `TimezoneMiddleware` activates the dojo's timezone for the current request.
- Non-superuser staff users only see data for their assigned dojos.

## Deployment

- Production runs on Debian 12 with Gunicorn (systemd socket activation) + Nginx (TLS via Let's Encrypt).
- PostgreSQL database named `shodan`.
- `debian-installer.sh` provisions the full server: git clone, venv, gunicorn service, nginx config, PostgreSQL, iptables rules.
- Static files collected to `/var/www/static/`.
- SSL certificates managed via certbot.
