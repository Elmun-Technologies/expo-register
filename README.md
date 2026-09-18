# 🎟️ Eventify

### Smart Event Management Platform

Eventify is a full-stack **Django-based Event Management System** designed to simplify the complete event lifecycle, from creating and publishing events to attendee registration, digital ticketing, QR-based check-in, analytics, notifications, and AI-powered assistance.

It provides separate experiences for **Administrators, Organizers, and Attendees**, with a modern responsive dashboard and a customizable interface.

---

## ✨ Highlights

- 🎪 Complete event creation and management
- 👥 Role-based user experience
- 📝 Event registration and cancellation
- 🎫 Digital event tickets
- 🔳 QR-code ticket system
- 📷 QR-based attendee check-in
- 🤖 AI-powered Eventify Assistant
- 📊 Organizer and administrator dashboards
- 📈 Event and registration analytics
- 🔔 Notification system
- 🎨 Customizable appearance
- 🌙 Light, Dark, and System themes
- 🎨 Multiple theme presets
- 🔎 Event search and navigation
- 📱 Responsive Bootstrap-based interface
- 🛡️ Django authentication and administration
- 📜 MIT licensed

---

# 🚀 Features

## 👤 User Management

Eventify supports different user roles with role-specific functionality.

### Administrator

Administrators can manage and monitor the platform through the administrative dashboard.

### Organizer

Organizers can:

- Create events
- Edit events
- Publish events
- Manage their events
- Monitor registrations
- View event statistics
- Check attendees in using QR tickets

### Attendee

Attendees can:

- Browse events
- View event details
- Register for events
- Cancel registrations
- View their registrations
- Access digital tickets
- Present QR tickets for check-in

---

# 🎪 Event Management

Organizers can create detailed events containing:

- Event title
- Category
- Description
- Venue
- Event date
- Start time
- End time
- Registration deadline
- Maximum capacity
- Ticket price
- Event image
- Publication status
- Featured-event status

Eventify also validates important event scheduling rules to prevent invalid event configurations.

---

# 🎟️ Registration System

Attendees can register for published events.

The registration system handles:

- Event capacity
- Available seats
- Registration deadlines
- Duplicate registration prevention
- Registration cancellation
- Registration status
- Attendee-event relationships

Registration statuses include:

```text
REGISTERED
CANCELLED
ATTENDED
```

---

# 🎫 Digital Ticket System

Every registration receives a unique ticket identifier.

Tickets contain:

- Event information
- Attendee information
- Ticket ID
- Registration date
- Registration status
- Check-in status
- QR ticket

This provides attendees with a digital representation of their event registration.

---

# 📷 QR Check-In

Eventify includes a QR-based attendee check-in workflow.

Organizers can scan attendee QR tickets and verify:

- Ticket authenticity
- Registration status
- Whether the ticket has already been used
- Attendee information
- Event association

Once successfully checked in, the registration records the check-in state and timestamp.

---

# 🤖 Eventify Assistant

Eventify includes an AI-powered chatbot called **Eventify Assistant**.

The assistant can interact with the Eventify platform and answer event-related questions using application data.

### Example queries

```text
What events are available?

Tell me about AI Workshop.

How many seats are available for Hackathon?

What events am I registered for?

Show me my Hackathon ticket.

Cancel my Hackathon registration.

How many people are registered for my events?

Show my events.

Take me to my registrations.
```

The chatbot provides a conversational interface for discovering information and interacting with Eventify.

---

# 📊 Dashboard & Analytics

Eventify provides dashboard experiences for platform management.

Dashboard information can include:

- Total users
- Organizers
- Events
- Registrations
- Event statistics
- Registration statistics
- Recent activity
- Event performance
- Organizer information

The interface is designed to provide important information without requiring users to navigate through multiple administrative pages.

---

# 🔔 Notifications

Eventify includes a notification system for communicating important platform and event-related information to users.

Users can access their notification list directly from the dashboard.

Unread notifications are displayed through the dashboard notification indicator.

---

# 🎨 Appearance Customization

Eventify includes a dedicated appearance customization system.

Users can customize the interface through the Appearance panel.

### Theme modes

- ☀️ Light
- 🌙 Dark
- 🖥️ System

### Theme presets

