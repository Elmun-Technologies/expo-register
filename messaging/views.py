from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from events.models import Event
from registrations.models import Registration

from .models import Conversation, Message


@login_required
def conversation_list(request):
    """
    Display conversations available to the current user.
    """

    conversations = (
        Conversation.objects
        .select_related(
            "event",
            "attendee",
            "organizer",
        )
        .filter(
            Q(attendee=request.user)
            | Q(organizer=request.user)
        )
        .order_by("-updated_at")
    )

    return render(
        request,
        "messaging/conversation_list.html",
        {
            "conversations": conversations,
        },
    )


@login_required
def start_conversation(request, event_id):
    """
    Start or open a conversation between an attendee
    and the organizer of an event.

    Only registered attendees can start conversations.
    """

    event = get_object_or_404(
        Event.objects.select_related("organizer"),
        id=event_id,
    )

    # Organizer cannot message themselves.
    if event.organizer == request.user:
        messages.error(
            request,
            "You cannot start a conversation with yourself.",
        )

        return redirect(
            "event_detail",
            slug=event.slug,
        )

    # Only registered attendees can message organizers.
    registration = (
        Registration.objects
        .filter(
            attendee=request.user,
            event=event,
            status__in=[
                Registration.Status.REGISTERED,
                Registration.Status.ATTENDED,
            ],
        )
        .first()
    )

    if not registration:
        messages.error(
            request,
            "You must be registered for this event before contacting the organizer.",
        )

        return redirect(
            "event_detail",
            slug=event.slug,
        )

    conversation, created = Conversation.objects.get_or_create(
        event=event,
        attendee=request.user,
        organizer=event.organizer,
    )

    return redirect(
        "conversation_detail",
        conversation_id=conversation.id,
    )


@login_required
def conversation_detail(request, conversation_id):
    """
    Display a conversation only if the current user is
    either the attendee or organizer.
    """

    conversation = get_object_or_404(
        Conversation.objects.select_related(
            "event",
            "attendee",
            "organizer",
        ),
        Q(
            id=conversation_id,
            attendee=request.user,
        )
        | Q(
            id=conversation_id,
            organizer=request.user,
        ),
    )

    conversation_messages = (
        conversation.messages
        .select_related("sender")
        .order_by("created_at")
    )

    # Mark messages sent by the other participant as read.
    conversation.messages.filter(
        is_read=False,
    ).exclude(
        sender=request.user,
    ).update(
        is_read=True,
    )

    return render(
        request,
        "messaging/conversation_detail.html",
        {
            "conversation": conversation,
            "conversation_messages": conversation_messages,
        },
    )


@login_required
@require_POST
def send_message(request, conversation_id):
    """
    Send a message inside a conversation.

    The sender is ALWAYS taken from request.user.
    """

    conversation = get_object_or_404(
        Conversation.objects.select_related(
            "event",
            "attendee",
            "organizer",
        ),
        Q(
            id=conversation_id,
            attendee=request.user,
        )
        | Q(
            id=conversation_id,
            organizer=request.user,
        ),
    )

    content = request.POST.get(
        "content",
        "",
    ).strip()

    if not content:
        messages.error(
            request,
            "Message cannot be empty.",
        )

        return redirect(
            "conversation_detail",
            conversation_id=conversation.id,
        )

    if len(content) > 5000:
        messages.error(
            request,
            "Message cannot exceed 5000 characters.",
        )

        return redirect(
            "conversation_detail",
            conversation_id=conversation.id,
        )

    Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=content,
    )

    # Update conversation activity timestamp.
    conversation.save(
        update_fields=[
            "updated_at",
        ],
    )

    return redirect(
        "conversation_detail",
        conversation_id=conversation.id,
    )