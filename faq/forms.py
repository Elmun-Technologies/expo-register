from django import forms

from .models import FAQ


class FAQForm(forms.ModelForm):

    class Meta:
        model = FAQ

        fields = [
            "question",
            "answer",
            "display_order",
            "is_active",
        ]

        widgets = {
            "question": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. What time should I arrive?",
                }
            ),
            "answer": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Enter the answer...",
                }
            ),
            "display_order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        labels = {
            "question": "Question",
            "answer": "Answer",
            "display_order": "Display Order",
            "is_active": "Active",
        }