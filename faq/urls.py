from django.urls import path

from . import views


urlpatterns = [

    path(
        "event/<int:event_id>/",
        views.faq_list,
        name="faq_list",
    ),

    path(
        "event/<int:event_id>/add/",
        views.faq_create,
        name="faq_create",
    ),

    path(
        "<int:faq_id>/edit/",
        views.faq_update,
        name="faq_update",
    ),

    path(
        "<int:faq_id>/delete/",
        views.faq_delete,
        name="faq_delete",
    ),

]