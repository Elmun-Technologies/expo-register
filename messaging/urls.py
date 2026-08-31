from django.urls import path

from . import views


urlpatterns = [

    path(
        "",
        views.conversation_list,
        name="conversation_list",
    ),

    path(
        "event/<int:event_id>/start/",
        views.start_conversation,
        name="start_conversation",
    ),

    path(
        "conversation/<int:conversation_id>/",
        views.conversation_detail,
        name="conversation_detail",
    ),

    path(
        "conversation/<int:conversation_id>/send/",
        views.send_message,
        name="send_message",
    ),

]