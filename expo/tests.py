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


class BadgeAndExportTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin", password="pass")
        self.visitor = ExpoVisitor.objects.create(
            first_name="Aziz", last_name="Karimov", company="UzAuto",
        )

    def test_badge_shows_qr_code(self):
        self.client.login(username="admin", password="pass")
        resp = self.client.get(f"/expo/visitors/{self.visitor.id}/badge/")
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("data:image/png;base64", content)  # QR kod bor

    def test_csv_export_downloads(self):
        self.client.login(username="admin", password="pass")
        resp = self.client.get("/expo/visitors/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Disposition"], 'attachment; filename="expo_visitors.csv"')
        content = resp.content.decode("utf-8")
        self.assertIn("Ism", content)  # sarlavha qatori
        self.assertIn("Aziz", content)  # mehmon ma'lumoti


class CameraAndPhotoTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin", password="pass")
        self.camera = Camera.objects.create(name="Kam 1", zone="Kirish")

    def test_camera_toggle_requires_admin(self):
        # anonim foydalanuvchi rad etiladi
        resp = self.client.get(f"/expo/devices/camera/{self.camera.id}/toggle/")
        self.assertEqual(resp.status_code, 302)

        self.client.login(username="admin", password="pass")
        before = self.camera.is_enabled
        resp = self.client.get(f"/expo/devices/camera/{self.camera.id}/toggle/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["is_enabled"], not before)

    def test_kiosk_accepts_photo_data(self):
        # kichik 1x1 PNG ni base64 qilib yuboramiz
        import base64
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )
        data_url = "data:image/png;base64," + base64.b64encode(png).decode()
        resp = self.client.post(
            "/expo/kiosk/",
            {
                "first_name": "Foto",
                "last_name": "Test",
                "company": "",
                "purpose": "BUSINESS",
                "phone": "",
                "photo_data": data_url,
            },
        )
        self.assertEqual(resp.status_code, 200)
        visitor = ExpoVisitor.objects.get(first_name="Foto")
        self.assertTrue(visitor.photo)  # surat saqlangan


class SearchAndPdfTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin", password="pass")
        Booth.objects.create(booth_number="A01", name="Test Stend", zone="Hall A")
        ExpoVisitor.objects.create(first_name="Sarvar", last_name="Aslonov", company="UzAuto")
        ExpoVisitor.objects.create(first_name="Malika", last_name="Azizova", company="Bank")

    def test_visitor_search_filters(self):
        self.client.login(username="admin", password="pass")
        resp = self.client.get("/expo/visitors/?search=Sarvar")
        content = resp.content.decode()
        self.assertIn("Sarvar", content)
        self.assertNotIn("Malika", content)

    def test_booth_pdf_downloads(self):
        self.client.login(username="admin", password="pass")
        resp = self.client.get("/expo/analytics/pdf/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertTrue(resp.content.startswith(b"%PDF"))

    def test_visitors_pdf_downloads(self):
        self.client.login(username="admin", password="pass")
        resp = self.client.get("/expo/visitors/pdf/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.content.startswith(b"%PDF"))
