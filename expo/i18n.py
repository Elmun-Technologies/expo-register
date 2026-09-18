"""
Yengil ikki tilli (o'zbekcha/ruscha) yordamchi.

To'liq Django i18n tizimini ishlatmasdan turib, expo modulidagi
matnlarni lug'at orqali tarjima qiladi. Yangi matn qo'shish uchun
TRANSLATIONS lug'atiga key qo'shish kifoya.
"""

TRANSLATIONS = {
    "uz": {
        "expo.title": "Expo nazorat tizimi",
        "expo.subtitle": "Har bir mehmonni to'liq kuzatib boramiz",
        "booth": "Stend",
        "booths": "Stendlar",
        "camera": "Kamera",
        "cameras": "Kameralar",
        "visitor": "Mehmon",
        "visitors": "Mehmonlar",
        "monitoring": "Monitoring",
        "devices": "Qurilmalar",
        "analytics": "Analitika",
        "language": "Til",
        "waiting": "Yo'l",
        "report": "Hisobot",
        "reports": "Hisobotlar",
        "dashboard": "Boshqaruv paneli",
        "new_visitor_alert": "Yangi mehmon ro'yxatdan o'tdi",
        "tracking_started": "Kuzatuv boshlandi",
        "inside_now": "Hozir ichkarida",
        "total_today": "Bugun jami",
        "cameras_online": "Kamera onlayn",
        "detections_24h": "24 soatda aniqlashlar",
        "zone": "Hudud",
        "company": "Kompaniya",
        "purpose": "Maqsad",
        "status": "Holat",
        "inside": "Ichkarida",
        "left": "Chiqib ketdi",
        "minutes": "daqiqa",
        "visits": "Tashriflar",
        "unique_visitors": "Noyob mehmonlar",
        "avg_dwell": "O'rtacha qolish",
        "leaderboard": "Eng qiziq stendlar",
    },
    "ru": {
        "expo.title": "Система контроля Expo",
        "expo.subtitle": "Полный контроль каждого посетителя",
        "booth": "Стенд",
        "booths": "Стенды",
        "camera": "Камера",
        "cameras": "Камеры",
        "visitor": "Посетитель",
        "visitors": "Посетители",
        "monitoring": "Мониторинг",
        "devices": "Устройства",
        "analytics": "Аналитика",
        "language": "Язык",
        "waiting": "Путь",
        "report": "Отчёт",
        "reports": "Отчёты",
        "dashboard": "Панель управления",
        "new_visitor_alert": "Новый посетитель зарегистрирован",
        "tracking_started": "Слежение началось",
        "inside_now": "Сейчас внутри",
        "total_today": "Всего сегодня",
        "cameras_online": "Камеры онлайн",
        "detections_24h": "Обнаружений за 24ч",
        "zone": "Зона",
        "company": "Компания",
        "purpose": "Цель",
        "status": "Статус",
        "inside": "Внутри",
        "left": "Вышел",
        "minutes": "мин",
        "visits": "Посещения",
        "unique_visitors": "Уникальные посетители",
        "avg_dwell": "Среднее время",
        "leaderboard": "Самые популярные стенды",
    },
}

FALLBACK = "uz"


def translate(key, lang="uz"):
    if lang not in TRANSLATIONS:
        lang = FALLBACK
    return TRANSLATIONS.get(lang, {}).get(
        key, TRANSLATIONS[FALLBACK].get(key, key)
    )
