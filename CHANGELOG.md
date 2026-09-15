# Changelog

## Refinement Pass — September 2026

A focused review pass on top of the existing, already well-structured
codebase. No features were removed and no existing behavior changed
except where noted as a bug fix.

### 🐛 Fixed

- **Superuser lockout in category & event management** (`events/views.py`).
  Several admin-only checks tested `request.user.role == "ADMIN"` but
  never checked `request.user.is_superuser`. Since a Django superuser
  created with `createsuperuser` defaults to role `ATTENDEE`, this
  silently locked superusers out of category management and out of
  editing/deleting events they didn't personally organize. Introduced
  a shared `is_admin(user)` helper (superuser OR role `ADMIN`) and
  applied it consistently — matching the pattern already used
  correctly in `dashboard/views.py` and `registrations/views.py`.

- **Past events became permanently un-editable** (`events/forms.py`).
  `EventForm` always required the event date/time to be in the
  future, even when editing an event that had already started or
  finished. That meant an organizer could never fix a typo in the
  venue or description of a past event. The form now detects when
  it's editing an event whose original date is already in the past
  and relaxes only the future-date checks for that case — all other
  validation (end time after start time, deadline before event, etc.)
  is unchanged.

- **`requirements.txt` was saved as UTF-16.** Converted to plain
  UTF-8, which is what `pip` and most tooling expect; the UTF-16
  version could fail to parse on some setups.

### 🔒 Hardened for production

- `config/settings.py`: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and
  `CSRF_TRUSTED_ORIGINS` now come from environment variables instead
  of being hardcoded, with safe development defaults so
  `runserver` still works with zero setup.
- Security settings (`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`,
  `CSRF_COOKIE_SECURE`, HSTS, `X_FRAME_OPTIONS`, content-type
  sniffing protection) now switch on automatically whenever
  `DEBUG=False`, instead of being commented out.
- Added a minimal `LOGGING` configuration so server errors are
  printed to the console/server logs instead of vanishing once
  `DEBUG=False` turns off Django's debug page.
- Added `.env.example` documenting every environment variable the
  project uses.

### 🎨 Added

- Custom, on-brand `404.html`, `500.html`, and `403.html` error
  pages. These are intentionally self-contained (not extending
  `base.html`) because Django renders the 500 page without template
  context processors — a self-contained page guarantees it always
  renders correctly, even when something else is broken.

### 📝 Documentation

- `README.md` environment-variables section rewritten to document
  every variable now read from `.env`.
