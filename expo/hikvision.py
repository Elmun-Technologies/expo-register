"""
Hikvision integratsiya qatlami (ISAPI / RTSP).

Hozircha tizim SIMULATION rejimda ishlaydi (haqiqiy kamerasiz).
Bu modul Hikvision kameralarini LIVE rejimga o'tkazish uchun
tayyor adapter vazifasini bajaradi.

ISAPI misollari:
    - Camera snapshot: http://<ip>/ISAPI/Streaming/channels/<ch>/picture
    - PTZ (preset):    PUT http://<ip>/ISAPI/PTZCtrl/channels/<ch>/presets/<id>/goto
    - DeviceInfo:      GET  http://<ip>/ISAPI/System/deviceInfo
    - Login (auth):    HTTP Digest (username/password)

SIMULATION rejimda haqiqiy tarmoqqa chiqilmaydi — demo (virtual) kadr
qaytariladi. LIVE rejimda esa qurilmaga ulanishning ikkala usuli ham
qo'llab-quvvatlanadi: Basic (eski qurilmalar) va Digest (standart).
"""

import base64
import hashlib
import logging
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


class HikvisionError(Exception):
    """Hikvision qurilmasi bilan ishlashdagi xatolik."""


def _basic_auth_header(username, password):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _build_opener(camera):
    """
    Kamera uchun urllib opener: Basic yoki Digest auth.

    Hikvision qurilmalari standart bo'yicha Digest talab qiladi,
    lekin ba'zi eski modellar Basic'ni ham qabul qiladi.
    """
    handlers = []
    if camera.username:
        # Avval Basic sarlavhani ishlatamiz; 401 kelsa Digest'ga qaytamiz
        # (o'qish davomida HTTPDigestAuthHandler sinab ko'riladi).
        pass
    return urllib.request.build_opener()


def _request(camera, path, method="GET", body=None, timeout=6, use_digest=True):
    """
    Kameraga ISAPI so'rov yuborish. Basic'ga qaytib, kerak bo'lsa Digest.
    Avtomatik 401 → Digest takrorlash.
    """
    base = f"http://{camera.ip_address}:{camera.port}"
    url = base + path
    req = urllib.request.Request(url, method=method, data=body)

    if camera.username:
        req.headers.update(_basic_auth_header(camera.username, camera.password))

    # Birinchi urinish: Basic
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), resp.status
    except urllib.error.HTTPError as exc:
        if exc.code == 401 and camera.username and use_digest:
            # Digest: ikki bosqichli
            return _request_digest(camera, path, method, body, timeout)
        raise HikvisionError(f"ISAPI {method} {path} xatosi: HTTP {exc.code}") from exc
    except Exception as exc:  # noqa: BLE001
        raise HikvisionError(f"Kameraga bog'lanib bo'lmadi ({path}): {exc}") from exc


