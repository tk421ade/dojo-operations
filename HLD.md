# Objective
To build a multi-tenant Karate Dojo Management System that handles dojo configuration, student management, training session scheduling, geo-verified attendance tracking, membership subscriptions, and financial record-keeping (sales and expenses).

# Roles
Super User — Django superuser with unrestricted access to all dojos, all models, and all administrative actions. Created via CLI (`manage.py createsuperuser`). Can manage all dojos without being explicitly assigned.
Dojo Staff — Non-superuser Django staff user assigned to one or more dojos. Can manage students, sessions, attendance, and financial records only for their assigned dojos. Cannot manage dojos they are not assigned to.
Student — End user (karate practitioner) who registers attendance for training sessions via the student-facing web portal. Authenticates by email only (no password); identity is resolved by matching the email to a `Student` record.

# Versions
Current — v1.0 (production). Single-server deployment on Debian 12 with Gunicorn + Nginx + PostgreSQL.
Deployment target: single server VM per installation.

# Architecture — App-as-Bounded-Context

The application is structured as four Django apps, each representing a bounded context. Apps share the same database, authentication system, and base template. Cross-app references are via Django ForeignKey (no API boundary between apps).

## Directory Structure

```
shodan/                     # Project root
  shodan/                   # Core app: Student, Session, Attendance
    models.py               # Student, StudentDocument, Session, Attendance
    admin.py                # Admin classes + custom actions (autosession)
    service.py              # autocreate_sessions_for_dojo()
    middleware.py           # Timezone, DojoPermissions, DojoConfiguration middleware
    logging_telegram.py     # TelegramHandler for production error alerts
    forms.py                # AdminSessionForm
    tests/                  # test_session.py, test_attendance.py
    settings.py             # Django settings (DB, S3, Telegram, logging)
    urls.py                 # Root URLconf (admin + web portal)
  dojoconf/                 # Dojo configuration app
    models.py               # Dojo, Address, Classes, Event
    admin.py                # DojoFkFilterModelAdmin base class + admin classes
    tests/                  # test_dojo.py
  financial/                # Financial app
    models.py               # MembershipProduct, MembershipCustomFrequency,
                            #   Membership, Category, Sale, Expense
    admin.py                # Admin classes + custom action (membership auto-sales)
    service.py              # autocreate_sales_from_memberships_for_dojo()
  web/                      # Student-facing web portal
    views.py                # Landing, student login, session picker, attendance
    urls.py                 # Student portal routes
    forms.py                # EmailForm (email-only login)
  templates/                # Project-level templates
    base.html               # Base template (new.css framework)
    landing_page.html       # Dojo landing page with Student/Instructor buttons
    bad_configuration.html  # Shown when hostname not mapped to a dojo
    student/                # Student portal templates
      student_login.html
      student_session_id.html
      student_session_attendance.html
      student_session_attendance_completed.html
    admin/                  # Custom admin change_list templates
      change_list.html      # Adds contextual help text to admin lists
      shodan/session/change_list.html     # Adds "Create Sessions Automatically" button
      financial/sale/change_list.html      # Adds "Update Sales from memberships" button
  static/
    admin/financial/membershipproduct/membership_product.js  # Toggles custom frequency inline
  fixtures/
    auth_groups_data.json   # dojostaff group with permissions
    auth_test_data.json     # Test users (admin + dojo staff)
    dojoconf_test_data.json # Test dojos, addresses, classes, events
  manage.py
  Makefile
  debian-installer.sh       # Debian 12 production installer
```

## Integration Contract

- All dojo-scoped models have a `dojo` ForeignKey to `dojoconf.Dojo`.
- Cross-app FK references are direct Python imports (e.g., `financial/models.py` imports `from shodan.models import Student`; `shodan/models.py` imports `from dojoconf.models import Dojo, Classes, Event`).
- There is no service API boundary between apps; service-layer functions (`service.py`) are called directly from admin actions.
- `DojoFkFilterModelAdmin` (in `dojoconf/admin.py`) is the base class for all dojo-scoped admin models, providing queryset filtering and FK restriction.

## URL Layout

- `/admin/` — Django admin (staff/superuser only)
- `/` — Student landing page (resolved by hostname)
- `/student` — Student email login
- `/student/session` — Next available session (auto-redirect if single session)
- `/student/session/<session_id>` — Session selection (when multiple sessions on same day)
- `/student/session/attendance` — Attendance registration (POST: creates Attendance record)
- `/student/session/attendance/compelted` — Attendance confirmation page
- `/dev/error` — Dev-only endpoint to trigger an unhandled exception (testing)

# Navigation & Entry Points