- 💜 Default
- 🌊 Ocean
- 💚 Emerald
- 🌅 Sunset
- 🌹 Rose

### Accent colors

The interface also supports multiple accent colors.

The theme system uses CSS variables so that the selected appearance can propagate across the dashboard instead of changing only a single component.

---

# 🧭 Navigation

The dashboard provides quick access to major Eventify features including:

- Dashboard
- Calendar
- Events
- Categories
- Reports
- Notifications
- Profile
- Registrations
- QR Check-In

The dashboard navbar dynamically displays the relevant page title.

---

# 🛠️ Tech Stack

## Backend

- Python
- Django

## Frontend

- HTML5
- CSS3
- JavaScript
- Bootstrap 5
- Bootstrap Icons

## Database

- SQLite for local development
- Django ORM

## AI

- Google Gemini API

## Other Technologies

- QR code generation and scanning
- Django authentication
- Django templates
- CSS variables
- Responsive web design

---

# 🏗️ Project Architecture

The project follows a Django application-based architecture.

```text
Eventify
│
├── accounts/
│   └── User authentication and account functionality
│
├── events/
│   └── Event and category management
│
├── registrations/
│   └── Registration, tickets and check-in functionality
│
├── chatbot/
│   └── Eventify Assistant and chatbot API
│
├── dashboard/
│   └── Dashboard, analytics and UI components
│
├── templates/
│   └── Django HTML templates
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── media/
│   └── User-uploaded media
│
├── manage.py
├── requirements.txt
├── LICENSE
└── README.md
```

---

# ⚙️ Installation

## 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/Eventify.git
```

Move into the project directory:

```bash
cd Eventify
```

---

## 2. Create a virtual environment

### Windows

```powershell
python -m venv venv
```

Activate it:

```powershell
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

---

# 🔐 Environment Variables

Eventify is configured entirely through environment variables, so the
same codebase runs safely in both development and production.

Copy the example file and fill in real values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | Recommended | Django's cryptographic secret key. A safe development default is used if omitted, but **must** be set to a unique, random value in production. Generate one with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DJANGO_DEBUG` | No | `True` for development (default), `False` for production. Setting this to `False` automatically enables HTTPS redirects, secure cookies, and HSTS. |
| `DJANGO_ALLOWED_HOSTS` | Only if `DEBUG=False` | Comma-separated list of hostnames the app is allowed to serve, e.g. `eventify.com,www.eventify.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Only if behind HTTPS/a custom domain | Comma-separated list of trusted origins, e.g. `https://eventify.com` |
| `GEMINI_API_KEY` | Only for the AI chatbot | Enables the Eventify Assistant. Leave blank to disable it. |

Never commit your real `.env` file to GitHub — it's already excluded
via `.gitignore`.

---

# 🗄️ Database Setup

Run Django migrations:

```bash
python manage.py migrate
```

---

# 👤 Create an Administrator

Create a Django superuser:

```bash
python manage.py createsuperuser
```

Follow the prompts to configure the administrator account.

---

# ▶️ Run the Development Server

Start Django:

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

The Django administration panel is available at:

```text
http://127.0.0.1:8000/admin/
```

---

# 🧪 Django System Check

Before running the application, you can verify the project configuration with:

```bash
python manage.py check
```

A successful check should report:

```text
System check identified no issues.
```

---

# 📸 Screenshots

## Dashboard

_Add your dashboard screenshot here._

```text
screenshots/dashboard.png
```

## Event Creation

_Add your event creation screenshot here._

```text
screenshots/create-event.png
```

## Event Details

_Add your event detail screenshot here._

```text
screenshots/event-details.png
```

## AI Assistant

_Add your chatbot screenshot here._

```text
screenshots/chatbot.png
```

## QR Check-In

_Add your QR scanner screenshot here._

```text
screenshots/qr-checkin.png
```

> Screenshots can be added later to a `screenshots/` directory.

---

# 🔄 Event Lifecycle

The general Eventify workflow is:

```text
Organizer
    │
    ▼
Create Event
    │
    ▼
Publish Event
    │
    ▼
Attendee Discovers Event
    │
    ▼
Registration
    │
    ▼
Digital QR Ticket
    │
    ▼
Event Check-In
    │
    ▼
Attendance Recorded
    │
    ▼
Organizer Analytics
```

