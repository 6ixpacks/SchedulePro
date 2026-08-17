# SchedulePro — Personal Scheduling Web Application

A Django-based appointment scheduling app for a service business (built around
a hair salon/barbershop example, but easily adapted to any appointment-based
business — consulting, tutoring, clinics, fitness training, etc.).

## Features

- **Customer accounts** — sign up, log in, book appointments, view upcoming/past
  bookings, cancel appointments.
- **Staff accounts** — set weekly recurring availability, block out time off,
  view/confirm/complete/cancel their appointments from a dashboard.
- **Business admin** — manage the service catalog (name, duration, price,
  which staff offer it) and has full access to Django's built-in admin site
  for everything else.
- **Smart slot picker** — the booking page uses AJAX calls to compute real
  open time slots for a chosen service + staff member + date, factoring in
  the staff member's weekly hours, approved time off, and existing bookings.
- **Conflict-safe booking** — server-side validation (`Appointment.clean()`)
  re-checks for overlaps at submission time, so two customers can't grab the
  same slot in a race condition.
- **Role-based access** — a `Profile` model (customer / staff / admin) sits on
  top of Django's `User` model and is auto-created via a signal on signup.

## Project layout

```
schedulepro/
├── accounts/          # Custom Profile model, signup/login/profile views
├── booking/           # Service, StaffAvailability, TimeOff, Appointment
│   ├── availability.py    # Slot-computation logic
│   └── management/commands/seed_demo_data.py
├── templates/          # Bootstrap 5 templates (base.html + per-app folders)
├── static/
├── schedulepro/         # Project settings/urls
└── manage.py
```

## Setup

```bash
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install django

python manage.py migrate
python manage.py seed_demo_data   # optional: demo superuser, 2 staff, 3 services
python manage.py runserver
```

Visit http://127.0.0.1:8000/

### Demo accounts (created by `seed_demo_data`)

| Role  | Username | Password      |
|-------|----------|---------------|
| Admin (superuser) | `admin` | `admin12345` |
| Staff | `jane`   | `staffpass123` |
| Staff | `sam`    | `staffpass123` |

Sign up as a new user via the site to get a **customer** account, then book
an appointment with Jane or Sam.

## Key design decisions

- **SQLite** for zero-config local development — swap `DATABASES` in
  `settings.py` for Postgres/MySQL in production.
- **Weekly recurring availability** (`StaffAvailability`) rather than
  one-off calendar entries — simpler for a small business to maintain.
  `TimeOff` handles the exceptions (holidays, sick days).
- **AJAX slot picker** avoids full-page reloads and lets the same view
  (`get_available_slots` in `booking/availability.py`) power both the UI
  and the final server-side validation, so the rules can't drift apart.
- **Django's built-in auth + admin** are used as much as possible rather
  than reinventing user management — `Profile.role` is the only real
  addition needed for role-based views.

## Extending it

- Email/SMS reminders: swap `EMAIL_BACKEND` in `settings.py` for a real
  backend and add a scheduled task (e.g. Celery beat or a cron + management
  command) that emails appointments starting soon.
- Payments: add a `paid` boolean or link out to Stripe Checkout from the
  appointment confirmation step.
- Recurring appointments, multi-location support, or a public "book without
  an account" flow are natural next features once the core loop is solid.
