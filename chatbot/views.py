from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

from registrations.models import Registration

from .services import (
    ask_gemini,
    get_navigation_links,
    detect_registration_request,
    find_event_from_message,
    detect_cancellation_request,
    find_user_registration_from_message,
    detect_ticket_request,
    find_user_ticket_from_message,
)


# ==========================================================
# LOCAL FALLBACK
# ==========================================================

def local_fallback_response(message, user):
    """
    Local chatbot fallback used when Gemini is unavailable,
    exhausted, rate-limited, or otherwise fails.

    This keeps the Eventify chatbot functional without
    depending completely on the Gemini API.
    """

    text = message.lower().strip()

    # ======================================================
    # GREETING
    # ======================================================

    greetings = [
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
    ]

    if any(
        text == greeting
        or text.startswith(greeting + " ")
        for greeting in greetings
    ):
        return (
            "Hi! 👋 I'm the Eventify Assistant.\n\n"
            "I can help you with events, registrations, "
            "tickets, FAQs, navigation, and your Eventify "
            "account.\n\n"
            "What would you like to know?"
        )

    # ======================================================
    # HELP
    # ======================================================

    if any(
        phrase in text
        for phrase in [
            "what can you help",
            "what can you do",
            "help me",
            "help",
            "features",
        ]
    ):
        return (
            "I can help you with:\n\n"
            "🎟️ Event registration\n"
            "📅 Upcoming events\n"
            "🎫 Tickets and QR codes\n"
            "❌ Registration cancellation\n"
            "📋 Your registrations\n"
            "🧭 Eventify navigation\n"
            "❓ FAQs and platform help\n\n"
            "Try asking something such as "
            "\"show my registrations\" or "
            "\"find upcoming events\"."
        )

    # ======================================================
    # UPCOMING EVENTS
    # ======================================================

    if any(
        phrase in text
        for phrase in [
            "upcoming events",
            "find events",
            "find upcoming",
            "browse events",
            "available events",
            "event list",
            "show events",
            "events near",
        ]
    ):
        return (
            "You can browse all currently available "
            "events from the Eventify event directory. "
            "Use the button below to explore events."
        )

    # ======================================================
    # REGISTRATION EXPLANATION
    # ======================================================

    if any(
        phrase in text
        for phrase in [
            "how do i register",
            "how can i register",
            "how to register",
            "registration process",
            "register for an event",
        ]
    ):
        return (
            "To register for an event:\n\n"
            "1. Open Browse Events.\n"
            "2. Select the event you want to attend.\n"
            "3. Check that registration is open.\n"
            "4. Click the Register button.\n"
            "5. Complete the registration process.\n\n"
            "Once registration is successful, your ticket "
            "and QR code will be available in My Registrations."
        )

    # ======================================================
    # MY REGISTRATIONS
    # ======================================================

    if any(
        phrase in text
        for phrase in [
            "my registrations",
            "my registration",
            "registered events",
            "what am i registered",
            "events i registered",
        ]
    ):
        return (
            "You can view all your registered, attended, "
            "and cancelled events from My Registrations."
        )

    # ======================================================
    # TICKETS
    # ======================================================

    if any(
        phrase in text
        for phrase in [
            "my ticket",
            "my tickets",
            "ticket details",
            "ticket information",
            "qr code",
            "my qr",
            "show my qr",
            "download ticket",
        ]
    ):
        return (
            "Your event tickets are available from "
            "My Registrations. Open a registered event "
            "to view the ticket details and QR code."
        )

    # ======================================================
    # CANCELLATION
    # ======================================================

    if any(
        phrase in text
        for phrase in [
            "cancel registration",
            "cancel my registration",
            "unregister",
            "cancel my event",
        ]
    ):
        return (
            "You can cancel an active registration from "
            "My Registrations. Open the relevant registration "
            "and select Cancel Registration."
        )

    # ======================================================
    # DASHBOARD
    # ======================================================

    if "dashboard" in text:
        return (
            "Your Eventify Dashboard gives you quick access "
            "to your events, registrations, tickets, "
            "notifications, and account information."
        )

    # ======================================================
    # PROFILE
    # ======================================================

    if any(
        phrase in text
        for phrase in [
            "my profile",
            "edit profile",
            "profile",
            "account",
        ]
    ):
        return (
            "You can manage your personal information "
            "from the Profile section of Eventify."
        )

    # ======================================================
    # FAQ
    # ======================================================

    if any(
        phrase in text
        for phrase in [
            "faq",
            "faqs",
            "frequently asked",
            "common questions",
        ]
    ):
        return (
            "Eventify FAQs cover common questions about "
            "registration, tickets, events, cancellations, "
            "and using the platform."
        )

    # ======================================================
    # FALLBACK GENERAL RESPONSE
    # ======================================================

    return (
        "I can still help you with Eventify even though "
        "the AI service is temporarily unavailable.\n\n"
        "Try asking about:\n"
        "• Upcoming events\n"
        "• Event registration\n"
        "• My registrations\n"
        "• My tickets or QR code\n"
        "• Cancelling a registration\n"
        "• Your dashboard or profile\n"
        "• Eventify FAQs"
    )


