from django.contrib.auth import get_user_model
from django.test import TestCase

from . import face, services, simulation
from .models import Booth, Camera, ExpoVisitor, TrackingEvent, VisitAlert

User = get_user_model()


class FaceAndDuplicateTests(TestCase):
    """Yuzni aniqlash va dublikat nazorati."""

    def setUp(self):
        Camera.objects.create(name="Kamera 1", zone="Kirish (Entrance)")
        Booth.objects.create(booth_number="A01", name="Test Stend", zone="Asosiy zal (Hall A)")

    def test_cascade_loads_and_detects_no_face_on_blank(self):
        # Haarcascade yuklanadi va bo'sh rasmda yuz topilmaydi
        import cv2
        import numpy as np
        import tempfile

        c = face._get_cascade()
        self.assertFalse(c.empty())

        f = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        cv2.imwrite(f.name, np.zeros((120, 120, 3), dtype=np.uint8))
        try:
            self.assertEqual(face.detect_faces(f.name), [])
        finally:
            import os
            os.unlink(f.name)

    def test_find_duplicate_by_name(self):
        ExpoVisitor.objects.create(
            first_name="Aziz",
            last_name="Karimov",
            purpose=ExpoVisitor.Purpose.BUSINESS,
        )
        dup = ExpoVisitor(
            first_name="Aziz",
            last_name="Karimov",
            purpose=ExpoVisitor.Purpose.BUSINESS,
        )
        found, reason = face.find_duplicate(dup)
        self.assertIsNotNone(found)
        self.assertEqual(reason, "name")

    def test_no_duplicate_for_distinct_name(self):
        ExpoVisitor.objects.create(
            first_name="Aziz",
            last_name="Karimov",
            purpose=ExpoVisitor.Purpose.BUSINESS,
        )
        other = ExpoVisitor(
            first_name="Nodir",
            last_name="Toshev",
            purpose=ExpoVisitor.Purpose.BUSINESS,
        )
        found, _ = face.find_duplicate(other)
        self.assertIsNone(found)

    def test_kiosk_rejects_duplicate_visitor(self):
        resp = self.client.post(
            "/expo/kiosk/",
            {
                "first_name": "Aziz",
                "last_name": "Karimov",
                "company": "",
                "purpose": "BUSINESS",
                "phone": "",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            ExpoVisitor.objects.filter(first_name="Aziz").count(), 1
        )

        # Xuddi shu ism bilan qayta urinish — dublikat
        resp2 = self.client.post(
            "/expo/kiosk/",
            {
                "first_name": "Aziz",
                "last_name": "Karimov",
                "company": "",
                "purpose": "BUSINESS",
                "phone": "",
            },
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertIn("Allaqachon", resp2.content.decode())
        self.assertEqual(
            ExpoVisitor.objects.filter(first_name="Aziz").count(), 1
        )


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


class GateScanTests(TestCase):
    """Darvoza (gate) — QR skaner va offline navbat oqimi."""

    def setUp(self):
        self.security = User.objects.create_user(
            username="sec1",
            password="pass12345",
            role=User.Role.SECURITY,
        )
        Camera.objects.create(name="Kamera 1", zone="Kirish (Entrance)")
        Booth.objects.create(booth_number="A01", name="Test Stend", zone="Asosiy zal (Hall A)")

    def test_gate_page_requires_monitor_role(self):
        resp = self.client.get("/expo/gate/")
        self.assertEqual(resp.status_code, 302)  # login talab
        self.client.force_login(self.security)
        resp = self.client.get("/expo/gate/")
        self.assertEqual(resp.status_code, 200)

    def test_gate_walkin_creates_visitor_and_tracking(self):
        self.client.force_login(self.security)
        resp = self.client.post(
            "/expo/gate/api/",
            data={
                "first_name": "Dilnoza",
                "last_name": "Karimova",
                "company": "Payme",
                "purpose": "INVESTOR",
                "visit_type": "EXHIBITOR",
            },
            content_type="application/json",
        )
        data = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "ok")

        visitor = ExpoVisitor.objects.get(pk=data["visitor_id"])
        self.assertEqual(visitor.full_name, "Dilnoza Karimova")
        self.assertEqual(visitor.visit_type, ExpoVisitor.VisitType.EXHIBITOR)
        self.assertEqual(visitor.source, ExpoVisitor.Source.GATE_WALKIN)
        self.assertTrue(visitor.tracking_events.exists())
        self.assertTrue(visitor.alerts.exists())

    def test_gate_walkin_requires_names(self):
        self.client.force_login(self.security)
        resp = self.client.post(
            "/expo/gate/api/",
            data={"first_name": "", "last_name": ""},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["success"])

    def test_gate_offline_batch_idempotent(self):
        self.client.force_login(self.security)
        import uuid
        oid = str(uuid.uuid4())
        batch = [
            {"offline_id": oid, "first_name": "Behruz", "last_name": "Olimov"},
        ]
        resp = self.client.post(
            "/expo/gate/api/",
            data=batch,
            content_type="application/json",
        )
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["results"][0]["status"], "ok")
        self.assertEqual(data["results"][0]["created"], True)

        # Xuddi shu offline_id qayta yuborilsa — yangi yozuv yaratilmaydi
        resp2 = self.client.post(
            "/expo/gate/api/",
            data=batch,
            content_type="application/json",
        )
        data2 = resp2.json()
        self.assertEqual(data2["results"][0]["created"], False)
        self.assertEqual(
            ExpoVisitor.objects.filter(offline_id=oid).count(), 1
        )

    def test_gate_qr_creates_visitor_from_registration(self):
        from events.models import Event
        from registrations.models import Registration
        from registrations.utils import generate_ticket_qr
        import json

        attendee = User.objects.create_user(
            username="mehmon_test",
            password="x",
            first_name="Akmal",
            last_name="Rahimov",
            role=User.Role.ATTENDEE,
        )
        from django.utils import timezone
        from events.models import EventCategory

        category = EventCategory.objects.get_or_create(
            name="Expo", defaults=dict(slug="expo")
        )[0]

        organizer = User.objects.create_user(
            username="org_test",
            password="x",
            role=User.Role.ORGANIZER,
        )

        event = Event.objects.get_or_create(
            title="Test Expo",
            defaults=dict(
                slug="test-expo",
                status="PUBLISHED",
                venue="Toshkent",
                description="test",
                category=category,
                organizer=organizer,
                event_date="2026-10-01",
                start_time="10:00:00",
                end_time="18:00:00",
                registration_deadline=timezone.now() + timezone.timedelta(days=5),
                max_capacity=100,
                available_seats=100,
                price=0,
            ),
        )[0]
        registration = Registration.objects.create(attendee=attendee, event=event)
        generate_ticket_qr(registration)

        self.client.force_login(self.security)
        qr_text = f"Ticket ID:\n{registration.ticket_code}\n"
        resp = self.client.post(
            "/expo/gate/api/",
            data=json.dumps({"qr_text": qr_text}),
            content_type="application/json",
        )
        data = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data["success"])
        visitor = ExpoVisitor.objects.get(pk=data["visitor_id"])
        self.assertEqual(visitor.full_name, "Akmal Rahimov")
        self.assertEqual(visitor.source, ExpoVisitor.Source.GATE_QR)
        self.assertEqual(visitor.registration_id, registration.id)

        # Qayta skanerlash — already
        resp2 = self.client.post(
            "/expo/gate/api/",
            data=json.dumps({"qr_text": qr_text}),
            content_type="application/json",
        )
        self.assertEqual(resp2.json()["status"], "already")