def _request_digest(camera, path, method="GET", body=None, timeout=6):
    """
    Soddalashtirilgan Digest auth amalga oshiruvi (RFC 2617).

    Hikvision ISAPI: 401 javobda ``WWW-Authenticate: Digest realm=...``
    sarlavhasi qaytadi. Shundan so'ng hisob-kitob qilib takror so'rov.
    """
    base = f"http://{camera.ip_address}:{camera.port}"
    url = base + path

    # 1) Dastlabki so'rov — 401 va nonce olish
    probe = urllib.request.Request(url, method=method, data=body)
    try:
        resp = urllib.request.urlopen(probe, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise HikvisionError(f"Digest kutilgan 401 emas: {exc.code}") from exc
        auth_header = exc.headers.get("WWW-Authenticate", "")
        params = _parse_digest_challenge(auth_header)
        if not params:
            return None
        # 2) Authorization sarlavhasini hisoblash
        authorization = _digest_authorization(
            camera.username, camera.password, method, path, params
        )
        req2 = urllib.request.Request(url, method=method, data=body)
        req2.add_header("Authorization", authorization)
        with urllib.request.urlopen(req2, timeout=timeout) as resp2:
            return resp2.read(), resp2.status
    return resp.read(), resp.status


def _parse_digest_challenge(header):
    """WWW-Authenticate sarlavhasidan realm/nonce/opaque/qop olish."""
    if not header.lower().startswith("digest"):
        return {}
    params = {}
    h = header[len("digest"):]
    # realm="x", nonce="y", ...
    import re

    for key in ("realm", "nonce", "opaque", "qop", "algorithm"):
        m = re.search(key + r'\s*=\s*"?([^",\s]+)"?', h, re.IGNORECASE)
        if m:
            params[key] = m.group(1)
    return params


def _digest_authorization(username, password, method, path, params):
    """RFC 2617 Digest ``Authorization`` sarlavhasini hisoblash."""
    realm = params.get("realm", "")
    nonce = params.get("nonce", "")
    opaque = params.get("opaque", "")
    qop = params.get("qop")
    algorithm = params.get("algorithm", "MD5").upper()

    ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
    ha2 = hashlib.md5(f"{method}:{path}".encode()).hexdigest()

    if qop:
        nc = "00000001"
        cnonce = "ExpoCtrl01"
        response = hashlib.md5(
            f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()
        ).hexdigest()
        parts = (
            f'username="{username}", realm="{realm}", nonce="{nonce}", '
            f'uri="{path}", response="{response}", algorithm={algorithm}, '
            f'qop={qop}, nc={nc}, cnonce="{cnonce}"'
        )
    else:
        response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
        parts = (
            f'username="{username}", realm="{realm}", nonce="{nonce}", '
            f'uri="{path}", response="{response}", algorithm={algorithm}'
        )

    if opaque:
        parts += f', opaque="{opaque}"'
    return "Digest " + parts


def goto_camera(camera, channel=None):
    """
    Kamerani "faollashtirish" — mehmon kuzatuvini boshlashda chaqiriladi.

    SIMULATION rejimda holat belgilanadi; LIVE rejimda PTZ preset 1 ga
    (kirish nuqtasi) buriladi.
    """
    if camera.mode == camera.Mode.SIMULATION:
        return {"ok": True, "mode": "simulation", "camera": camera.name}

    if not camera.ip_address:
        raise HikvisionError("Kamerada IP manzil belgilanmagan.")

    ch = channel or camera.channel
    path = f"/ISAPI/PTZCtrl/channels/{ch}/presets/1/goto"
    _, status = _request(camera, path, method="PUT")
    return {"ok": True, "mode": "live", "camera": camera.name, "status": status}


def goto_preset(camera, preset_id=1, channel=None):
    """PTZ kamerani aniq preset nuqtasiga burish."""
    if camera.mode == camera.Mode.SIMULATION:
        return {"ok": True, "mode": "simulation", "preset": preset_id}
    ch = channel or camera.channel
    path = f"/ISAPI/PTZCtrl/channels/{ch}/presets/{preset_id}/goto"
    _, status = _request(camera, path, method="PUT")
    return {"ok": True, "mode": "live", "preset": preset_id, "status": status}


def capture_snapshot(camera, channel=None):
    """Kamera kadrini olish (JPEG bytes). SIMULATION'da None."""
    if camera.mode == camera.Mode.SIMULATION:
        return None
    ch = channel or camera.channel
    path = f"/ISAPI/Streaming/channels/{ch}/picture"
    data, _ = _request(camera, path, method="GET")
    return data


def camera_device_info(camera):
    """Kamera ishchi (onlayn) ekanini tekshirish."""
    if camera.mode == camera.Mode.SIMULATION:
        return {"simulation": True}
    path = "/ISAPI/System/deviceInfo"
    data, _ = _request(camera, path, method="GET")
    return {"simulation": False, "raw_len": len(data)}


def stream_url(camera, channel=None):
    """RTSP stream manzili (VLC/HLS uchun)."""
    if camera.mode == camera.Mode.SIMULATION:
        return ""
    if camera.rtsp_url:
        return camera.rtsp_url
    ch = channel or camera.channel
    stream = camera.substream or 1
    return (
        f"rtsp://{camera.username}:{camera.password}@"
        f"{camera.ip_address}:554/Streaming/Channels/{ch}{stream:02d}"
    )
