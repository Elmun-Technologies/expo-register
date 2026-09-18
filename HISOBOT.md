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
| `hikvision.py` | Hikvision ISAPI/RTSP adapter: **Digest auth**, jonli snapshot, PTZ preset, stream URL |
| `simulation.py` | Demo rejim uchun deterministik harakat yo'llari |
| `forms.py` | Kiosk formasi (O'z/Rus tilli) |
| `face.py` | Yuzni aniqlash (OpenCV Haar) + yuz izi (hash) + **dublikat nazorati** |
| `pdf.py` | PDF hisobotlar: stend analitikasi + mehmonlar ro'yxati (Cyrillic qo'llab-quvvatlash bilan) |
| `sms.py` | **Eskiz.uz** SMS xabarnoma adapteri (O'zbekiston SMS provayderi) |
| `telegram.py` | Telegram xabarnoma (admin guruhga yangi mehmon haqida xabar) |
| `gate.py` | **Darvoza xizmati**: QR/jobida ro'yxatdan mehmon yaratish + kuzatuv boshlash + offline sinxronlash |
| `telegram_bot.py` | **Telegram bot**: mijoz ro'yxatdan o'tadi → QR oladi (long polling) |
| `management/commands/telegram_bot.py` | Botni ishga tushirish: `python manage.py telegram_bot` |
| `static/expo/js/html5-qrcode.min.js` | QR skaner kutubxonasi (lokal — internet kerak emas) |
| `static/expo/js/gate-sw.js` | Service Worker — manager telefoni offline ishlashini ta'minlaydi |
| `data/haarcascade_frontalface_default.xml` | OpenCV yuzni aniqlash modeli fayli |

### 🚪 Darvoza (Gate) — offline rejim qanday ishlaydi

**Oqim (Telegram bot → QR → darvoza):**
1. Mijoz **Telegram bot**da (`/start`) ro'yxatdan o'tadi — ism, familiya,
   kompaniya, maqsad kiritadi.
2. Bot ro'yxatdan o'tkazib **avtomatik QR kartochka (rasm)** yuboradi
   (QR ichida Eventify Ticket ID — UUID).
3. Kirish joyida manager telefonida `/expo/gate/` sahifasini ochadi.
4. QR skaner (kamera) mijoz QR sini o'qiydi → tizim uni registratsiyadan
   topib **ExpoVisitor yaratadi va darhol kuzatuvni boshlaydi**.
5. QR bo'lmasa — manager **joyida** ism/familiya/kompaniya kiritadi
   (walk-in) — xuddi shunday kuzatuv boshlanadi.

**Telegram bot (qo'shimcha kanal):**
- `python manage.py telegram_bot` — botni ishga tushiradi (long polling).
- BotFather'dan `TELEGRAM_BOT_TOKEN` olinib `.env` ga yoziladi.
- `/start` — mijoz ro'yxati; `/manager` — manager rejimi.
- Bot ham mijozni Eventify'ga (`User` + `Registration`) bog'laydi va
  QR tayyorlaydi — darvoza skaneri bilan bir xil format.

**Offline (internet uzilganda):**
- Skanerlangan yoki kiritilgan yozuv **telefon xotirasida (localStorage)** saqlanadi.
- Ekran "Offline — navbatda saqlanadi" deb ko'rsatadi.
- Internet qaytganda **bir tugma bilan (Sinxronlash)** yoki avtomatik yuboriladi.
- Har bir offline yozuvga unikal `offline_id` beriladi — shu tufayli
  xuddi shu yozuv **ikki marta takror kiritilmaydi** (idempotentlik).
- Sahifa Service Worker orqali keshlanadi — telefon butunlay offline
  bo'lsa ham gate sahifasi ochiladi.

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
| **Darvoza (QR skaner)** | `/expo/gate/` | Admin, Security (offline-friendly) |
| Darvoza API | `/expo/gate/api/` | Admin, Security |
| Darvoza auto-QR | `/expo/gate/auto-qr/<id>/` | Ro'yxatdan o'tgan mijoz |
| Monitoring paneli | `/expo/monitor/` | Admin, Security |
| Mehmonlar ro'yxati | `/expo/visitors/` | Admin, Security |
| Mehmon detal (kuzatuv yo'li) | `/expo/visitors/<id>/` | Admin, Security, Stend egasi |
| Qurilmalar (kameralar+stendlar) | `/expo/devices/` | Admin |
| Stend analitikasi | `/expo/analytics/` | Admin, Stend egasi |
| Tadbirlar | `/events/` | Login bilan |
| Dashboard | `/dashboard/` | Rollarga qarab |
| Hisobotlar | `/dashboard/reports/` | Admin |
| Badge (QR kartochka) | `/expo/visitors/<id>/badge/` | Admin, Security, Stend egasi |
| CSV eksport (mehmonlar) | `/expo/visitors/export/` | Admin, Security |
| PDF hisobot (mehmonlar) | `/expo/visitors/pdf/` | Admin, Security |
| PDF hisobot (analitika) | `/expo/analytics/pdf/` | Admin |
| CSV eksport (stend mehmonlari) | `/expo/analytics/booth/<id>/export/` | Admin, shu stend egasi |

---

## 5. Demo hisoblar

| Hисоб | Parol | Rol |
|---|---|---|
| `expo_admin` | `expo12345` | Admin |
| `security` | `security123` | Xavfsizlik |
| `aloqa` | `aloqa12345` | Stend egasi (AloqaBank Digital) |
| `uzauto` | `uzauto12345` | Stend egasi (UzAuto Tech) |
| `bepro` | `bepro12345` | Stend egasi (BePro Startup) |
| `mehmon_demo` | `mehmon12345` | Mehmon (QR tiketli) |

Demo ma'lumotlarni qayta yaratish: `python manage.py seed_expo_demo`

---

## 6. Bu bilan NIMALAR qila olamiz (imkoniyatlar)

### Hozir (ishlayapti)
1. **Mehmonlarni to'liq nazorat** — kim keldi, qachon keldi, qayerga kirdi, qancha turdi, qachon chiqdi.
2. **Xavfsizlik paneli** — real vaqtda kameralar (jonli kadrlar) + ogohlantirishlar + ichkaridagi mehmonlar (avto-yangilanish 5 s).
3. **Stend analitikasi** — qaysi stend qanchalik qiziq? (noyob mehmonlar, tashriflar, o'rtacha vaqt).
4. **Reyting** — eng qiziq stendlar ro'yxati (admin uchun).
5. **Yuzni aniqlash + dublikat nazorati** — kiosk kamerasi suratidan yuz olinadi va bir odam ikkinchi marta ro'yxatdan o'tmaydi (ism yoki yuz bo'yicha aniqlanadi).
6. **Telegram bot → QR → darvoza oqimi** — mijoz Telegram'da ro'yxatdan o'tadi, QR oladi, manager skanerlab ichkariga kiritadi, kuzatuv darhol boshlanadi.
7. **Offline darvoza** — internet uzilganda ham manager telefoni ishlaydi: yozuv navbatga saqlanadi, ulanish qaytganda avtomatik sinxronlanadi (takror yozilmaydi).
8. **QR-kartochka (Badge)** — har bir mehmonga unikal QR-kodli kartochka, chop etish imkoniyati bilan.
9. **CSV eksport** — mehmonlar ro'yxati (umumiy) va har bir stend uchun alohida (o'zbekcha BOM bilan).
10. **PDF hisobotlar** — stend analitikasi va mehmonlar ro'yxati (o'zbekcha/ruscha shrift bilan).
11. **Telegram + SMS xabarnoma** — yangi mehmon ro'yxatdan o'tganda admin guruhga Telegram xabar va telefonga Eskiz.uz SMS.
12. **Admin dashboard integratsiyasi** — Expo ko'rsatkichlari (faol mehmonlar, stendlar, kameralar) asosiy dashboard'da.
13. **To'liq Eventify funksionalligi** — tadbirlar, QR-ticket, check-in, notification'lar, chatbot.
14. **Hikvision LIVE qatlami** — `Camera.mode = LIVE` + IP/login/parol bilan: Digest auth, jonli snapshot, PTZ preset, RTSP stream URL; SIMULATION'da virtual kadr.

### Kelajakda (qatlam tayyor, ulash kerak)
1. **Kamera'dan avtomatik ob'ekt kuzatish** — Hikvision'ning o'z motion/abonement eventlarini tinglab (ISAPI event subscription) mehmonga bog'lash.
2. **Chuqur yuz tanish (face recognition)** — hozir Haar + yuz izi ishlayapti; katta tadbir uchun FaceNet/Iris.ai kabi chuqur model ulash mumkin (qatlam `face.py` da almashtiriladi).
3. **To'lov integratsiyasi** — Payme / Click / Payze (pullik tadbirlar uchun).
4. **Mobil ilova** — kiosk va monitoring'ni tabletkada ishlatish.
5. **Eskiz.uz real token** — `.env` da `ESKIZ_EMAIL`/`ESKIZ_PASSWORD` kiritilgach SMS avtomatik ishlaydi (hozir konsol rejimi).

---

## 7. Texnik holat

- ✅ `python manage.py check` — 0 xato
- ✅ `python manage.py test expo` — 32/32 test o'tdi
- ✅ `migrate` — barcha migratsiyalar qo'llangan (`face_hash`, `visit_type`, `source`, `offline_id`, `registration`)
- ✅ Server ishga tushirilgan (LIVE PREVIEW, port 8000)
- ✅ GitHub: barcha ishlar push qilindi
- ✅ OpenCV 4.10 yuzni aniqlash + haarcascade modeli bog'langan
- ✅ QR skaner (html5-qrcode) lokal — offline ishlaydi
- ✅ Service Worker — gate sahifasi offline keshlanadi

---

## 8. Keyingi qadamlar (tavsiyalar)

1. **Haqiqiy kamera seriallarini kiriting** va LIVE rejimni sinab ko'ring (`Camera.mode = LIVE`).
2. **Chuqur yuz tanish (FaceNet/Iris.ai)** — katta tadbir uchun aniqroq tanish (hozir Haar+iz ishlayapti).
3. **Payme/Click to'lov** — pullik eksponingiz bo'lsa.
4. **SMS xabarnoma (real)** — `env.example` asosida `.env` yarating, Eskiz.uz login/parol kiriting.
5. **Brendlash** — "Expo Control" nomi/logo'larini to'liq almashtirish.

Rasmiy hisobotning to'liq texnik variantini ham tayyorlab bera olaman (PDF/Markdown).
