"""
Simulyatsiya: mehmonning expo bo'ylab harakat yo'lini aniqlash.

Haqiqiy kamera integratsiyasi bo'lmagan muhitda (demo rejim)
tizimning ishlashini to'liq ko'rsatish uchun ishlatiladi.
Hikvision LIVE rejim ulanganda bu funksiyalar o'rniga kameradan
kelgan real hodisalar (ona-tili: events) yoziladi.
"""

import hashlib
import time

from PIL import Image, ImageDraw

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


def demo_frame(seed, size=(640, 360)):
    """
    SIMULATION rejimdagi kamera uchun jonli ko'rinadigan virtual kadr.

    Har kameraga xos rang va vaqt bo'yicha o'zgaradigan "harakat"
    nuqtalari chiziladi — monitoring panelda kadrlar jonlidek ko'rinadi.
    """
    import math

    t = int(time.time())
    base_r = 20 + (seed % 60)
    base_g = 20 + ((seed // 7) % 60)
    base_b = 30 + ((seed // 13) % 60)

    img = Image.new("RGB", size, (18, 22, 34))
    d = ImageDraw.Draw(img)

    # Gradient fon
    for y in range(size[1]):
        k = y / size[1]
        d.line(
            [(0, y), (size[0], y)],
            fill=(int(18 + 30 * k), int(22 + 35 * k), int(34 + 40 * k)),
        )

    # Shiftli "skaner" chizig'i
    ypos = (t * 60) % (size[1] + 200) - 100
    d.rectangle([0, ypos, size[0], ypos + 3], fill=(base_r + 60, base_g + 60, base_b + 60))

    # Harakatlanuvchi nuqtalar (odamlarni ifodalaydi)
    for i in range(5):
        x = int(size[0] * (0.15 + 0.7 * ((math.sin(t * 0.7 + i * 2.1 + seed) + 1) / 2)))
        y = int(size[1] * (0.2 + 0.6 * ((math.cos(t * 0.5 + i * 1.7 + seed) + 1) / 2)))
        r = 6 + (i % 3) * 2
        d.ellipse(
            [x - r, y - r, x + r, y + r],
            outline=(base_r + 100, base_g + 100, base_b + 100),
            width=2,
        )

    # Kadr raqami va vaqt
    stamp = time.strftime("%d.%m.%Y %H:%M:%S")
    d.rectangle([0, 0, 230, 24], fill=(0, 0, 0))
    d.text((6, 5), f"CAM{seed % 100:02d} SIM", fill=(160, 220, 160))
    d.text((110, 5), stamp, fill=(220, 220, 220))

    return img
