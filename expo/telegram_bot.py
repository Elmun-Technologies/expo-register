"""
Telegram bot — Expo ro'yxatdan o'tish va kirish nazorati uchun.

Nimalar qila oladi:
- Mijoz botda ro'yxatdan o'tadi (ism, familiya, kompaniya, maqsad).
- Ro'yxatdan o'tgach QR kartochka oladi — manager darvoza skaneri
  shu QR ni o'qib mijozni ichkariga kiritadi (expo.gate).
- Manager (kirish nazorati) uchun oddiy menyu.

Faqat bitta oqim yetarli — Eventify foydalanuvchisi yaratish orqali
``Registration`` + ``ticket_qr`` tayyor bo'ladi (avto QR).

WEBHOOKʼdan voz kechdik — sandboxʼda tashqi kirish yo'q. Buning o'rniga
uzoq so'rov (long polling) rejimi ishlatiladi: python-telegram-bot
``Application.run_polling``. Ishlatishdan oldin BotFather orqali
``TELEGRAM_BOT_TOKEN`` olinadi.

E'tibor: handlerlar async — Django ORM faqat ``sync_to_async`` orqali
chaqiriladi (async kontekstda sinxron ORM taqiqlangan).
"""

import io
import logging
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

import qrcode  # noqa: E402
from asgiref.sync import sync_to_async  # noqa: E402
from django.conf import settings  # noqa: E402
from django.db import transaction  # noqa: E402
from telegram import (  # noqa: E402
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ChatAction  # noqa: E402
from telegram.ext import (  # noqa: E402
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .models import TelegramProfile  # noqa: E402

logger = logging.getLogger(__name__)

# Konversatsiya holatlari
(
    ST_FIRST_NAME,
    ST_LAST_NAME,
    ST_COMPANY,
    ST_PURPOSE,
    ST_PHONE,
) = range(5)

PURPOSE_LABELS = {
    "BUSINESS": "💼 Biznes",
    "PARTNERSHIP": "🤝 Hamkorlik",
    "INVESTOR": "💰 Investor",
    "MEDIA": "📰 Matbuot / Media",
    "STUDENT": "🎓 Talaba",
    "OTHER": "ℹ️ Boshqa",
}


def _token():
    return getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""


# ====================================================
# Sinxron (DB bilan ishlaydigan) yordamchilar
# ====================================================

def _get_or_create_profile_sync(telegram_id, username="", first_name="", last_name=""):
    """Telegram foydalanuvchisiga mos TelegramProfile (sinxron)."""
    profile, created = TelegramProfile.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
        },
    )
    if not created:
        changed = {}
        if profile.username != username:
            changed["username"] = username
        if profile.first_name != first_name:
            changed["first_name"] = first_name
        if profile.last_name != last_name:
            changed["last_name"] = last_name
        if changed:
            for k, v in changed.items():
                setattr(profile, k, v)
            profile.save(update_fields=list(changed.keys()))
    return profile


def _set_profile_fields_sync(profile, **fields):
    """Profile obyektini yangilash (sinxron)."""
    for k, v in fields.items():
        setattr(profile, k, v)
    profile.save(update_fields=list(fields.keys()))
    return profile


def _default_organizer_sync():
    """Admin/har qanday organizer foydalanuvchini topish yoki yaratish."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    organizer = (
        User.objects.filter(role=User.Role.ORGANIZER).first()
        or User.objects.filter(is_superuser=True).first()
        or User.objects.filter(is_staff=True).first()
    )
    if not organizer:
        organizer = User.objects.create_user(
            username="expo_organizer",
            first_name="Expo",
            last_name="Organizer",
            role=User.Role.ORGANIZER,
        )
    return organizer


def _default_event_sync():
    """Bot ro'yxatga olinadigan expo tadbirini tanlash."""
    from events.models import Event, EventCategory

    event = (
        Event.objects.filter(status=Event.Status.PUBLISHED)
        .order_by("event_date", "start_time")
        .first()
    )
    if not event:
        category, _ = EventCategory.objects.get_or_create(
            name="Texnologiya", defaults={"slug": "texnologiya"}
        )
        event = Event.objects.create(
            title="O'zbekiston Expo — Texnologiyalar 2026",
            slug="ozbekiston-expo-texnologiyalar-2026",
            description="O'zbekiston texnologiyalar ko'rgazmasi",
            venue="Toshkent, Uzexpocentre",
            category=category,
            status=Event.Status.PUBLISHED,
            event_date="2026-10-15",
            start_time="10:00:00",
            end_time="18:00:00",
            registration_deadline="2026-10-14 23:59:59",
            max_capacity=1000,
            available_seats=990,
            price=0,
            organizer=_default_organizer_sync(),
        )
    return event