class TelegramBotTests(TestCase):
    """Telegram bot — ro'yxat oqimi va QR generatsiyasi."""

    def setUp(self):
        Camera.objects.create(name="Kamera 1", zone="Kirish (Entrance)")

    def test_default_event_and_organizer(self):
        from expo import telegram_bot as tb

        event = tb._default_event_sync()
        self.assertIsNotNone(event)
        self.assertEqual(event.status, "PUBLISHED")
        self.assertIsNotNone(event.organizer)

    def test_get_or_create_profile(self):
        from expo import telegram_bot as tb
        from expo.models import TelegramProfile

        profile = tb._get_or_create_profile_sync(123456789, "mehmon", "Aziz", "Karimov")
        self.assertEqual(profile.telegram_id, 123456789)
        self.assertEqual(TelegramProfile.objects.filter(telegram_id=123456789).count(), 1)

        # Qayta chaqirilsa yangi yaratilmaydi
        tb._get_or_create_profile_sync(123456789, "mehmon", "Aziz", "Karimov")
        self.assertEqual(TelegramProfile.objects.filter(telegram_id=123456789).count(), 1)

    def test_finish_registration_sync(self):
        from expo import telegram_bot as tb
        from django.contrib.auth import get_user_model
        from expo.models import TelegramProfile

        User = get_user_model()
        result = tb._finish_registration_sync(
            777001,
            "botuser",
            "Tele",
            "Gram",
            {"first_name": "Karim", "last_name": "Navruzov",
             "company": "GreenTech", "purpose": "BUSINESS"},
            phone="998901234567",
        )
        profile, registration, event, fname, lname, company, purpose = result
        self.assertEqual(fname, "Karim")
        self.assertEqual(lname, "Navruzov")
        self.assertEqual(company, "GreenTech")
        self.assertIsNotNone(registration.ticket_qr)
        self.assertEqual(registration.attendee.username, "tg777001")
        self.assertEqual(
            TelegramProfile.objects.get(telegram_id=777001).state, "DONE"
        )

    def test_build_qr_png_contains_ascii(self):
        from expo import telegram_bot as tb
        from events.models import Event
        from django.contrib.auth import get_user_model
        from registrations.models import Registration

        User = get_user_model()
        event = tb._default_event_sync()
        user = User.objects.create_user(
            username="tg_test_qr", first_name="Q", last_name="T", role="ATTENDEE"
        )
        reg = Registration.objects.create(attendee=user, event=event)
        buf = tb.build_qr_png(reg)
        data = buf.getvalue()
        self.assertTrue(data.startswith(b"\x89PNG"))
        self.assertGreater(len(data), 500)

    def test_build_application_requires_token(self):
        from expo import telegram_bot as tb

        with self.assertRaises(RuntimeError):
            tb.build_application(token="")


