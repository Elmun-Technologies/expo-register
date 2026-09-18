"""
Hikvision integratsiya qatlami (ISAPI / RTSP).

Hozircha tizim SIMULATION rejimda ishlaydi (haqiqiy kamerasiz).
Bu modul Hikvision kameralarini LIVE rejimga o'tkazish uchun
tayyor adapter vazifasini bajaradi.

ISAPI misollari:
    - Camera snapshot: http://<ip>/ISAPI/Streaming/channels/<ch>/picture
    - PTZ (preset):    PUT http://<ip>/ISAPI/PTZCtrl/channels/<ch>/presets/<id>/goto
    - Login (auth):    HTTP Digest (username/password)

Haqiqiy qurilmalarni ulaganda:
1. Camera.mode = LIVE va ip_address / username / password to'ldiriladi.
2. ``hikvision.goto_preset()`` yoki ``capture_snapshot()`` chaqirilib,
   xavfsizlik xodimiga jonli kadr ko'rsatiladi.
"""

import base64
import logging
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


class HikvisionError(Exception):
    """Hikvision qurilmasi bilan ishlashdagi xatolik."""


def _digest_auth_header(username, password):
    """
    ISAPI ko'pincha Digest auth talab qiladi. Bu yerda asosiy
    (Basic) sarlavha tayyorlab qo'yiladi — prodda kerakli
    autentifikatsiya turiga moslab kengaytiriladi.
    """
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def goto_camera(camera, channel=None):
    """
    Xavfsizlik xodimi qaysi kamerani ishga tushirishni so'rasa,
    ushbu funksiya o'sha kamerani "faollashtiradi".

    SIMULATION rejimda faqat holatni belgilab qo'yadi; LIVE rejimda
    qurilmaga so'rov yuboradi.
    """
    if camera.mode == camera.Mode.SIMULATION:
        return {"ok": True, "mode": "simulation", "camera": camera.name}

    if not camera.ip_address:
        raise HikvisionError("Kamerada IP manzil belgilanmagan.")

    url = (
        f"http://{camera.ip_address}:{camera.port}"
        f"/ISAPI/PTZCtrl/channels/{channel or camera.channel}"
        f"/presets/1/goto"
    )
    req = urllib.request.Request(url, method="PUT")
    req.headers.update(_digest_auth_header(camera.username, camera.password))
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return {"ok": True, "mode": "live", "camera": camera.name, "status": resp.status}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Hikvision ISAPI xatosi: %r", exc)
        raise HikvisionError("Kameraga bog'lanib bo'lmadi.") from exc


def capture_snapshot(camera, channel=None):
    """Kamera kadrini olish (snapshot URL)."""
    if camera.mode == camera.Mode.SIMULATION:
        return None
    ch = channel or camera.channel
    return (
        f"http://{camera.ip_address}:{camera.port}"
        f"/ISAPI/Streaming/channels/{ch}/picture"
    )