N1 - Root `/` resolves the hostname via `DojoConfigurationMiddleware`, stores `dojo_id` in the session, and renders the landing page for the matched dojo.
N2 - If no dojo matches the hostname, a "bad configuration" page is shown with the hostname that failed to resolve.
N3 - The landing page offers two entry points: "Students" (links to `/student`) and "Instructors" (links to `/admin/`).
N4 - The student portal (`/student`) uses email-only authentication: the student enters their email, and the system looks up the matching `Student` record for the current dojo.
N5 - Staff users authenticate via Django's built-in auth at `/admin/login/`.
N6 - The student session is maintained via Django session framework (`student_email` key); if the session expires, the student is redirected back to login.

# Multi-Tenant Architecture

MT1 - Each `Dojo` has a `hostname` field (e.g., `dojo.brightonkarate.com.au`).
MT2 - `DojoConfigurationMiddleware` resolves the hostname from the incoming request and stores `dojo_id` in the Django session.
MT3 - `DojoPermissionsMiddleware` resolves which dojos a staff user can access (via `Dojo.users` M2M) and stores `user_dojos` (list of dojo IDs) in the session.
MT4 - `TimezoneMiddleware` activates the dojo's configured timezone for the current request.
MT5 - Non-superuser staff users only see data for their assigned dojos (enforced by `DojoFkFilterModelAdmin`).
MT6 - Superusers bypass all dojo-scoping and can see all dojos.
MT7 - When a non-superuser staff user creates a new dojo, they are automatically assigned to it (added to `Dojo.users` and to the session's `user_dojos`).

# Use Case U1 - Dojo Configuration

U1.1 - A `Dojo` represents a karate training organization. Fields: name, email, timezone (pytz timezone), hostname, users (M2M to Django `User`), created_at, updated_at, deleted_at.
U1.2 - A `Dojo` is linked to one or more `User` accounts (staff). Non-superuser users can only see dojos they are assigned to.
U1.3 - An `Address` represents a physical training location. Fields: dojo FK, name (friendly name), street, city, state, zip_code, country, latitude, longitude. Used by `Classes` and `Event` to define where sessions are held.
U1.4 - `Address` latitude/longitude are used for geo-verification during student attendance registration (see U4).
U1.5 - A `Classes` represents a recurring weekly training class template. Fields: dojo FK, address FK, name, type (currently only "weekly"), days_of_week (PostgreSQL ArrayField of weekday names), starting_at, finishing_at (nullable), time_from, time_to, notes.
U1.6 - `Classes.get_duration()` calculates the class duration from `time_from` and `time_to` (returns `timedelta`).
U1.7 - An `Event` represents a one-off or occasional activity (e.g., seminar, grading, competition). Fields: dojo FK, address FK, name, notes. Events do not have predefined times or days; times are set per-session.
U1.8 - All configuration models use the soft-delete pattern (created_at, updated_at, deleted_at), though deletion is via Django admin's standard delete (no soft-delete query filtering is implemented).

# Use Case U2 - Student Management

U2.1 - A `Student` represents a karate practitioner. Fields: dojo FK, status (active/inactive), name, start (start date), date_of_birth, email, mobile, address1, address2, kyu (integer), dan (integer), hours (total training time in minutes), points, medical_conditions, emergency_contact, notes, created_at, updated_at, deleted_at.
U2.2 - The student `hours` field accumulates total training time in minutes. It is auto-updated when an `Attendance` record is created (see U4.8).
U2.3 - The student `points` field accumulates points (toward grading). Points are set per-attendance.
U2.4 - The student `kyu` and `dan` fields track rank progression. Kyu counts down (higher number = lower rank); dan counts up (black belt degrees).
U2.5 - The admin list view defaults to filtering by `status = active`. This is enforced in `StudentAdmin.changelist_view` by injecting the filter when no query parameters are present.
U2.6 - A `StudentDocument` can be attached to a student (e.g., medical certificate, grading certificate). Fields: student FK, name, file (uploaded to S3), notes, created_at. Files are stored in S3 under `dojo_<id>/student_<id>/file_<random>_<filename>`.
U2.7 - Student documents are managed via a `TabularInline` on the Student admin page.
U2.8 - The student `email` field is used as the sole authentication identifier for the student web portal (no password). Email must match a Student record for the current dojo.

# Use Case U3 - Session Management

U3.1 - A `Session` represents a specific training occurrence on a specific date. Fields: dojo FK, classes FK (nullable), event FK (nullable), date, name (auto-generated if empty), time_from, time_to, duration, notes, created_at, updated_at, deleted_at.
U3.2 - A session must be linked to either a `Classes` or an `Event` (validated in `Session.clean()`). Choosing both raises a validation error; choosing neither raises a validation error.
U3.3 - When a session is linked to a `Classes`, the `time_from`, `time_to`, and `duration` are auto-populated from the class template in `Session.save()` if they are not provided.
U3.4 - When a session is linked to an `Event`, the admin must manually provide `time_from`, `time_to`, and `duration` (validated in `Session.clean()` — all three are required if the session is event-based).
U3.5 - The session `name` is auto-generated in `save()` if empty: `"Event <event.name>"` for event-based sessions, `"<classes.name>"` for class-based sessions, or `"Session at <date>"` as fallback.
U3.6 - The admin session list view orders sessions with future sessions first, then past sessions. Sessions are ordered by date within each group.
U3.7 - The admin session list view has a "Create Sessions Automatically" button that triggers the `autosession` admin action.

## Auto-Creation of Sessions

U3.8 - The `autocreate_sessions_for_dojo()` service function generates future `Session` records from `Classes` templates.
U3.9 - For each class, the function iterates from `max(starting_at, today)` to `min(today + 1 month, finishing_at)` and creates a session for each matching day-of-week.
U3.10 - The function is idempotent: if a session already exists for the same date, dojo, and classes, it is skipped.
U3.11 - The function returns summary counts (sessions created vs. already existed) as admin messages.
U3.12 - The admin action processes all dojos assigned to the current staff user.
U3.13 - Superusers are blocked from running auto-session creation (the action requires a dojo assignment to determine scope).

# Use Case U4 - Student Attendance (Web Portal)

U4.1 - Students access the web portal via the dojo's hostname URL. The landing page shows the dojo name with "Students" and "Instructors" buttons.
U4.2 - Students log in by entering their email address on the `/student` page. The system looks up the `Student` record matching the email for the current dojo.
U4.3 - If no student is found with the given email, an error message is shown and the student remains on the login page.
U4.4 - After login, the system finds the next upcoming session (date >= today) for the student's dojo. If there is only one session on that date, the student is redirected directly to the session attendance page. If there are multiple sessions on the same date, the student is shown a session picker.
U4.5 - The session attendance page shows: session name, dojo name, session date/time, address details, and an interactive map (Leaflet.js + OpenStreetMap tiles).

## Geo-Verification

U4.6 - The attendance page uses the browser's `navigator.geolocation.watchPosition` API to track the student's location in real-time.
U4.7 - The page displays a countdown timer to the session start. Registration opens 30 minutes before the session start time. The timer turns green when within the 30-minute window.
U4.8 - The page displays the distance from the student's current location to the session address (Haversine formula). Registration requires the student to be within 100 meters (0.1 km) of the address. The distance indicator turns green when within 500 meters and red otherwise.
U4.9 - The attendance registration form is only shown when both conditions are met: (1) within 30 minutes of session start, and (2) within 100 meters of the address.
U4.10 - When the student clicks "Register Attendance", a POST to `/student/session/attendance` creates an `Attendance` record.
U4.11 - Server-side validation: the session start datetime (in the dojo's timezone) must be within 30 minutes of the current time. If too early, an error is shown.
U4.12 - Server-side check: if the student already has an attendance record, they are redirected to the completed page (duplicate prevention).
U4.13 - Upon successful registration, the student is redirected to a "Registration Completed" confirmation page.

## Attendance Model

U4.14 - An `Attendance` record links a `Student` to a `Session`. Fields: dojo FK, session FK, student FK, date (auto-populated from session), duration (auto-populated from session), points (optional), notes, created_at, updated_at, deleted_at.
U4.15 - On creation, `Attendance.save()` auto-populates `date` from the session date and `duration` from the session duration if not provided.
U4.16 - On creation only (`pk is None`), `Attendance.save()` adds the session duration (in minutes) to the student's `hours` total and saves the student record. Updates to existing attendance records do not re-adjust hours.
U4.17 - The student's accumulated `hours` can be viewed in the admin.

## Membership Payment Check

U4.18 - When a student views the attendance page, the system checks whether they have an active membership sale covering the current date.
U4.19 - If no active membership sale exists, or if the sale is underpaid (`paid < amount`), a payment reminder banner is displayed with the membership product details (name, frequency, amount, currency) and payment instructions (if configured on the `MembershipProduct`).

# Use Case U5 - Financial Management

## Membership Products

U5.1 - A `MembershipProduct` defines a pricing and billing template. Fields: dojo FK, name, frequency (monthly/quarterly/custom), amount, currency (AUD only), notes, payment_instructions, created_at, updated_at, deleted_at.
U5.2 - The admin form shows a "Payments" fieldset (collapsible) for `payment_instructions`, with a description explaining that these instructions are visible to students when their membership has expired or is unpaid during attendance registration.
U5.3 - When frequency is "custom", a `MembershipCustomFrequency` inline is shown (toggled via JavaScript). The custom frequency defines billing date ranges as free-text (one per line, supporting date ranges and single dates).
U5.4 - The admin JavaScript (`membership_product.js`) shows/hides the custom frequency inline based on the selected frequency value.

## Memberships

U5.5 - A `Membership` links a `Student` to a `MembershipProduct`. Fields: dojo FK, membership_product FK, student FK, status (active/cancelled), amount (auto-populated from product if empty), currency, notes, created_at, updated_at, deleted_at.
U5.6 - A student can only have one active membership per dojo. `Membership.clean()` validates this and raises a validation error if a second active membership is attempted.
U5.7 - `Membership.save()` auto-populates `amount` and `currency` from the `MembershipProduct` if not provided.

## Sales

U5.8 - A `Sale` records a financial transaction. Fields: dojo FK, membership FK (nullable), category FK (nullable), event FK (nullable), date, student FK, date_from, date_to (membership billing period), amount, paid, currency, notes, created_at, updated_at, deleted_at.
U5.9 - A sale must reference at least one of: membership, category, or event (validated in `Sale.clean()`).
U5.10 - The `date_from` and `date_to` fields define the membership billing period covered by the sale. They are used to determine membership validity during attendance checks (U4.18).
U5.11 - The admin sale list view has an "Update Sales from memberships" button that triggers the `membership` admin action.
U5.12 - Superusers are blocked from running the auto-sales action (the action requires dojo assignments to determine scope).

## Auto-Creation of Sales

U5.13 - The `autocreate_sales_from_memberships_for_dojo()` service function generates unpaid `Sale` records for active students with active memberships who do not have a covering sale for the current period.
U5.14 - For each active student, the function checks if a sale exists with `date_from <= today <= date_to` and `membership` is not null. If none exists, a new sale is created.
U5.15 - The new sale's `date_from` is set to the day after the latest existing sale's `date_to` (or today if no prior sale). The `date_to` is calculated based on the membership product frequency: monthly (+1 month) or quarterly (+3 months). Custom frequency sales require manual `date_to` entry.
U5.16 - The new sale is created with `paid = 0` (unpaid). The sale `amount` is copied from the membership's amount.
U5.17 - The function returns summary counts: active students processed, membership products count, and total memberships.

## Categories

U5.18 - A `Category` classifies sales and expenses (e.g., "Shinpads", "Training material"). Fields: dojo FK, name, notes, created_at, updated_at, deleted_at.

## Expenses

U5.19 - An `Expense` records a cost. Fields: dojo FK, event FK (nullable), category FK (nullable), name, date, amount, currency, notes, created_at, updated_at, deleted_at.

# Use Case U6 - Administration

U6.1 - The Django admin is the primary management interface for all staff users.
U6.2 - The admin site header is "Shodan Dojo Admin" with title "Shodan Admin Portal".
U6.3 - All admin model classes (except `Dojo` itself) extend `DojoFkFilterModelAdmin` which provides:
  - `formfield_for_foreignkey`: restricts the `dojo` FK dropdown to only the dojos the user is assigned to (non-superuser).
  - `get_changeform_initial_data`: pre-selects the first assigned dojo when creating new records.
  - `get_search_results`: ensures search results are filtered by assigned dojos.
  - `has_change_permission`: prevents editing objects from non-assigned dojos.
  - `has_view_permission`: prevents viewing objects from non-assigned dojos.
U6.4 - `DojoAdmin` filters the queryset to assigned dojos for non-superusers. When a non-superuser creates a new dojo, they are automatically assigned to it.
U6.5 - All admin change list views include contextual help text (via custom `change_list.html` template override) with cross-links to related admin sections.
U6.6 - Custom admin actions are registered via `get_urls()`:
  - Session admin: `autosession/` endpoint for auto-creating sessions from classes.
  - Sale admin: `membership/` endpoint for auto-creating sales from memberships.
U6.7 - Custom admin change list templates add action buttons:
  - `admin/shodan/session/change_list.html`: "Create Sessions Automatically" button.
  - `admin/financial/sale/change_list.html`: "Update Sales from memberships" button.
U6.8 - The `created_at_tz` method on `DojoFkFilterModelAdmin` renders timestamps in the dojo's timezone.

# Important Considerations

M1 - The system is built with Django 5.1 and PostgreSQL. No SQLite fallback in production (SQLite code is commented out in settings).
M2 - Multi-tenant isolation is enforced via middleware (hostname resolution, dojo permissions, timezone) and `DojoFkFilterModelAdmin`. All dojo-scoped models must extend this base admin class.
M3 - Student documents are stored in AWS S3 using `S3Boto3Storage`. The upload path is structured as `dojo_<id>/student_<id>/file_<random>_<filename>`. AWS credentials are required for document upload to function.
M4 - Attendance geo-verification uses the browser Geolocation API with `watchPosition` for real-time tracking. The server-side check validates the 30-minute window but does not re-verify distance (distance check is client-side only).
M5 - The student web portal uses email-only authentication (no password). Session state stores `student_email`. This is intentional simplicity for karate students who may not be tech-savvy.
M6 - Timezone handling: each dojo has a timezone field. `TimezoneMiddleware` activates the dojo's timezone for all requests. Timestamps in the admin are rendered in the dojo's timezone via `created_at_tz`.
M7 - Production errors (HTTP 500-level and unhandled exceptions) are sent to a Telegram bot via `TelegramHandler`. This is configured in `settings.LOGGING` with a `require_debug_false` filter (only fires in production).
M8 - The soft-delete pattern (`created_at`, `updated_at`, `deleted_at`) is modeled on most entities but deletion is performed via Django admin's standard delete mechanism (hard delete). The `deleted_at` field exists for future soft-delete query filtering.
M9 - The `Attendance.save()` method only increments student `hours` on initial creation (`pk is None`). Updates to existing attendance records do not re-calculate hours. Deleting an attendance record does not decrement hours.
M10 - Currency is limited to AUD (`CURRENCIES = [('AUD', 'AUD')]`).
M11 - The Makefile is the canonical entry point for all development and deployment operations.
M12 - The production installer (`debian-installer.sh`) provisions a complete Debian 12 server: git clone, virtualenv, gunicorn (systemd socket activation), Nginx (reverse proxy with TLS), PostgreSQL, and iptables rules. SSL certificates are managed externally via certbot.
M13 - `ALLOWED_HOSTS = ['*']` in production. This is a known security concern for future hardening.

# Data Model Relationships

```
Dojo (dojoconf)
  ├── users (M2M → Django User)
  ├── Address (dojoconf)
  │     └── latitude, longitude (for geo-verification)
  ├── Classes (dojoconf)
  │     ├── address FK → Address
  │     ├── days_of_week (ArrayField)
  │     └── time_from, time_to
  ├── Event (dojoconf)
  │     └── address FK → Address
  ├── Student (shodan)
  │     ├── hours (accumulated minutes)
  │     ├── points
  │     ├── kyu, dan
  │     └── StudentDocument (shodan)
  │           └── file → S3
  ├── Session (shodan)
  │     ├── classes FK → Classes (nullable)
  │     ├── event FK → Event (nullable)
  │     ├── date, time_from, time_to, duration
  │     └── Attendance (shodan)
  │           ├── student FK → Student
  │           ├── duration (auto from session)
  │           └── points
  ├── MembershipProduct (financial)
  │     ├── frequency (monthly/quarterly/custom)
  │     ├── amount, currency
  │     ├── MembershipCustomFrequency (financial)
  │     └── Membership (financial)
  │           ├── student FK → Student
  │           ├── status (active/cancelled)
  │           └── Sale (financial)
  │                 ├── membership FK → Membership (nullable)
  │                 ├── category FK → Category (nullable)
  │                 ├── event FK → Event (nullable)
  │                 ├── student FK → Student
  │                 ├── amount, paid, currency
  │                 └── date_from, date_to
  ├── Category (financial)
  │     ├── Sale → Category (nullable)
  │     └── Expense (financial) → Category (nullable)
  └── Expense (financial)
        ├── event FK → Event (nullable)
        ├── amount, currency
        └── date
```

# Student Portal Flow

```
Hostname Request
  │
  ▼
DojoConfigurationMiddleware
  │ resolves hostname → dojo_id in session
  ▼
/ (landing_page)
  │
  ├──► /student (student_login)
  │      │ email lookup → student_email in session
  │      ▼
  │    /student/session (student_session)
  │      │ find next upcoming session
  │      ├── single session ──► /student/session/<id>
  │      └── multiple sessions ──► session picker
  │                                ▼
  │                              /student/session/<id> (student_session_id)
  │                                │ shows countdown + geo map
  │                                ▼
  │                              /student/session/attendance (POST)
  │                                │ validates 30-min window
  │                                │ creates Attendance record
  │                                │ increments student.hours
  │                                ▼
  │                              /student/session/attendance/compelted
  │
  └──► /admin/ (Django admin)
```
