# 📊 Loyiha hisoboti — Expo Register (O'zbekiston bozoriga moslashtirilgan)

**Sana:** 2026-09-18
**Branch:** `arena/01a0b2c9-expo-register`
**Base loyiha:** Eventify (Django 5.2 + Bootstrap 5)

---

## 1. Loyiha nima?

Bu — **Django** asosida qurilgan **tadbir/tadbirdorlik boshqaruvi platformasi** (Eventify) bo'lib, biz uni **O'zbekiston expo (ko'rgazma) bozori** uchun to'liq moslashtirdik. Endi tizim ikki katta qismdan iborat:

| Qism | Tavsif |
|---|---|
| 🎟️ **Eventify (saqlangan)** | Tadbirlar, ro'yxatdan o'tish, QR-ticket, check-in, notification, chatbot, dashboard |
| 🎥 **Expo Monitoring (yangi)** | Mehmonlarni kuzatish, kameralar, stend analitikasi, xavfsizlik paneli |

---

## 2. Siz aytgan oqim — qanday ishlaydi

```
Mehmon kioskka keladi
        ↓
Ism + Familiya kiritadi  (kompaniya, maqsad, telefon ixtiyoriy)
        ↓
TIZIM ISHGA TUSHADI
        ↓
"Ro'yxatga olindi" xabari → Xavfsizlik xodimi panelida paydo bo'ladi
        ↓
Kuzatuv kameralari shu mehmonni kuzatishni BOSHLAB YUBORADI
        ↓
Mehmon qaysi zonada, qaysi stend oldida — har bir qadam qayd qilinadi
        ↓
Stend egasi: "mening stendimga qancha mehmon keldi, qancha vaqt turishdi" statistikasini ko'radi
```

✅ Bu hammasi **hozir ishlayapti** (demo rejimida virtual harakat yo'llari bilan; haqiqiy Hikvision kameralariga ulash qatlami tayyor).

---

## 3. Nima qo'shildi / o'zgartirildi

### 🎥 Yangi "Expo" moduli (`expo/` ilovasi)

| Fayl | Vazifa |
|---|---|
| `models.py` | 5 ta model: `Booth` (stend), `Camera` (kamera), `ExpoVisitor` (mehmon), `TrackingEvent` (kuzatuv hodisasi), `VisitAlert` (xabar) |
| `services.py` | Kuzatuv mantig'i: ro'yxatdan o'tish → xabar → kuzatuv boshlani → zonalar → chiqib ketish |
| `analytics.py` | Stendlar statistikasi: noyob mehmonlar, tashriflar, o'rtacha qolish vaqti |
| `hikvision.py` | Hikvision ISAPI/RTSP adapter qatlami (LIVE rejim uchun tayyor) |
| `simulation.py` | Demo rejim uchun deterministik harakat yo'llari |
| `forms.py` | Kiosk formasi (O'z/Rus tilli) |

### 🔐 Yangi rollar va huquqlar

- **ADMIN** — hamma narsani ko'radi va boshqaradi
- **SECURITY (Xavfsizlik)** — faqat monitoring paneli, mehmonlar, kiosk
- **ORGANIZER (Stend egasi)** — faqat o'z stendi statistikasi
- **ATTENDEE** — oddiy tadbir ishtirokchisi (Eventify qismi)

### 🌍 O'zbekiston bozoriga moslashuvlar

| Nima | Avval | Hozir |
|---|---|---|
| Vaqt zonasi | Asia/Kolkata | **Asia/Tashkent** ✅ |
| Pul birligi | ₹ (Hind rupiyasi) | **so'm (UZS)** ✅ |
| Narx formati | ₹500 | **150,000 so'm** (minglik ajratuvchi bilan) |
| Sana/vaqt | "18 Sep 2026, 10:15 AM" | **"18.09.2026 10:15"** (24 soatlik) |
| "Free" | Free | **Bepul** ✅ |
| Email jo'natuvchi | Event Management System | **Expo Control** ✅ |
| Hafta boshlanishi | yakshanba | **dushanba** ✅ |
| Til | Inglizcha | Kiosk O'z + Rus (almashtirish bilan) ✅ |

---

## 4. Sahifalar (URL'lar)

| Sahifa | URL | Kimga ochiq |
|---|---|---|
| Bosh sahifa | `/` | Hammaga |
| Kiosk (O'z) | `/expo/kiosk/` | Hammaga (terminalsiz) |
| Kiosk (Rus) | `/expo/kiosk/?lang=ru` | Hammaga |
| Monitoring paneli | `/expo/monitor/` | Admin, Security |
| Mehmonlar ro'yxati | `/expo/visitors/` | Admin, Security |
| Mehmon detal (kuzatuv yo'li) | `/expo/visitors/<id>/` | Admin, Security, Stend egasi |
| Qurilmalar (kameralar+stendlar) | `/expo/devices/` | Admin |
| Stend analitikasi | `/expo/analytics/` | Admin, Stend egasi |
| Tadbirlar | `/events/` | Login bilan |
| Dashboard | `/dashboard/` | Rollarga qarab |
| Hisobotlar | `/dashboard/reports/` | Admin |

---

## 5. Demo hisoblar

| Hисоб | Parol | Rol |
|---|---|---|
| `expo_admin` | `expo12345` | Admin |
| `security` | `security123` | Xavfsizlik |
| `aloqa` | `aloqa12345` | Stend egasi (AloqaBank Digital) |
| `uzauto` | `uzauto12345` | Stend egasi (UzAuto Tech) |
| `bepro` | `bepro12345` | Stend egasi (BePro Startup) |

Demo ma'lumotlarni qayta yaratish: `python manage.py seed_expo_demo`

---

## 6. Bu bilan NIMALAR qila olamiz (imkoniyatlar)

### Hozir (ishlayapti)
1. **Mehmonlarni to'liq nazorat** — kim keldi, qachon keldi, qayerga kirdi, qancha turdi, qachon chiqdi.
2. **Xavfsizlik paneli** — real vaqtda kameralar + ogohlantirishlar + ichkaridagi mehmonlar (avto-yangilanish 5 s).
3. **Stend analitikasi** — qaysi stend qanchalik qiziq? (noyob mehmonlar, tashriflar, o'rtacha vaqt).
4. **Reyting** — eng qiziq stendlar ro'yxati (admin uchun).
5. **To'liq Eventify funksionalligi** — tadbirlar, QR-ticket, check-in, notification'lar, chatbot.

### Kelajakda (qatlam tayyor, ulash kerak)
6. **Haqiqiy Hikvision kameralar** — `Camera.mode = LIVE` qilib IP/login/parol kiritiladi (adapter `hikvision.py` tayyor).
7. **Yuz tanish (face recognition)** — kamera kadridan mehmonni avtomatik tanish (hozir adaptr tayyor, ML qo'shish kerak).
8. **Badge / QR chiqarish** — mehmon kartochkasi (badge_token allaqachon bor).
9. **SMS/Telegram xabarnoma** — O'zbekistonda mashhur; hozir email+in-app notif bo'lib, SMS provayderi qo'shish mumkin.
10. **To'lov integratsiyasi** — Payme / Click / Payze (pullik tadbirlar uchun).
11. **Tahlil/eksport** — statistikani Excel/PDF ko'rinishida eksport.
12. **Mobil ilova** — kiosk va monitoring'ni tabletkada ishlatish.

---

## 7. Texnik holat

- ✅ `python manage.py check` — 0 xato
- ✅ `python manage.py test expo` — 5/5 test o'tdi
- ✅ `migrate` — barcha migratsiyalar qo'llangan
- ✅ Server ishga tushirilgan (LIVE PREVIEW)
- ✅ GitHub: 2 ta commit push qilindi

---

## 8. Keyingi qadamlar (tavsiyalar)

1. **Haqiqiy kamera seriallarini kiriting** va LIVE rejimni sinab ko'ring.
2. **Yuz tanish (face recognition)** qo'shish — eng katta qiymat beradi.
3. **Payme/Click to'lov** — pullik eksponingiz bo'lsa.
4. **SMS xabarnoma** — Eskiz.uz yoki Playmobile orqali.
5. **Brendlash** — "Expo Control" nomi/logo'larini to'liq almashtirish.

Rasmiy hisobotning to'liq texnik variantini ham tayyorlab bera olaman (PDF/Markdown).
