from django.urls import path

from . import views


urlpatterns = [
    path(
        "event/<int:event_id>/submit/",
        views.submit_feedback,
        name="submit_feedback",
    ),
]