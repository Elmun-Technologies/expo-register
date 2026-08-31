from django import forms

from .models import Feedback


class FeedbackForm(forms.ModelForm):

    class Meta:
        model = Feedback

        fields = [
            "rating",
            "comment",
        ]

        widgets = {
            "rating": forms.RadioSelect(
                choices=Feedback._meta.get_field(
                    "rating"
                ).choices
            ),
            "comment": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": (
                        "Share your experience with this event..."
                    ),
                    "maxlength": 2000,
                }
            ),
        }

        labels = {
            "rating": "Your Rating",
            "comment": "Your Feedback",
        }

    def clean_rating(self):

        rating = self.cleaned_data.get("rating")

        if rating is None:
            raise forms.ValidationError(
                "Please select a rating."
            )

        if not 1 <= int(rating) <= 5:
            raise forms.ValidationError(
                "Rating must be between 1 and 5."
            )

        return rating

    def clean_comment(self):

        comment = (
            self.cleaned_data.get("comment") or ""
        ).strip()

        return comment