class HikvisionTests(TestCase):
    """Hikvision adapter — Digest auth va ish rejimlari."""

    def test_digest_challenge_parse(self):
        from expo import hikvision

        header = 'Digest realm="hikvision", nonce="abc123", qop="auth", opaque="xyz"'
        params = hikvision._parse_digest_challenge(header)
        self.assertEqual(params["realm"], "hikvision")
        self.assertEqual(params["nonce"], "abc123")
        self.assertEqual(params["qop"], "auth")
        self.assertEqual(params["opaque"], "xyz")

    def test_digest_authorization(self):
        from expo import hikvision

        params = {"realm": "hikvision", "nonce": "abc123", "qop": "auth", "opaque": "xyz"}
        auth = hikvision._digest_authorization("admin", "pass123", "GET", "/ISAPI/System/deviceInfo", params)
        self.assertTrue(auth.startswith("Digest "))
        self.assertIn("username=\"admin\"", auth)
        self.assertIn("response=\"", auth)

    def test_goto_camera_simulation(self):
        from expo import hikvision

        cam = Camera.objects.create(name="Sim Kamera", zone="Kirish (Entrance)", mode=Camera.Mode.SIMULATION)
        result = hikvision.goto_camera(cam)
        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "simulation")

    def test_snapshot_simulation_returns_none(self):
        from expo import hikvision

        cam = Camera.objects.create(name="Sim Kamera 2", zone="Hall A", mode=Camera.Mode.SIMULATION)
        self.assertIsNone(hikvision.capture_snapshot(cam))

    def test_stream_url(self):
        from expo import hikvision

        cam = Camera.objects.create(
            name="Live Kamera", zone="Hall B", mode=Camera.Mode.LIVE,
            ip_address="192.168.1.10", username="admin", password="pass",
            channel=2, substream=1,
        )
        url = hikvision.stream_url(cam)
        self.assertTrue(url.startswith("rtsp://admin:pass@192.168.1.10:554/Streaming/Channels/"))

    def test_snapshot_view_requires_monitor(self):
        Camera.objects.create(name="K1", zone="Kirish (Entrance)")
        # Anonim — redirect
        self.assertEqual(self.client.get("/expo/devices/camera/1/snapshot/").status_code, 302)