def build_qr_png(registration, box_size=10, border=2):
    """Ro'yxat uchun QR PNG (ByteIO). ORM ga tegmaydi."""
    payload = (
        f"Ticket ID:\n{registration.ticket_code}\n\n"
        f"Attendee:\n{registration.attendee.username}\n\n"
        f"Event:\n{registration.event.title}\n"
    )
    qr = qrcode.make(payload, box_size=box_size, border=border)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _finish_registration_sync(telegram_id, username, tg_first_name, tg_last_name, data, phone=""):
    """
    Ro'yxatni to'liq yaratish (sinxron, thread da ishlaydi).

    Qaytaradi: (profile, registration, event, first_name, last_name,
                company, purpose)
    """
    from django.contrib.auth import get_user_model
    from registrations.models import Registration
    from registrations.utils import generate_ticket_qr

    User = get_user_model()
    profile = _get_or_create_profile_sync(
        telegram_id, username, tg_first_name, tg_last_name
    )

    first_name = data.get("first_name") or tg_first_name or ""
    last_name = data.get("last_name") or tg_last_name or ""
    company = data.get("company", "")
    purpose = data.get("purpose", "BUSINESS")

    username_base = f"tg{telegram_id}"
    with transaction.atomic():
        account, account_created = User.objects.get_or_create(
            username=username_base,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "role": User.Role.ATTENDEE,
            },
        )
        # Har safar ma'lumotni yangilaymiz (profil ma'lumotlari o'zgargan bo'lishi mumkin)
        account.first_name = first_name or account.first_name
        account.last_name = last_name or account.last_name
        if phone:
            account.phone_number = phone
        account.save(
            update_fields=[
                "first_name",
                "last_name",
                "phone_number",
            ]
        )

        profile.user = account
        profile.first_name = first_name
        profile.last_name = last_name
        profile.state = "DONE"
        profile.save(update_fields=["user", "first_name", "last_name", "state"])

        event = _default_event_sync()
        registration, _ = Registration.objects.get_or_create(
            attendee=account,
            event=event,
            defaults={"status": Registration.Status.REGISTERED},
        )
        if registration.status == Registration.Status.CANCELLED:
            registration.status = Registration.Status.REGISTERED
            registration.save(update_fields=["status"])

        if not registration.ticket_qr:
            generate_ticket_qr(registration)

    return profile, registration, event, first_name, last_name, company, purpose


# ====================================================
# Async handlerlar
# ====================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    profile = await sync_to_async(_get_or_create_profile_sync)(
        user.id, user.username or "", user.first_name or "", user.last_name or ""
    )

    if profile.kind == TelegramProfile.Kind.MANAGER:
        await update.message.reply_text(
            "👋 Salom, manager! Siz kirish nazorati menyusidasiz.\n\n"
            "Mehmonlarni ro'yxatga olish uchun /new_visitor yoki "
            "menyudan foydalaning."
        )
        return ConversationHandler.END

    await sync_to_async(_set_profile_fields_sync)(profile, state=ST_FIRST_NAME)

    text = (
        "👋 Assalomu alaykum! \"Expo\" mehmonlarini ro'yxatga olish botiga xush kelibsiz.\n\n"
        "Sizni ro'yxatga olib, QR kartochka beraman. Darvoza oldida "
        "shu QR ni ko'rsatasiz — biz sizni kiritamiz va kuzatuvni boshlaymiz.\n\n"
        "Ismingizni kiriting:"
    )
    await update.message.reply_text(text)
    return ST_FIRST_NAME


async def manager_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manager uchun alohida /manager buyrug'i."""
    user = update.effective_user
    profile = await sync_to_async(_get_or_create_profile_sync)(
        user.id, user.username or "", user.first_name or "", user.last_name or ""
    )
    await sync_to_async(_set_profile_fields_sync)(
        profile, kind=TelegramProfile.Kind.MANAGER
    )
    await update.message.reply_text(
        "✅ Siz manager sifatida belgilandingiz.\n\n"
        "Mehmonni joyida ro'yxatga olish uchun /new_visitor"
    )
    return ConversationHandler.END


async def collect_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["first_name"] = update.message.text.strip()
    await update.message.reply_text("Familiyangizni kiriting:")
    return ST_LAST_NAME


async def collect_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["last_name"] = update.message.text.strip()
    await update.message.reply_text(
        "Kompaniya nomi (yo'q bo'lsa — \"Yo'q\" deb yozing):"
    )
    return ST_COMPANY


