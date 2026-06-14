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
    views.py                # Landing, student login, session picker, attendance, kiosk mode
    urls.py                 # Student portal + kiosk routes
    forms.py                # EmailForm, EventWaiverForm, KioskPinForm
    context_processors.py   # dojo_context — makes dojo available in all templates
  templates/                # Project-level templates
    base.html               # Base template (new.css framework)
    landing_page.html       # Dojo landing page with Student/Instructor buttons
    bad_configuration.html  # Shown when hostname not mapped to a dojo
    student/                # Student portal templates
      student_login.html
      student_session_id.html
      student_session_attendance.html
      student_session_attendance_completed.html
    kiosk/                  # Kiosk mode templates (iPad self-service)
      kiosk_activate.html
      kiosk_home.html
      kiosk_register.html
      kiosk_attendance.html
      kiosk_attendance_sessions.html
      kiosk_attendance_completed.html
      kiosk_register_success.html
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
- `/event/<event_id>/waiver` — Public event waiver/participation form (no login required)
- `/event/waiver/list` — Event picker when multiple events have waivers enabled
- `/event/waiver/success` — Waiver submission confirmation page

# Navigation & Entry Points

N1 - Root `/` resolves the hostname via `DojoConfigurationMiddleware`, stores `dojo_id` in the session, and renders the landing page for the matched dojo.
N2 - If no dojo matches the hostname, a "bad configuration" page is shown with the hostname that failed to resolve.
N3 - The landing page offers two entry points: "Students" (links to `/student`) and "Instructors" (links to `/admin/`).
N4 - The student portal (`/student`) uses email-only authentication: the student enters their email, and the system looks up the matching `Student` record for the current dojo.
N5 - Staff users authenticate via Django's built-in auth at `/admin/login/`.
N6 - The student session is maintained via Django session framework (`student_email` key); if the session expires, the student is redirected back to login.
N7 - A subtle "Kiosk Mode" link on the landing page (`/`) links to `/kiosk/activate`. An admin enters the per-dojo PIN (`Dojo.kiosk_pin`) to activate Kiosk Mode (`kiosk_mode = True` in session). When active, the kiosk home page (`/kiosk`) shows two large buttons: New Student and Register Attendance.
N8 - Kiosk Mode is deactivated via the same PIN at `/kiosk/deactivate`.
N9 - A context processor (`web.context_processors.dojo_context`) makes the `dojo` object available in all templates, enabling the logo display in `base.html` without per-view context passing.

# Multi-Tenant Architecture

