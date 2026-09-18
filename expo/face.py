"""
Yuzni aniqlash (face detection) va dublikat nazorati.

- ``detect_faces``: mehmon suratidan yuzlarni topadi (OpenCV Haar cascade).
- ``face_hash``: yuz hududidan oddiy perceptual-hash o'xshash iz (hash)
  yaratadi. U bilan bir odamning ikkinchi marta ro'yxatdan o'tishini
  aniqlash mumkin.
- ``find_duplicate``: kiritilgan ism/familiya yoki yuz iziga o'xshash
  mavjud mehmonni qaytaradi.

Bu haqiqiy face-recognition (FaceNet/Dlib) emas, balki kam resurs
sarflaydigan birinchi qadam — sandbox'da to'liq ishlaydi va
keyinchalik chuqur model (FaceNet/Iris.ai) bilan almashtirilishi mumkin.
"""

import hashlib
import logging
from pathlib import Path

import cv2
import numpy as np
from django.db.models import Q

from .models import ExpoVisitor

logger = logging.getLogger(__name__)

CASCADE_PATH = Path(__file__).parent / "data" / "haarcascade_frontalface_default.xml"

_cascade = None


def _get_cascade():
    global _cascade
    if _cascade is None:
        _cascade = cv2.CascadeClassifier(str(CASCADE_PATH))
    return _cascade


def detect_faces(image_path):
    """
    Suratdan yuzlarni topish. Natija: yuzlar ro'yxati (x, y, w, h).
    """
    if not image_path or not Path(image_path).exists():
        return []
    img = cv2.imread(str(image_path))
    if img is None:
        return []
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = _get_cascade().detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40),
    )
    return [tuple(int(v) for v in f) for f in faces]


def face_hash(image_path):
    """
    Suratdagi birinchi yuzdan bitmap-logo o'xshash "hash" (64-simvolli
    hex) hisoblash. Ikki suratdagi bir odamning izi o'xshash bo'ladi.
    """
    faces = detect_faces(image_path)
    if not faces:
        return ""
    img = cv2.imread(str(image_path))
    if img is None:
        return ""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    x, y, w, h = faces[0]
    face = gray[y:y + h, x:x + w]
    face = cv2.resize(face, (16, 16), interpolation=cv2.INTER_AREA)
    avg = float(face.mean())
    bits = (face > avg).astype(np.uint8).flatten()
    # 256 bit -> 64 hex belgi
    return hashlib.sha1(bits.tobytes()).hexdigest()[:16]


def hamming(a, b):
    """Ikki hex o'xshashlik izi orasidagi farq (bitlarda)."""
    if not a or not b:
        return 999999
    try:
        x = int(a, 16)
        y = int(b, 16)
    except ValueError:
        return 999999
    return bin(x ^ y).count("1")


def normalize_name(value):
    return " ".join((value or "").strip().lower().split())


def find_duplicate(visitor, threshold=12):
    """
    Yangi mehmon uchun dublikat qidirish.

    Qaytaradi: (duplicate_visitor yoki None, reason)
    """
    # 1) Ism + familiya bir xil bo'lsa
    name = normalize_name(f"{visitor.first_name} {visitor.last_name}")
    if name:
        candidates = ExpoVisitor.objects.filter(
            Q(first_name__iexact=visitor.first_name)
            & Q(last_name__iexact=visitor.last_name)
        ).exclude(pk=visitor.pk)
        if candidates.exists():
            return candidates.first(), "name"

    # 2) Yuz izi o'xshash bo'lsa (suratlari bor mehmonlar orasida)
    if visitor.photo and visitor.photo.path:
        new_hash = visitor.face_hash or face_hash(visitor.photo.path)
        if new_hash:
            for other in ExpoVisitor.objects.exclude(pk=visitor.pk).exclude(photo=""):
                try:
                    other_hash = other.face_hash or face_hash(other.photo.path)
                except Exception:
                    continue
                if other_hash and hamming(new_hash, other_hash) <= threshold:
                    return other, "face"

    return None, None
