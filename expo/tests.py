from django.contrib.auth import get_user_model
from django.test import TestCase

from . import services, simulation
from .models import Booth, Camera, ExpoVisitor, TrackingEvent, VisitAlert

User = get_user_model()


class KioskFlowTests(TestCase):
    """Mehmon ro'yxatdan o'tishi -> kuzatuv boshlandi oqimi."""

    def setUp(self):
        Camera.objects.create(name="Kamera 1", zone="Kirish (Entrance)")
        Booth.objects.create(booth_number="A01", name="Test Stend", zone="Asosiy zal (Hall A)")

    def test_kiosk_checkin_creates_visitor_and_starts_tracking(self):
        resp = self.client.post(
            "/expo/kiosk/",
            {
                "first_name": "Aziz",
                "last_name": "Karimov",
                "company": "UzAuto",
                "purpose": "BUSINESS",
                "phone": "",
            },
        )
        self.assertEqual(resp.status_code, 200)
        visitor = ExpoVisitor.objects.get(first_name="Aziz", last_name="Karimov")
        self.assertTrue(visitor.planned_path)
        self.assertEqual(visitor.status, ExpoVisitor.Status.ACTIVE)

        # Xabar yozildi — monitoring paneli uchun
        self.assertTrue(
            VisitAlert.objects.filter(visitor=visitor, level="SUCCESS").exists()
        )
        # Kuzatuv boshlandi
        self.assertTrue(visitor.tracking_events.filter(kind=TrackingEvent.Kind.SEEN).exists())

    def test_missing_required_name_rejected(self):
        resp = self.client.post(
            "/expo/kiosk/",
            {"first_name": "", "last_name": "", "company": "", "purpose": "BUSINESS"},
        )
        self.assertEqual(ExpoVisitor.objects.count(), 0)

    def test_advance_tracking_moves_through_zones_and_checks_out(self):
        visitor = ExpoVisitor.objects.create(
            first_name="Dilnoza", last_name="Rahimova",
            sim_seed=simulation.stable_seed("seed"), planned_path=["Zona A", "Zona B"],
        )
        services.start_tracking(visitor)

        for _ in range(10):
            zone = services.advance_tracking(visitor)

        self.assertEqual(visitor.status, ExpoVisitor.Status.LEFT)
        self.assertTrue(
            visitor.tracking_events.filter(kind=TrackingEvent.Kind.LEFT).exists()
        )


class BoothAnalyticsTests(TestCase):
    def setUp(self):
        booth = Booth.objects.create(booth_number="A01", name="Stend", zone="Zona A")
        visitor = ExpoVisitor.objects.create(
            first_name="Botir", last_name="Ergashev",
            sim_seed=1, planned_path=["Zona A", "Zona B"],
        )
        TrackingEvent.objects.create(visitor=visitor, booth=booth, zone="Zona A", kind=TrackingEvent.Kind.ENTERED)
        TrackingEvent.objects.create(visitor=visitor, booth=booth, zone="Zona A", kind=TrackingEvent.Kind.ENTERED)

    def test_booth_summary_counts_visitors_and_visits(self):
        from . import analytics
        booth = Booth.objects.get(booth_number="A01")
        summary = analytics.booth_summary(booth)
        self.assertEqual(summary["unique_visitors"], 1)
        self.assertEqual(summary["visits"], 2)


class PermissionsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin", password="pass")
        self.organizer = User.objects.create_user(
            username="organizer",
            password="pass",
            role=User.Role.ORGANIZER,
        )

    def test_monitor_requires_staff(self):
        self.client.login(username="organizer", password="pass")
        resp = self.client.get("/expo/monitor/")
        self.assertEqual(resp.status_code, 302)  # redirect

        self.client.login(username="admin", password="pass")
        resp = self.client.get("/expo/monitor/")
        self.assertEqual(resp.status_code, 200)
