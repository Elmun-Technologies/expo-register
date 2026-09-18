"""
Telegram botni ishga tushirish (long polling).

Ishlatish:
    python manage.py telegram_bot

Token `.env` da (TELEGRAM_BOT_TOKEN). Yo'q bo'lsa bot chiqadi.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Expo Telegram botini ishga tushirish (long polling)"

    def handle(self, *args, **options):
        from expo.telegram_bot import run_polling

        run_polling()