---

# 🎫 Registration Lifecycle

```text
Event Published
      │
      ▼
Attendee Registers
      │
      ▼
Registration Created
      │
      ▼
QR Ticket Generated
      │
      ▼
Attendee Presents Ticket
      │
      ▼
QR Verification
      │
      ▼
Check-In
      │
      ▼
Attendance Recorded
```

---

# 🤖 AI Assistant Workflow

```text
User
 │
 ▼
Eventify Assistant
 │
 ▼
Chatbot API
 │
 ▼
Application / Event Data
 │
 ▼
AI Processing
 │
 ▼
Contextual Response
 │
 ▼
User
```

---

# 🛡️ Security Considerations

The project uses Django's built-in security mechanisms and authentication framework.

Important development practices include:

- Keeping API keys outside source code
- Excluding `.env` from version control
- Excluding the virtual environment
- Using Django authentication
- Using CSRF protection
- Restricting organizer/admin functionality
- Validating event and registration operations

For production deployment, additional configuration should be applied for:

- Production `SECRET_KEY`
- `DEBUG=False`
- Allowed hosts
- HTTPS
- Production database
- Secure cookies
- Static/media hosting
- Production API configuration

---

# 🗺️ Future Improvements

Potential future improvements include:

- 💳 Online payment integration
- 📧 Automated email notifications
- 📱 Progressive Web App support
- 📍 Interactive event maps
- 📅 Calendar integration
- 📊 More advanced analytics
- 🧠 More advanced natural-language chatbot commands
- 🔎 Advanced event recommendations
- ⭐ Event reviews and ratings
- 📱 Mobile application
- ☁️ Cloud deployment
- 🔐 Additional security hardening

---

# 🎥 Expo Monitoring (Uzbekistan Edition)

Eventify ustiga qurilgan **Expo nazorat moduli** — ko'rgazma (expo) hududiga
kiruvchi har bir mehmonni to'liq kuzatib borish tizimi.

## Oqim

1. **Kiosk** (`/expo/kiosk/`) — mehmon ism, familiya va (ixtiyoriy) kompaniya,
   maqsad ma'lumotlarini kiritadi. O'zbekcha va ruscha interfeys.
2. Mehmon ro'yxatdan o'tishi bilan tizim **xabar** yuboradi va
   **kuzatuvni boshlaydi** (xavfsizlik xodimi panelida ko'rinadi).
3. **Monitoring** (`/expo/monitor/`) — kameralar, jonli ogohlantirishlar va
   ichkaridagi mehmonlar real vaqtda ko'rsatiladi.
4. **Stend analitikasi** (`/expo/analytics/`) — har bir stend oldiga qancha
   mehmon kelgani, qancha vaqt turishgani hisoblab chiqiladi. Bu kelajakdagi
   expolar uchun muhim statistika.

## Kameralar

- **SIMULATION** rejimi (hozirgi): haqiqiy qurilmasiz to'liq demo.
- **LIVE** rejimi: Hikvision ISAPI / RTSP qatlami tayyor
  (`expo/hikvision.py`). Kamera `ip_address`, `username`, `password`,
  `rtsp_url` kiritilgach haqiqiy oqimga ulash mumkin.

## Rollar

- **Admin** — monitor, qurilmalar, barcha stendlar statistikasi.
- **Organizer (stend egasi)** — faqat o'z stendi statistikasi.
- Mehmonlar kiosk orqali maxsus akkauntsiz ro'yxatdan o'tadi.

## Demo ma'lumotlar

```bash
python manage.py seed_expo_demo
```

8 ta kamera, 8 ta stend va `expo_admin / expo12345` admin hisobi yaratiladi.

---

# 📜 License

This project is licensed under the **MIT License**.

See the [LICENSE](LICENSE) file for details.

---

# 👨‍💻 Author

## Aryan Singh

B.Tech Computer Science & Engineering Student

Interested in:

- Full-Stack Development
- Python
- Django
- Artificial Intelligence
- Machine Learning
- Data Analytics

---

# ⭐ Support

If you find this project useful or interesting, consider giving the repository a ⭐ on GitHub.

---

<p align="center">
  Built with Python, Django, JavaScript and a little bit of Eventify magic ✨
</p>