MT1 - Each `Dojo` has a `hostname` field (e.g., `dojo.brightonkarate.com.au`).
MT2 - `DojoConfigurationMiddleware` resolves the hostname from the incoming request and stores `dojo_id` in the Django session.
MT3 - `DojoPermissionsMiddleware` resolves which dojos a staff user can access (via `Dojo.users` M2M) and stores `user_dojos` (list of dojo IDs) in the session.
MT4 - `TimezoneMiddleware` activates the dojo's configured timezone for the current request.
MT5 - Non-superuser staff users only see data for their assigned dojos (enforced by `DojoFkFilterModelAdmin`).
MT6 - Superusers bypass all dojo-scoping and can see all dojos.
MT7 - When a non-superuser staff user creates a new dojo, they are automatically assigned to it (added to `Dojo.users` and to the session's `user_dojos`).

# Use Case U1 - Dojo Configuration

U1.1 - A `Dojo` represents a karate training organization. Fields: name, email, timezone (pytz timezone), hostname, kiosk_pin (4-6 digit PIN for Kiosk Mode activation), logo (image file stored in S3/local, displayed on all public pages), users (M2M to Django `User`), created_at, updated_at, deleted_at.
U1.2 - A `Dojo` is linked to one or more `User` accounts (staff). Non-superuser users can only see dojos they are assigned to.
U1.3 - An `Address` represents a physical training location. Fields: dojo FK, name (friendly name), street, city, state, zip_code, country, latitude, longitude. Used by `Classes` and `Event` to define where sessions are held.
U1.4 - `Address` latitude/longitude are used for geo-verification during student attendance registration (see U4).
U1.5 - A `Classes` represents a recurring weekly training class template. Fields: dojo FK, address FK, name, type (currently only "weekly"), days_of_week (PostgreSQL ArrayField of weekday names), starting_at, finishing_at (nullable), time_from, time_to, notes.
U1.6 - `Classes.get_duration()` calculates the class duration from `time_from` and `time_to` (returns `timedelta`).
U1.7 - An `Event` represents a one-off or occasional activity (e.g., seminar, grading, competition). Fields: dojo FK, address FK, name, notes, requires_waiver (boolean, default False — enables the waiver form link on the landing page), waiver_success_message (nullable text — custom message shown on the waiver success page). Events do not have predefined times or days; times are set per-session.
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

# Use Case U7 - Event Waivers

## Waiver Form

U7.1 - An `EventWaiver` stores a signed participation/liability waiver for an `Event`. Fields: dojo FK, event FK, student FK (nullable), first_name, last_name, address, suburb, state, post_code, phone, email, date_of_birth, current_grade, emergency_contact_name, emergency_contact_relationship (nullable), emergency_contact_phone, terms_accepted (Boolean), questionnaire_responses (JSONField — dict of question number → "yes"/"no"), medical_specify (nullable text), other_reason_specify (nullable text), allergies (nullable text), applicant_signature (FileField→S3), applicant_name, applicant_date, guardian_signature (FileField→S3, nullable), guardian_name (nullable), guardian_date (nullable), created_at, updated_at, deleted_at.

U7.2 - The waiver form is public (no login required). The URL pattern is `/event/<event_id>/waiver`. The dojo is resolved from the hostname via `DojoConfigurationMiddleware` (same as all other pages). The event must belong to the resolved dojo.

U7.3 - The `student` FK is auto-matched by email within the resolved dojo. If the email matches a `Student` record for this dojo, the FK is set. External students (from other dojos) will have `student = null`.

U7.4 - The waiver form captures: personal information (name, address, phone, email, DOB, grade), emergency contact details, terms & conditions acceptance (checkbox), a physical readiness questionnaire (14 yes/no questions with 2 optional "please specify" text fields), allergies, and two digital signatures (applicant + guardian). The "Please specify" fields for Q13 and Q14 are hidden by default and only shown when the participant answers "Yes" to the respective question. When "Yes" is selected, the specify field becomes required (validated server-side).

U7.5 - The waiver terms text, instructor names, and venue information are a fixed template hardcoded in the template (not configurable per event in the admin).

U7.5.1 - An `Event` has a `requires_waiver` boolean field (default False). When enabled, an "Events" button appears on the dojo's landing page. If only one event has `requires_waiver=True`, the button links directly to `/event/<event_id>/waiver`. If multiple events have waivers enabled, the button links to `/event/waiver/list` (an event picker page). The admin controls this flag per event.

## Digital Signatures

U7.6 - Signatures are captured via the `signature_pad` JavaScript library (loaded from CDN). Two canvas elements are rendered: one for the applicant signature and one for the guardian signature (optional, for applicants under 18).

U7.7 - On form submission, JavaScript converts each canvas to a base64 PNG string and populates hidden form fields. The server decodes the base64 data and saves the image to S3 using `S3Boto3Storage` (or local `FileSystemStorage` when AWS is not configured), following the same storage pattern as `StudentDocument`. Files are stored under `dojo_<id>/waiver_<id>/`.

U7.8 - Each signature pad has a "Clear" button to reset the canvas.

U7.9 - The applicant signature is always required. The guardian signature section (signature, name, and date) is hidden by default and only displayed when the participant's date of birth indicates they are under 18 years old. When under 18, the guardian signature, guardian name, and guardian date all become required (validated server-side). Date of birth is a required field on the waiver form.

## Anti-Bot Mechanism (Honeypot)

U7.10 - The waiver form includes a hidden honeypot field named `email2` (visually hidden off-screen, not `display:none`). Legitimate users will never see or interact with this field. Bots that auto-fill form fields will populate it.

U7.11 - On submission, if the honeypot field `email2` has a value, the submission is silently rejected: the bot receives a normal success response (success page rendered), but no `EventWaiver` record is created. This follows the same honeypot pattern used in the locoroo project (locoroo HLD U2).

## Duplicate Prevention

U7.12 - If an `EventWaiver` already exists for the same email + event combination, the form shows an informational message ("You have already signed the waiver for this event") and does not allow re-submission.

## Admin

U7.13 - `EventWaiverAdmin` extends `DojoFkFilterModelAdmin` for dojo-scoped access. The admin list view shows applicant name, event, email, and submission date. Detail view is fully read-only, displaying all submitted data including signature images as clickable thumbnails.

U7.14 - Staff can filter waivers by event and search by applicant name or email.

## URL Layout

U7.15 - `/event/<event_id>/waiver` — Public waiver form (GET: render form, POST: process submission).
U7.16 - `/event/waiver/success` — Waiver submission confirmation page. Displays a custom per-event success message (configured via `Event.waiver_success_message`) if set, otherwise a generic default message. The event ID is stored in the session on submission and read on the success page.
- `/kiosk` — Kiosk home page (New Student / Register Attendance buttons)
- `/kiosk/activate` — PIN entry to enable Kiosk Mode
- `/kiosk/deactivate` — PIN entry to disable Kiosk Mode
- `/kiosk/register` — New student registration (full waiver form, creates Student + StudentWaiver)
- `/kiosk/register/success` — Registration success page (auto-redirects to `/kiosk` after 5s)
- `/kiosk/attendance` — Attendance email entry (finds/creates today's session, shows session picker if multiple)
- `/kiosk/attendance/session/<session_id>` — Register attendance for a specific session
- `/kiosk/attendance/completed` — Attendance success page (auto-redirects to `/kiosk` after 5s)
- `/kiosk/attendees` — View Attendees PIN entry (instructor only)
- `/kiosk/attendees/session/<session_id>` — Attendee list for a specific session (name, emergency contact, medical conditions)

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

# Use Case U8 - Frontend Design Standards

U8.1 - All public-facing pages (student portal, event waivers, landing page) use **TailwindCSS** delivered via the Play CDN (`https://cdn.tailwindcss.com`). Tailwind is configured with `darkMode: 'media'` so dark/light mode auto-follows the user's OS setting (`prefers-color-scheme`).

U8.2 - `base.html` is the single foundation template. It loads Tailwind, the Inter font, and a global `<style type="text/tailwindcss">` block that applies Tailwind utility classes to all native HTML form elements (inputs, selects, textareas, checkboxes, radios, labels). This ensures Django-rendered form widgets are styled automatically without per-field class annotations.

U8.3 - **Design quality target**: every public page must look modern, clean, and professional — comparable to a modern Big Tech / SaaS product UI. No raw HTML elements, no unstyled inputs, no broken dark mode.

U8.4 - **Dark mode is mandatory** on all public pages. Every colour, border, background, and shadow must have a `dark:` variant. Test in both light and dark modes.

U8.5 - **Responsive design**: all pages are mobile-first. Students primarily access the portal on phones. Use responsive grid/flex layouts (`grid-cols-1 sm:grid-cols-2`), readable font sizes, and touch-friendly tap targets (min 44px).

U8.6 - **Accent colour** is red (`red-600` / `hover:red-700`) for primary actions (submit buttons, active links, focus rings). Secondary actions use gray. Success states use green. Warning states use amber.

U8.7 - **Card-based layout**: forms and content sections are wrapped in rounded cards (`rounded-xl border shadow-sm`) with light/dark variants. The page is constrained to `max-w-4xl` with consistent padding. Kiosk templates override this padding via `{% block container_class %}` and `{% block header_class %}` blocks to achieve a compact, no-scroll layout on tablets.

U8.8 - **Form inputs**: styled via the global Tailwind layer in `base.html`. All inputs have rounded borders, focus rings (red), and dark mode backgrounds. Labels are above inputs, using `text-sm font-medium`.

U8.9 - **Error states**: Django `errorlist` elements are styled as red text. Alert banners use coloured borders + backgrounds (red for errors, amber for warnings, green for success) with SVG icons.

U8.10 - Admin pages (`/admin/`) continue to use Django's built-in admin CSS and are **not** part of the Tailwind design system.

U8.11 - **Dojo logo**: when a `Dojo.logo` is uploaded, it is displayed on all public pages via the `base.html` header. The logo is rendered on a white card surface (`bg-white rounded-xl`) regardless of light/dark mode, so transparent PNGs designed for white backgrounds always display correctly. When no logo is set, the text-only header is shown (current behavior). A context processor (`web.context_processors.dojo_context`) makes the `dojo` object available in all templates.

# Use Case U9 - Kiosk Mode

## Overview

U9.1 - Kiosk Mode transforms the student-facing landing page into a self-service tablet interface (Samsung Galaxy Tab / iPad) for use at the dojo during class. It enables two flows: New Student Registration and Attendance Registration — both optimized for touch and shared-device use.

## Activation & Deactivation

U9.2 - Kiosk Mode is activated via a per-dojo PIN (`Dojo.kiosk_pin`, 4-6 digits). A subtle "Kiosk Mode" link on the landing page (`/`) links to `/kiosk/activate` where the admin enters the PIN.
U9.3 - If `Dojo.kiosk_pin` is not set (null/empty), activation is refused with a message directing the admin to configure it in the admin panel.
U9.4 - Kiosk Mode state is stored in the Django session (`kiosk_mode = True`). It persists until explicitly deactivated or the session expires.
U9.5 - Deactivation is via the same PIN. A small "Exit Kiosk Mode" link on the kiosk home page (`/kiosk/deactivate`) prompts for the PIN. On correct entry, `kiosk_mode` is set to `False` and the user is redirected to the landing page.

## Kiosk Home

U9.6 - The kiosk home page (`/kiosk`) shows touch-friendly buttons: "New Student" (links to `/kiosk/register`) and "Register Attendance" (links to `/kiosk/attendance`) arranged in a responsive grid (side-by-side on tablet, stacked on phone). A subtle "Exit Kiosk Mode" link is at the bottom. The entire page must fit within the viewport without scrolling on a tablet (Samsung Galaxy Tab landscape).
U9.7 - If kiosk mode is not active, `/kiosk` redirects to the landing page.
U9.7a - **Compact layout**: All kiosk templates use reduced container padding and header margins via `{% block container_class %}` and `{% block header_class %}` hooks in `base.html`. This ensures the kiosk home, PIN entry, attendance, and success screens fit without scrolling on tablet displays. The waiver registration form (`/kiosk/register`) is exempt as it is inherently a long form requiring scroll.

## New Student Registration

U9.8 - The registration form (`/kiosk/register`) reuses the full waiver form (same fields as `EventWaiverForm`): personal information, emergency contact, terms & conditions, 14-question physical readiness questionnaire, allergies, and digital signatures (applicant + guardian for under-18s).
U9.9 - The same honeypot anti-bot mechanism (`email2` field) is used as in the event waiver form (U7.10-U7.11).
U9.10 - On submission, two records are created:
  - A `Student` record with `status=active`. The `name` field is the concatenation of `first_name + " " + last_name`. Other fields are mapped: email, mobile (from phone), date_of_birth, address1 (from address), address2 (suburb/state/postcode combined), emergency_contact, medical_conditions, start (today's date), kyu (parsed from current_grade).
  - A `StudentWaiver` record linked to the new Student, storing the full waiver data: questionnaire responses (JSONField), allergies, medical details, terms acceptance, and digital signatures (uploaded to S3/local storage).
U9.11 - Duplicate prevention: if a `Student` with the same email already exists in the dojo **and has a `StudentWaiver`**, a message is shown ("already registered — use Register Attendance") and no new records are created. If the student exists but has **no waiver**, the form creates a waiver for the existing student (no new Student record is created).
U9.12 - After successful registration, the user is redirected to `/kiosk/register/success` which displays a welcome message and auto-redirects back to the kiosk home after 5 seconds.

## Attendance Registration

U9.13 - The attendance flow (`/kiosk/attendance`) uses email-only student lookup (same as the regular student portal). The student enters their email, and the system looks up the matching `Student` for the current dojo.
U9.14 - If no student is found, an error message is shown directing them to register as a new student first.
U9.15 - **Session auto-creation**: the `get_or_create_today_sessions(dojo_id)` service function is called. It finds today's `Session` records. If none exist, it auto-creates sessions from `Classes` templates whose `days_of_week` matches today's weekday name and whose date range includes today. This is idempotent (existing sessions are not duplicated).
U9.16 - If no sessions exist and no `Classes` templates match today's weekday, an error is shown: "No class scheduled for today."
U9.17 - If a single session exists, attendance is registered immediately (no session picker).
U9.18 - If multiple sessions exist for today, a session picker page is shown (`/kiosk/attendance/sessions`) displaying clickable session cards. Each card POSTs to `/kiosk/attendance/session/<session_id>` to register attendance.
U9.19 - **Geo-verification is bypassed** in Kiosk Mode. The kiosk device (iPad) is trusted to be at the dojo location. No GPS distance check or 30-minute window constraint is applied.
U9.20 - Duplicate prevention: if the student already has an `Attendance` record for the session, a message is shown ("already registered") and no new record is created.
U9.21 - After registering attendance (or finding a duplicate), the system checks whether the student has a `StudentWaiver`. If the student has a waiver, they are redirected to `/kiosk/attendance/completed` (confirmation message, auto-redirect to kiosk home after 5 seconds).
U9.21a - **Waiver after attendance**: If the student has **no `StudentWaiver`**, attendance is still registered (non-blocking). The student is redirected to `/kiosk/register` with:
  - `kiosk_waiver_pending_email` set in the session (used to pre-fill the email field and show a contextual "Your attendance is registered!" banner).
  - The page title changes to "Complete Your Waiver" instead of "New Student Registration".
  - The email field is pre-filled and read-only behaviour is not enforced (student can still edit it).
U9.21b - After completing the waiver from the post-attendance flow, the student is redirected to `/kiosk/register/success` which displays "Waiver Submitted!" (instead of "Welcome to {dojo.name}!") and auto-redirects to the kiosk home after 5 seconds. The `kiosk_waiver_pending_email` session key is cleared.
U9.21c - **Pending waiver state cleanup**: The `kiosk_waiver_pending_email` session key is cleared whenever the kiosk home page (`/kiosk`) is loaded. This prevents stale waiver-pending state from leaking across different users on a shared kiosk device (e.g., a student walks away after attendance without completing the waiver; the next person clicking "New Student" must see a clean registration form).

## StudentWaiver Model

U9.22 - A `StudentWaiver` stores the full waiver/registration data for a new student. Fields: dojo FK, student FK (non-nullable), first_name, last_name, address, suburb, state, post_code, phone, email, date_of_birth, current_grade, emergency_contact_name, emergency_contact_relationship, emergency_contact_phone, terms_accepted (Boolean), questionnaire_responses (JSONField), medical_specify, other_reason_specify, allergies, applicant_signature (FileField → S3), applicant_name, applicant_date, guardian_signature (FileField → S3, nullable), guardian_name, guardian_date, created_at, updated_at, deleted_at.
U9.23 - `StudentWaiverAdmin` extends `DojoFkFilterModelAdmin` for dojo-scoped access. The admin detail view is fully read-only, displaying all submitted data including signature images as clickable thumbnails and questionnaire responses as a formatted table (same pattern as `EventWaiverAdmin`).

## View Attendees (Instructor)

U9.24 - The kiosk home page shows a third button, "View Attendees" (bordered/outline style, labeled "Instructor only - PIN required"), visible only when sessions exist for today (`has_sessions`).
U9.25 - "View Attendees" requires the dojo PIN (`Dojo.kiosk_pin`) on every access. The PIN entry form is shown at `/kiosk/attendees` (GET). On correct PIN (POST), `kiosk_attendees_verified` is set to `True` in the session.
U9.26 - After PIN validation, the system determines today's sessions via `get_or_create_today_sessions()`:
  - 0 sessions → error message "No class scheduled for today."
  - 1 session → redirect to `/kiosk/attendees/session/<id>` (attendee list).
  - Multiple sessions → session picker page (`/kiosk/attendees/session` template) with links to `/kiosk/attendees/session/<id>`.
U9.27 - Direct access to `/kiosk/attendees/session/<id>` without `kiosk_attendees_verified` in the session redirects to the PIN entry page.
U9.28 - The attendee list (`/kiosk/attendees/session/<id>`) shows all students with an `Attendance` record for the selected session. Each attendee is displayed as a card with:
  - Student name.
  - Emergency contact data (name, relationship, phone). When a `StudentWaiver` exists, the structured fields (`emergency_contact_name`, `emergency_contact_relationship`, `emergency_contact_phone`) are used. Otherwise, the `Student.emergency_contact` text field is used as a fallback.
  - Declared medical conditions, shown in an amber-highlighted section with a "Medical Alert" badge:
    - Any questionnaire "Yes" answers (from `StudentWaiver.questionnaire_responses`) mapped to human-readable labels via `QUESTIONNAIRE_LABELS`.
    - The `StudentWaiver.allergies` text if not empty.
    - The `StudentWaiver.medical_specify` text if not empty.
  - For students without a waiver, `Student.medical_conditions` text is shown if not empty. A "No waiver on file" note is displayed.
U9.29 - Attendees are sorted alphabetically by name. If no students are registered for the session, an empty state message is shown ("No students registered yet").
U9.30 - The attendee list page includes a "Select another class" link (back to session picker) and a "Back to Kiosk" link.

## Kiosk Security

U9.31 - **Honeypot**: All kiosk PIN forms (`KioskPinForm`) include a hidden `website` honeypot field (same pattern as the waiver form's `email2`). If a bot fills this field, a fake "Login Completed!" success page is rendered (`kiosk_fake_success.html`) — the bot believes it succeeded but no PIN is processed, no session state changes, and no functionality is granted.

U9.32 - **Rate limiting (lockout)**: The `Dojo` model has two security fields:
  - `kiosk_locked` (BooleanField, default False) — when True, all kiosk PIN entry is blocked.
  - `kiosk_failed_attempts` (IntegerField, default 0) — consecutive failed PIN attempts counter.

U9.33 - All three PIN entry points (`/kiosk/activate`, `/kiosk/deactivate`, `/kiosk/attendees`) share the same counter and lock state on the `Dojo` model. The `_process_kiosk_pin(request, dojo, form)` helper centralises the security logic.

U9.34 - **Counter behaviour**:
  - Wrong PIN → `kiosk_failed_attempts` incremented by 1, logged at WARNING level with the client IP address (via `_get_client_ip` which checks `X-Forwarded-For` then `REMOTE_ADDR`).
  - Correct PIN → `kiosk_failed_attempts` reset to 0.
  - `kiosk_failed_attempts >= 10` → `kiosk_locked` set to True, Telegram alert sent, locked page shown.

U9.35 - **Lockout Telegram alert**: When the lock triggers, `_send_kiosk_lock_alert(dojo, ip)` sends a direct, concise message via `Bot.send_message()` (not the verbose `TelegramHandler`): dojo name, failed attempt count, last attempt IP, and instruction for admin to unlock. Silently skips if Telegram is not configured.

U9.36 - **Locked state behaviour**:
  - All PIN entry pages show a "Kiosk Mode is locked" message with a lock icon instead of the PIN form.
  - No PIN is processed (even the correct PIN is rejected).
  - Student-facing kiosk features (registration, attendance) **continue to work** — only PIN-gated actions are blocked.

U9.37 - **Admin unlock**: The Dojo admin page (`DojoAdmin`) includes `kiosk_locked` (editable checkbox) and `kiosk_failed_attempts` (readonly) in the Kiosk Mode fieldset. An "Unlock kiosk mode" admin action (`unlock_kiosk`) resets both fields to their defaults in one click. Unchecking `kiosk_locked` and saving also works but does not reset the counter (the action does both).

# Important Considerations

M1 - The system is built with Django 5.2 and PostgreSQL. No SQLite fallback in production (SQLite code is commented out in settings).
M2 - Multi-tenant isolation is enforced via middleware (hostname resolution, dojo permissions, timezone) and `DojoFkFilterModelAdmin`. All dojo-scoped models must extend this base admin class.
M3 - Student documents and waiver signatures are stored in AWS S3 using `S3Boto3Storage` when AWS credentials are configured (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`). When these are absent (e.g., dev environments), the system falls back to local file storage (`FileSystemStorage` under `MEDIA_ROOT`). The upload path is structured as `dojo_<id>/student_<id>/file_<random>_<filename>` for documents and `dojo_<id>/waiver_<id>/` for waiver signatures.
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
  └── EventWaiver (shodan)
        ├── event FK → Event
        ├── student FK → Student (nullable)
        ├── personal info, emergency contact
        ├── questionnaire_responses (JSONField)
        ├── applicant_signature → S3
        └── guardian_signature → S3 (nullable)
  └── StudentWaiver (shodan)
        ├── student FK → Student (non-nullable)
        ├── personal info, emergency contact
        ├── questionnaire_responses (JSONField)
        ├── applicant_signature → S3
        └── guardian_signature → S3 (nullable)
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

# Kiosk Mode Flow

```
Landing Page (/)
  │
  ├──► "Kiosk Mode" link
  │      ▼
  │    /kiosk/activate
  │      │ PIN entry → kiosk_mode = True in session
  │      ▼
  │    /kiosk (Kiosk Home)
  │      │
  │      ├──► /kiosk/register (New Student)
  │      │      │ Full waiver form (personal info, questionnaire, signatures)
  │      │      │ creates Student (status=active) + StudentWaiver
  │      │      ▼
  │      │    /kiosk/register/success → auto-redirect 5s → /kiosk
  │      │
  │      └──► /kiosk/attendance (Register Attendance)
  │             │ email lookup → student
  │             │ get_or_create_today_sessions() → auto-create from Classes if needed
  │             │
  │             ├── single session ──► register attendance immediately
  │             └── multiple sessions ──► /kiosk/attendance/sessions (picker)
  │                                        ▼
  │                                      /kiosk/attendance/session/<id>
  │                                        │ creates Attendance (no GPS, no 30-min check)
  │                                        │
  │                                        ├── has waiver? ──► /kiosk/attendance/completed
  │                                        │                    │ auto-redirect 5s → /kiosk
  │                                        │
  │                                        └── no waiver? ──► /kiosk/register
  │                                                           │ pre-filled email, "attendance registered" banner
  │                                                           │ creates StudentWaiver for existing student
  │                                                           ▼
  │                                                         /kiosk/register/success ("Waiver Submitted!")
  │                                                           │ auto-redirect 5s → /kiosk
  │      │
  │      └──► /kiosk/attendees (View Attendees — instructor only)
  │             │ PIN required every time (kiosk_attendees_verified in session)
  │             │
  │             ├── single session ──► /kiosk/attendees/session/<id>
  │             └── multiple sessions ──► session picker ──► /kiosk/attendees/session/<id>
  │                                        │ attendee cards: name, emergency contact, medical flags
  │                                        │ medical data from StudentWaiver (or Student fallback)
  │                                        │ amber highlight for medical conditions
  │                                        ▼
  │                                      ← Back to /kiosk
  │
  └──► "Exit Kiosk" link
         ▼
       /kiosk/deactivate
         │ PIN entry → kiosk_mode = False
         ▼
       / (Landing Page)
```