# ==========================================================
# HELPER: BUILD RESPONSE
# ==========================================================

def chatbot_response(
    reply,
    links=None,
    success=True,
    status=200,
):
    """
    Keep all chatbot JSON responses consistent.
    """

    return JsonResponse(
        {
            "success": success,
            "reply": reply,
            "links": links or [],
        },
        status=status,
    )


# ==========================================================
# CHAT API
# ==========================================================

@login_required
@require_POST
def chat_api(request):

    # ======================================================
    # GET MESSAGE
    # ======================================================

    message = request.POST.get(
        "message",
        "",
    ).strip()

    # ======================================================
    # EMPTY MESSAGE
    # ======================================================

    if not message:

        return chatbot_response(
            "Please enter a message.",
            success=False,
            status=400,
        )

    # ======================================================
    # CHAT HISTORY
    # ======================================================

    chat_history = request.session.get(
        "eventify_chat_history",
        [],
    )

    # Make sure corrupted session data does not break chat.
    if not isinstance(chat_history, list):

        chat_history = []

    try:

        # ==================================================
        # 1. CANCELLATION REQUEST
        # ==================================================

        if detect_cancellation_request(message):

            registration = (
                find_user_registration_from_message(
                    message,
                    request.user,
                )
            )

            # ----------------------------------------------
            # Registration not found
            # ----------------------------------------------

            if not registration:

                event = find_event_from_message(
                    message
                )

                if event:

                    return chatbot_response(
                        (
                            f"You do not have an active "
                            f"registration for "
                            f"{event.title}."
                        ),
                        [
                            {
                                "label": "My Registrations",
                                "url": reverse(
                                    "my_registrations"
                                ),
                            }
                        ],
                        success=False,
                    )

                return chatbot_response(
                    (
                        "I couldn't identify which event "
                        "registration you want to cancel. "
                        "Please mention the event name."
                    ),
                    [
                        {
                            "label": "My Registrations",
                            "url": reverse(
                                "my_registrations"
                            ),
                        }
                    ],
                )

            # ----------------------------------------------
            # Already cancelled
            # ----------------------------------------------

            if (
                registration.status
                == Registration.Status.CANCELLED
            ):

                return chatbot_response(
                    (
                        f"Your registration for "
                        f"{registration.event.title} "
                        f"is already cancelled."
                    ),
                    [
                        {
                            "label": "My Registrations",
                            "url": reverse(
                                "my_registrations"
                            ),
                        }
                    ],
                )

            # ----------------------------------------------
            # Already attended
            # ----------------------------------------------

            if (
                registration.status
                == Registration.Status.ATTENDED
            ):

                return chatbot_response(
                    (
                        f"Your registration for "
                        f"{registration.event.title} "
                        f"cannot be cancelled because "
                        f"you have already attended "
                        f"the event."
                    ),
                    [
                        {
                            "label": "My Registrations",
                            "url": reverse(
                                "my_registrations"
                            ),
                        }
                    ],
                    success=False,
                )

            # ----------------------------------------------
            # Confirmation required
            # ----------------------------------------------

            return chatbot_response(
                (
                    f"Are you sure you want to cancel "
                    f"your registration for "
                    f"{registration.event.title}?"
                ),
                [
                    {
                        "label": "Yes, Cancel Registration",
                        "url": (
                            f"/my-registrations/"
                            f"{registration.id}/cancel/"
                        ),
                    },
                    {
                        "label": "Keep Registration",
                        "url": reverse(
                            "my_registrations"
                        ),
                    },
                ],
            )

        # ==================================================
        # 2. TICKET REQUEST
        # ==================================================

        if detect_ticket_request(message):

            ticket = (
                find_user_ticket_from_message(
                    message,
                    request.user,
                )
            )

            # ----------------------------------------------
            # Ticket found
            # ----------------------------------------------

            if ticket:

                links = [
                    {
                        "label": "View My Registrations",
                        "url": reverse(
                            "my_registrations"
                        ),
                    }
                ]

                if ticket.ticket_qr:

                    links.insert(
                        0,
                        {
                            "label": "Download QR Ticket",
                            "url": ticket.ticket_qr.url,
                        },
                    )

                return chatbot_response(
                    (
                        f"Your ticket for "
                        f"{ticket.event.title} "
                        f"is ready. 🎟️\n\n"
                        f"Ticket ID: "
                        f"{ticket.ticket_id()}\n"
                        f"Status: "
                        f"{ticket.get_status_display()}"
                    ),
                    links,
                )

            # ----------------------------------------------
            # Ticket event not identified
            # ----------------------------------------------

            event = find_event_from_message(
                message
            )

            if event:

                return chatbot_response(
                    (
                        f"I couldn't find an active ticket "
                        f"for {event.title}."
                    ),
                    [
                        {
                            "label": "My Registrations",
                            "url": reverse(
                                "my_registrations"
                            ),
                        }
                    ],
                    success=False,
                )

            return chatbot_response(
                (
                    "I couldn't identify which event's "
                    "ticket you want to view. "
                    "Please mention the event name."
                ),
                [
                    {
                        "label": "My Registrations",
                        "url": reverse(
                            "my_registrations"
                        ),
                    }
                ],
            )

        # ==================================================
        # 3. REGISTRATION REQUEST
        # ==================================================

        if detect_registration_request(message):

            event = find_event_from_message(
                message
            )

            # ----------------------------------------------
            # Event not found
            # ----------------------------------------------

            if not event:

                return chatbot_response(
                    (
                        "Sure, I can help you register. "
                        "Please mention the event name so "
                        "I can find the correct event."
                    ),
                    [
                        {
                            "label": "Browse Events",
                            "url": reverse(
                                "event_list"
                            ),
                        }
                    ],
                )

            # ----------------------------------------------
            # Existing registration
            # ----------------------------------------------

            registration = (
                Registration.objects
                .filter(
                    attendee=request.user,
                    event=event,
                )
                .first()
            )

            if registration:

                if (
                    registration.status
                    == Registration.Status.REGISTERED
                ):

                    return chatbot_response(
                        (
                            f"You are already registered "
                            f"for {event.title}. 🎟️"
                        ),
                        [
                            {
                                "label": "My Registrations",
                                "url": reverse(
                                    "my_registrations"
                                ),
                            }
                        ],
                    )

                if (
                    registration.status
                    == Registration.Status.ATTENDED
                ):

                    return chatbot_response(
                        (
                            f"You already attended "
                            f"{event.title}."
                        ),
                        [
                            {
                                "label": "My Registrations",
                                "url": reverse(
                                    "my_registrations"
                                ),
                            }
                        ],
                    )

            # ----------------------------------------------
            # Organizer cannot register for own event
            # ----------------------------------------------

            if event.organizer == request.user:

                return chatbot_response(
                    (
                        "You cannot register for "
                        "your own event."
                    ),
                    [
                        {
                            "label": f"View {event.title}",
                            "url": reverse(
                                "event_detail",
                                kwargs={
                                    "slug": event.slug,
                                },
                            ),
                        }
                    ],
                    success=False,
                )

            # ----------------------------------------------
            # Registration closed
            # ----------------------------------------------

            if not event.is_registration_open:

                return chatbot_response(
                    (
                        f"Registration for "
                        f"{event.title} is "
                        f"currently closed."
                    ),
                    [
                        {
                            "label": f"View {event.title}",
                            "url": reverse(
                                "event_detail",
                                kwargs={
                                    "slug": event.slug,
                                },
                            ),
                        }
                    ],
                    success=False,
                )

            # ----------------------------------------------
            # Registration available
            # ----------------------------------------------

            return chatbot_response(
                (
                    f"{event.title} is available "
                    f"for registration. "
                    f"Click below to register."
                ),
                [
                    {
                        "label": (
                            f"Register for "
                            f"{event.title}"
                        ),
                        "url": reverse(
                            "register_event",
                            kwargs={
                                "slug": event.slug,
                            },
                        ),
                    }
                ],
            )

        # ==================================================
        # 4. NORMAL AI CHAT
        # ==================================================

        try:

            reply = ask_gemini(
                message,
                request.user,
                chat_history,
            )

        except TypeError:

            # Compatibility with an older ask_gemini()
            # that accepts only message + user.
            reply = ask_gemini(
                message,
                request.user,
            )

        # ==================================================
        # VALIDATE GEMINI RESPONSE
        # ==================================================

        if not reply:

            raise RuntimeError(
                "Gemini returned an empty response."
            )

        # ==================================================
        # SAVE CHAT HISTORY
        # ==================================================

        chat_history.append(
            {
                "role": "user",
                "content": message,
            }
        )

        chat_history.append(
            {
                "role": "assistant",
                "content": reply,
            }
        )

        # Keep session small.
        request.session[
            "eventify_chat_history"
        ] = chat_history[-10:]

        request.session.modified = True

        # ==================================================
        # NAVIGATION LINKS
        # ==================================================

        links = get_navigation_links(
            message,
            request.user,
        )

        return chatbot_response(
            reply,
            links,
        )

    # ======================================================
    # GEMINI / EXTERNAL SERVICE FAILURE
    # ======================================================

    except Exception as error:

        error_text = str(error)

        print(
            "Chatbot error:",
            error,
        )

        # ==================================================
        # IMPORTANT:
        # DO NOT RETURN HTTP 429 TO THE FRONTEND.
        #
        # Gemini quota exhaustion is an internal provider
        # problem. Eventify itself should remain functional.
        # ==================================================

        if (
            "429" in error_text
            or "RESOURCE_EXHAUSTED" in error_text
            or "quota" in error_text.lower()
            or "rate limit" in error_text.lower()
            or "too many requests" in error_text.lower()
            or "503" in error_text
            or "service unavailable" in error_text.lower()
            or "500" in error_text
            or "internal" in error_text.lower()
            or "timeout" in error_text.lower()
        ):

            fallback_reply = local_fallback_response(
                message,
                request.user,
            )

            # Save fallback conversation too.
            chat_history.append(
                {
                    "role": "user",
                    "content": message,
                }
            )

            chat_history.append(
                {
                    "role": "assistant",
                    "content": fallback_reply,
                }
            )

            request.session[
                "eventify_chat_history"
            ] = chat_history[-10:]

            request.session.modified = True

            links = get_navigation_links(
                message,
                request.user,
            )

            return chatbot_response(
                fallback_reply,
                links,
            )

        # ==================================================
        # AUTH / PERMISSION FAILURE
        # ==================================================

        if (
            "401" in error_text
            or "403" in error_text
            or "permission" in error_text.lower()
            or "unauthorized" in error_text.lower()
        ):

            fallback_reply = local_fallback_response(
                message,
                request.user,
            )

            return chatbot_response(
                fallback_reply,
                get_navigation_links(
                    message,
                    request.user,
                ),
            )

        # ==================================================
        # ANY OTHER AI FAILURE
        # ==================================================

        fallback_reply = local_fallback_response(
            message,
            request.user,
        )

        return chatbot_response(
            fallback_reply,
            get_navigation_links(
                message,
                request.user,
            ),
        )