from django import forms

from .models import ExpoVisitor

PURPOSE_LABELS = {
    "uz": {
        ExpoVisitor.Purpose.BUSINESS: "Biznes",
        ExpoVisitor.Purpose.PARTNERSHIP: "Hamkorlik",
        ExpoVisitor.Purpose.INVESTOR: "Investor",
        ExpoVisitor.Purpose.MEDIA: "Matbuot / Media",
        ExpoVisitor.Purpose.STUDENT: "Talaba",
        ExpoVisitor.Purpose.OTHER: "Boshqa",
    },
    "ru": {
        ExpoVisitor.Purpose.BUSINESS: "Бизнес",
        ExpoVisitor.Purpose.PARTNERSHIP: "Партнёрство",
        ExpoVisitor.Purpose.INVESTOR: "Инвестор",
        ExpoVisitor.Purpose.MEDIA: "Пресса / Медиа",
        ExpoVisitor.Purpose.STUDENT: "Студент",
        ExpoVisitor.Purpose.OTHER: "Другое",
    },
}


class KioskCheckinForm(forms.ModelForm):
    """
    Expo kiosk ekranidagi kirish formasi.

    Mehmon faqat ism va familiyani kiritishi bilan tizim ishga tushadi;
    qolgan maydonlar ixtiyoriy. ``photo_data`` veb-kameradan olingan
    suratning base64 (data URL) ko'rinishi — maxfiy maydon.
    """

    photo_data = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = ExpoVisitor
        fields = (
            "first_name",
            "last_name",
            "company",
            "purpose",
            "phone",
        )
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-lg",
                    "placeholder": "Ism",
                    "autofocus": "autofocus",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-lg",
                    "placeholder": "Familiya",
                }
            ),
            "company": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Kompaniya (ixtiyoriy)",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "+998 XX XXX-XX-XX (ixtiyoriy)",
                }
            ),
            "purpose": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        lang = kwargs.pop("lang", "uz")
        super().__init__(*args, **kwargs)
        self.fields["purpose"].initial = ExpoVisitor.Purpose.BUSINESS
        labels = PURPOSE_LABELS.get(lang, PURPOSE_LABELS["uz"])
        self.fields["purpose"].choices = [
            (value, labels.get(value, label))
            for value, label in ExpoVisitor.Purpose.choices
        ]
