"""
Simulyatsiya: mehmonning expo bo'ylab harakat yo'lini aniqlash.

Haqiqiy kamera integratsiyasi bo'lmagan muhitda (demo rejim)
tizimning ishlashini to'liq ko'rsatish uchun ishlatiladi.
Hikvision LIVE rejim ulanganda bu funksiyalar o'rniga kameradan
kelgan real hodisalar (ona-tili: events) yoziladi.
"""

import hashlib

EXPO_ZONES = [
    "Kirish (Entrance)",
    "Asosiy zal (Hall A)",
    "Asosiy zal (Hall B)",
    "Texnologiyalar zonasi",
    "Startaplar zonasi",
    "B2B muzokaralar zonasi",
    "Media zona",
    "Ko'rgazma zali (Demo)",
]


def stable_seed(value):
    """Matndan deterministik butun son olish (SQLite uchun 32-bit)."""
    digest = int(hashlib.md5(str(value).encode("utf-8")).hexdigest(), 16)
    return digest % (2**31 - 1)


def build_visitor_path(visitor):
    """
    Mehmon uchun zonalar ketma-ketligini qaytaradi.

    Xuddi shu mehmon uchun har doim bir xil yo'l bo'ladi
    (deterministik), shunda demo ekranda izchil ko'rinadi.
    """
    seed = visitor.sim_seed
    n = 3 + (seed % 4)  # 3..6 zona
    path = []
    idx = seed
    for i in range(n):
        zone = EXPO_ZONES[idx % len(EXPO_ZONES)]
        idx += (seed % 5) + 1
        path.append(zone)
    # Mehmon oxirida chiqib ketadi
    return path
