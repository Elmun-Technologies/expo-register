"""
Demo ma'lumotlar: kameralar, stendlar, admin foydalanuvchi.

Ishga tushirish:
    python manage.py seed_expo_demo
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from expo import simulation
from expo.models import Booth, Camera

User = get_user_model()

CAMERAS = [
    ("Kamera 1 — Kirish", "Kirish (Entrance)", "192.168.1.101", 80),
    ("Kamera 2 — Hall A", "Asosiy zal (Hall A)", "192.168.1.102", 80),
    ("Kamera 3 — Hall B", "Asosiy zal (Hall B)", "192.168.1.103", 80),
    ("Kamera 4 — Texno", "Texnologiyalar zonasi", "192.168.1.104", 80),
    ("Kamera 5 — Startaplar", "Startaplar zonasi", "192.168.1.105", 80),
    ("Kamera 6 — B2B", "B2B muzokaralar zonasi", "192.168.1.106", 80),
    ("Kamera 7 — Media", "Media zona", "192.168.1.107", 80),
    ("Kamera 8 — Demo zal", "Ko'rgazma zali (Demo)", "192.168.1.108", 80),
]

BOOTHS = [
    ("A01", "AloqaBank Digital", "Asosiy zal (Hall A)"),
    ("A02", "UzAuto Tech", "Asosiy zal (Hall A)"),
    ("B01", "BePro Startup", "Asosiy zal (Hall B)"),
    ("B02", "iTeach Academy", "Asosiy zal (Hall B)"),
    ("T01", "Turon Robotics", "Texnologiyalar zonasi"),
    ("S01", "Click Ventures", "Startaplar zonasi"),
    ("M01", "Mediabay", "Media zona"),
    ("D01", "Kaspersky Demo", "Ko'rgazma zali (Demo)"),
]


class Command(BaseCommand):
    help = "Expo demo ma'lumotlarini yaratish (kameralar, stendlar, admin)"

    def handle(self, *args, **options):
        self._cameras()
        self._booths()
        self._admin()
        self._security()
        self._demo_attendee()
        self.stdout.write(self.style.SUCCESS("Expo demo ma'lumotlari tayyor!"))

    def _cameras(self):
        created = 0
        for name, zone, ip, port in CAMERAS:
            _, was_created = Camera.objects.get_or_create(
                name=name,
                defaults={
                    "zone": zone,
                    "ip_address": ip,
                    "port": port,
                    "mode": Camera.Mode.SIMULATION,
                    "username": "admin",
                    "password": "",
                },
            )
            created += int(was_created)
        self.stdout.write(f"  Kameralar: {created} ta yangi")

    def _booths(self):
        created = 0
        for number, name, zone in BOOTHS:
            _, was_created = Booth.objects.get_or_create(
                booth_number=number,
                defaults={"name": name, "zone": zone},
            )
            created += int(was_created)
        self.stdout.write(f"  Stendlar: {created} ta yangi")

    def _admin(self):
        username = "expo_admin"
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": "Expo",
                "last_name": "Administrator",
                "is_staff": True,
                "is_superuser": True,
                "role": User.Role.ADMIN,
            },
        )
        if created:
            user.set_password("expo12345")
            user.save()
            self.stdout.write(f"  Admin yaratildi: {username} / expo12345")
        else:
            self.stdout.write(f"  Admin allaqachon mavjud: {username}")

    def _security(self):
        username = "security"
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": "Sherzod",
                "last_name": "Qodirov",
                "role": User.Role.SECURITY,
            },
        )
        if created:
            user.set_password("security123")
            user.save()
            self.stdout.write(f"  Xavfsizlik xodimi: {username} / security123")
        else:
            self.stdout.write(f"  Xavfsizlik xodimi allaqachon mavjud: {username}")

    def _demo_attendee(self):
        """
        Bot orqali ro'yxatdan o'tgan demo mehmon — QR tiket bilan.
        Manager darvoza skaneri shu QR ni o'qib uni ichkariga kiritadi.
        """
        from events.models import Event, EventCategory
        from registrations.models import Registration
        from registrations.utils import generate_ticket_qr

        username = "mehmon_demo"
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": "Akmal",
                "last_name": "Rahimov",
                "role": User.Role.ATTENDEE,
            },
        )
        if created:
            user.set_password("mehmon12345")
            user.save()

        category, _ = EventCategory.objects.get_or_create(
            name="Texnologiya",
            defaults={"slug": "texnologiya"},
        )
        # Organizer — admin foydalanuvchi (yoki biron organizator).
        organizer = (
            User.objects.filter(role=User.Role.ORGANIZER).first()
            or User.objects.filter(is_superuser=True).first()
            or User.objects.filter(username="expo_admin").first()
        )
        if not organizer:
            organizer = User.objects.create_user(
                username="expo_organizer",
                first_name="Expo",
                last_name="Organizer",
                role=User.Role.ORGANIZER,
            )

        event, _ = Event.objects.get_or_create(
            title="O'zbekiston Expo — Texnologiyalar 2026",
            defaults={
                "slug": "ozbekiston-expo-texnologiyalar-2026",
                "description": "O'zbekiston texnologiyalar ko'rgazmasi",
                "venue": "Toshkent, Uzexpocentre",
                "category": category,
                "organizer": organizer,
                "status": Event.Status.PUBLISHED,
                "event_date": "2026-10-15",
                "start_time": "10:00:00",
                "end_time": "18:00:00",
                "registration_deadline": "2026-10-14T23:59:59+05:00",
                "max_capacity": 1000,
                "available_seats": 990,
                "price": 0,
            },
        )

        registration, reg_created = Registration.objects.get_or_create(
            attendee=user,
            event=event,
        )
        if reg_created or not registration.ticket_qr:
            generate_ticket_qr(registration)

        if reg_created:
            self.stdout.write(f"  Demo mehmon (QR tiket): {username} / mehmon12345")
        else:
            self.stdout.write(f"  Demo mehmon allaqachon mavjud: {username}")
