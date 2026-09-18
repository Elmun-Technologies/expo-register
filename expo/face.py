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


def detect_faces_array(img):
    """NumPy (BGR) tasvirdan yuzlarni topish."""
    if img is None:
        return []
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = _get_cascade().detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40),
    )
    return [tuple(int(v) for v in f) for f in faces]


def _gray_face_region(img, face_rect, size=(100, 100)):
    """Yuz hududini kulrang, o'lchamlari normalangan massivga aylantirish."""
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    x, y, w, h = face_rect
    face = gray[y:y + h, x:x + w]
    if face.size == 0:
        return None
    return cv2.resize(face, size, interpolation=cv2.INTER_AREA)


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


# ==========================================================
# TANIYDI QATLAMI — OpenCV LBPH face recognizer
# ==========================================================
#
# endi kuzatuv kamerasi kadridan yuz olinib, u yuz qaysi mehmon
# ekanini "tanib" qaytaradi. Model barcha mehmonlarning ro'yxatdagi
# suratlaridan o'qitiladi (train_recognizer), keyin yangi kadrdan
# predict_face ile taniladi.
#
# LBPH — kam resurs sarflaydigan klassik usul; sandbox'da ishlaydi.
# Katta tadbir uchun FaceNet/Iris.ai bilan almashtirish mumkin (o'zi
# qatlam interfeysi birxil qoladi).


def _recognizer_available():
    """cv2.face (contrib) mavjudligini tekshirish."""
    return hasattr(cv2, "face") and hasattr(cv2.face, "LBPHFaceRecognizer_create")


def train_recognizer(visitors=None):
    """
    Barcha (yoki berilgan) mehmonlarning suratlaridan LBPH model
    o'qitish. Suratsiz mehmonlar o'tkazib yuboriladi.

    Qaytaradi: (recognizer, id_to_visitor_dict, trained_count)
    Bunda id_to_visitor_dict: LBPH ichki ID -> visitor.pk
    """
    if not _recognizer_available():
        raise RuntimeError("cv2.face mavjud emas (opencv-contrib kerak).")

    from .models import ExpoVisitor as _Visitor

    query = visitors if visitors is not None else _Visitor.objects.all()
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    mapping = {}
    features = []
    labels = []
    nid = 0

    for visitor in query:
        if not visitor.photo:
            continue
        try:
            rects = detect_faces(visitor.photo.path)
        except Exception:
            rects = []
        if not rects:
            continue
        img = cv2.imread(visitor.photo.path)
        region = _gray_face_region(img, rects[0])
        if region is None:
            continue
        features.append(region)
        labels.append(nid)
        mapping[nid] = visitor.pk
        nid += 1

    if not features:
        return None, mapping, 0

    recognizer.train(features, np.array(labels, dtype=np.int32))
    return recognizer, mapping, nid


def predict_face(recognizer, mapping, image_path, min_confidence=60.0):
    """
    Suratdagi (kamera kadridagi) yuzni tanib, qaysi mehmonga tegishli
    ekanini qaytaradi.

    Qaytaradi: (visitor_pk yoki None, confidence yoki None)
    confidence LBPH da qancha kichik bo'lsa — shuncha o'xshash;
    min_confidence dan katta bo'lsa — "tanilmay qolgani".
    """
    if recognizer is None or not mapping:
        return None, None
    rects = detect_faces(image_path)
    if not rects:
        return None, None
    img = cv2.imread(str(image_path))
    region = _gray_face_region(img, rects[0])
    if region is None:
        return None, None

    label, confidence = recognizer.predict(region)
    if confidence > min_confidence:
        return None, confidence
    visitor_pk = mapping.get(int(label))
    return visitor_pk, confidence


def predict_face_array(recognizer, mapping, img_array, min_confidence=60.0):
    """NumPy (BGR) kadrdan yuzni tanib olish (kamera oqimi uchun)."""
    if recognizer is None or not mapping:
        return None, None
    rects = detect_faces_array(img_array)
    if not rects:
        return None, None
    region = _gray_face_region(img_array, rects[0])
    if region is None:
        return None, None
    label, confidence = recognizer.predict(region)
    if confidence > min_confidence:
        return None, float(confidence)
    return mapping.get(int(label)), float(confidence)


def match_visitor(image_path, min_confidence=60.0):
    """
    Qulay o'rash: kamera kadri suratidan mehmonni tanib,
    (ExpoVisitor, confidence) qaytaradi.

    Hammasini birdaniga qiladi: model o'qitadi (barcha suratli
    mehmonlardan) → kadrni tanidi.
    """
    recognizer, mapping, trained = train_recognizer()
    if recognizer is None:
        return None, None
    visitor_pk, confidence = predict_face(recognizer, mapping, image_path, min_confidence)
    if visitor_pk is None:
        return None, confidence
    return ExpoVisitor.objects.filter(pk=visitor_pk).first(), confidence