async def collect_company(update: Update, context: ContextTypes.DEFAULT_TYPE):
    company = update.message.text.strip()
    if company.lower() in ("yo'q", "yoq", "нет", "нету", "-", "none"):
        company = ""
    context.user_data["company"] = company

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(PURPOSE_LABELS["BUSINESS"], callback_data="P_BUSINESS")],
            [InlineKeyboardButton(PURPOSE_LABELS["PARTNERSHIP"], callback_data="P_PARTNERSHIP")],
            [InlineKeyboardButton(PURPOSE_LABELS["INVESTOR"], callback_data="P_INVESTOR")],
            [InlineKeyboardButton(PURPOSE_LABELS["MEDIA"], callback_data="P_MEDIA")],
            [InlineKeyboardButton(PURPOSE_LABELS["STUDENT"], callback_data="P_STUDENT")],
            [InlineKeyboardButton(PURPOSE_LABELS["OTHER"], callback_data="P_OTHER")],
        ]
    )
    await update.message.reply_text("Tashrif maqsadingizni tanlang:", reply_markup=keyboard)
    return ST_PURPOSE


async def collect_purpose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    purpose = query.data.replace("P_", "")
    context.user_data["purpose"] = purpose

    reply_kb = ReplyKeyboardMarkup(
        [
            [KeyboardButton("Telefonni yuborish", request_contact=True)],
            [KeyboardButton("O'tkazib yuborish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await query.message.reply_text(
        f"Tanlandi: {PURPOSE_LABELS[purpose]}\n\n"
        "Telefon raqamingiz (ixtiyoriy) — yoki \"O'tkazib yuborish\" bosing:",
        reply_markup=reply_kb,
    )
    return ST_PHONE


async def collect_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = ""
    if update.message.contact:
        phone = update.message.contact.phone_number or ""
    else:
        text = (update.message.text or "").strip()
        if text.lower() not in (
            "o'tkazib yuborish",
            "otkazib yuborish",
            "skip",
            "нет",
            "yo'q",
        ):
            phone = text
    return await _finish_registration(update, context, phone)


async def _finish_registration(update, context, phone=""):
    user = update.effective_user
    result = await sync_to_async(_finish_registration_sync)(
        user.id,
        user.username or "",
        user.first_name or "",
        user.last_name or "",
        context.user_data,
        phone,
    )
    (profile, registration, event, first_name, last_name, company, purpose) = result

    await update.message.reply_text(
        "✅ Ro'yxatdan o'tdingiz! Qr kartochkangiz tayyorlanmoqda…"
    )
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO
    )

    qr_img = await sync_to_async(build_qr_png)(registration)
    caption = (
        f"🎟️ <b>{event.title}</b>\n\n"
        f"👤 {first_name} {last_name}\n"
        + (f"🏢 {company}\n" if company else "")
        + f"🎯 {PURPOSE_LABELS.get(purpose, purpose)}\n\n"
        f"Ticket ID: <code>{registration.ticket_id()}</code>\n\n"
        "Kirishda shu QR ni manager\u2019ga ko\u2019rsating — "
        "sizni kiritib, kuzatuvni boshlaymiz."
    )
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=qr_img,
        caption=caption,
        parse_mode="HTML",
    )

    context.user_data.clear()
    return ConversationHandler.END


async def new_visitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manager — mehmonni o'zi ro'yxatga olish (qo'lda)."""
    return await start(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi. Qayta boshlash uchun /start.")
    context.user_data.clear()
    return ConversationHandler.END


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Botdan foydalanish:\n"
        "/start — ro'yxatdan o'tish\n"
        "/manager — manager rejimiga o'tish\n"
        "/cancel — bekor qilish"
    )


def build_application(token=None):
    """python-telegram-bot Application obyektini qurish."""
    token = token or _token()
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN sozlanmagan. BotFather orqali token oling "
            "va .env ga kiriting."
        )

    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ST_FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_first_name)],
            ST_LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_last_name)],
            ST_COMPANY: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_company)],
            ST_PURPOSE: [CallbackQueryHandler(collect_purpose)],
            ST_PHONE: [
                MessageHandler(filters.CONTACT, collect_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, collect_phone),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("manager", manager_start))
    app.add_handler(CommandHandler("new_visitor", new_visitor))
    app.add_handler(CommandHandler("help", help_cmd))

    return app


def run_polling(token=None):
    app = build_application(token)
    logger.info("Telegram bot polling boshlandi…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
