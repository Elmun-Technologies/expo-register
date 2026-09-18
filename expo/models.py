import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Booth(models.Model):
    """
    Expo hududidagi stend (ko'rgazma joyi).

    Har bir stend egasi (ORGANIZER roli) o'z stendi oldiga
    kelgan mehmonlar statistikasini ko'ra oladi.
    """

    name = models.CharField(max_length=150)
    booth_number = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    zone = models.CharField(max_length=100, blank=True, help_text="Hudud / zal nomi")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booths",
        help_text="Stend egasi (ORGANIZER)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["booth_number"]

    def __str__(self):
        return f"{self.booth_number} — {self.name}"


class Camera(models.Model):
    """
    Hikvision kuzatuv kamerasi.

    ``mode`` = SIMULATION bo'lsa, haqiqiy qurilmaga ulanmaydi va
    tizim virtual "kadr"lar bilan ishlaydi (demo rejim).
    ``mode`` = LIVE bo'lsa, Hikvision ISAPI / RTSP orqali ulanadi.
    """

    class Mode(models.TextChoices):
        SIMULATION = "SIMULATION", "Simulation (demo)"
        LIVE = "LIVE", "Live (Hikvision ISAPI/RTSP)"

    name = models.CharField(max_length=150)
    zone = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.SIMULATION)
    is_enabled = models.BooleanField(default=True)

    # Hikvision ulanish ma'lumotlari (LIVE rejim uchun)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    port = models.PositiveIntegerField(default=80)
    username = models.CharField(max_length=100, blank=True)
    password = models.CharField(max_length=200, blank=True)
    rtsp_url = models.URLField(blank=True, help_text="rtsp://user:pass@ip:554/Streaming/...")

    # RTSP asosidagi live oqim uchun kanal
    channel = models.PositiveIntegerField(default=1, help_text="Hikvision kanal raqami")
    substream = models.PositiveIntegerField(default=1, help_text="1 = asosiy, 2 = sub-stream")

    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["zone", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_mode_display()})"

    @property
    def stream_url(self):
        """Brauzer uchun oqim manzili (LIVE rejimda RTSP -> HLS proxy kerak)."""
        if self.mode == self.Mode.LIVE and self.rtsp_url:
            return self.rtsp_url
        return ""


class ExpoVisitor(models.Model):
    """
    Kiosk orqali ro'yxatdan o'tgan mehmon.

    Ro'yxatdan o'tishi bilan kuzatuv tizimi ishga tushadi va
    monitoring paneliga xabar yuboriladi.
    """

    class Purpose(models.TextChoices):
        BUSINESS = "BUSINESS", "Business"
        PARTNERSHIP = "PARTNERSHIP", "Partnership"
        INVESTOR = "INVESTOR", "Investor"
        MEDIA = "MEDIA", "Media"
        STUDENT = "STUDENT", "Student"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active (inside)"
        LEFT = "LEFT", "Left"

    class VisitType(models.TextChoices):
        VISITOR = "VISITOR", "Mehmon (Guest)"
        EXHIBITOR = "EXHIBITOR", "Eksponent (Exhibitor)"

    class Source(models.TextChoices):
        KIOSK = "KIOSK", "Kiosk terminal"
        GATE_QR = "GATE_QR", "Darvoza — QR ticket"
        GATE_WALKIN = "GATE_WALKIN", "Darvoza — joyida ro'yxat"
        OFFLINE = "OFFLINE", "Offline navbat (sinxronlandi)"

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    company = models.CharField(max_length=150, blank=True)
    visit_type = models.CharField(max_length=20, choices=VisitType.choices, default=VisitType.VISITOR)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.KIOSK)

    # Mijoz qurilmasida yaratilgan unikal ID — offline navbat takror
    # sinxronlanmasligi uchun (idempotentlik).
    offline_id = models.UUIDField(null=True, blank=True, unique=True, editable=False)

    # Bot orqali ro'yxatdan o'tgan bo'lsa, shu ro'yxatga bog'lanadi.
    registration = models.OneToOneField(
        "registrations.Registration",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expo_visitor",
    )
    purpose = models.CharField(max_length=30, choices=Purpose.choices, default=Purpose.BUSINESS)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    photo = models.ImageField(upload_to="expo/visitors/", blank=True, null=True)

    # Yuz izi — dublikat nazorati uchun (suratdan hisoblanadi)
    face_hash = models.CharField(max_length=32, blank=True, editable=False)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    check_in_at = models.DateTimeField(default=timezone.now)
    check_out_at = models.DateTimeField(null=True, blank=True)

    badge_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Simulyatsiya uchun deterministik yo'l
    sim_seed = models.IntegerField(default=0, editable=False)
    planned_path = models.JSONField(default=list, blank=True, editable=False)
    current_zone = models.CharField(max_length=150, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expo_checkins",
    )

    class Meta:
        ordering = ["-check_in_at"]
        indexes = [
            models.Index(fields=["status", "check_in_at"]),
            models.Index(fields=["last_name", "first_name"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def minutes_inside(self):
        end = self.check_out_at or timezone.now()
        return max(0, int((end - self.check_in_at).total_seconds() // 60))

    def get_absolute_url(self):
        return reverse("expo_visitor_detail", args=[self.pk])


class TrackingEvent(models.Model):
    """
    Kuzatuv hodisasi: mehmon qayerda, qaysi kamerada ko'rindi,
    qaysi stendga kirdi / chiqdi.
    """

    class Kind(models.TextChoices):
        REGISTERED = "REGISTERED", "Registered"
        SEEN = "SEEN", "Seen by camera"
        ENTERED = "ENTERED", "Entered zone"
        EXITED = "EXITED", "Exited zone"
        LEFT = "LEFT", "Left expo"

    visitor = models.ForeignKey(ExpoVisitor, on_delete=models.CASCADE, related_name="tracking_events")
    camera = models.ForeignKey(Camera, on_delete=models.SET_NULL, null=True, blank=True, related_name="tracking_events")
    booth = models.ForeignKey(Booth, on_delete=models.SET_NULL, null=True, blank=True, related_name="tracking_events")
    zone = models.CharField(max_length=150, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.SEEN)
    detected_at = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["detected_at"]
        indexes = [
            models.Index(fields=["visitor", "detected_at"]),
            models.Index(fields=["booth", "kind"]),
            models.Index(fields=["camera", "detected_at"]),
        ]

    def __str__(self):
        return f"{self.visitor.full_name} — {self.get_kind_display()} @ {self.zone}"


class VisitAlert(models.Model):
    """
    Monitoring paneli uchun xabar (ogohlantirish).

    Yangi mehmon ro'yxatdan o'tganda, kuzatuv boshlanganda va
    mehmon chiqib ketganda yoziladi.
    """

    class Level(models.TextChoices):
        INFO = "INFO", "Info"
        SUCCESS = "SUCCESS", "Success"
        WARNING = "WARNING", "Warning"

    visitor = models.ForeignKey(ExpoVisitor, on_delete=models.CASCADE, related_name="alerts")
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INFO)
    message = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.message}"
