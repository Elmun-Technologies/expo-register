from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from events.models import Event
from registrations.models import Registration

from .forms import FeedbackForm
from .models import Feedback


@login_required
def submit_feedback(request, event_id):

    event = get_object_or_404(
        Event,
        pk=event_id,
    )

    registration = Registration.objects.filter(
        attendee=request.user,
        event=event,
    ).first()

    # ==========================================
    # ELIGIBILITY CHECK
    # ==========================================

    if not registration:
        messages.error(
            request,
            "You can only review an event you registered for.",
        )

        return redirect(
            event.get_absolute_url()
        )

    if registration.status != Registration.Status.ATTENDED:
        messages.error(
            request,
            "You can submit feedback only after attending the event.",
        )

        return redirect(
            event.get_absolute_url()
        )

    if not registration.checked_in:
        messages.error(
            request,
            "Feedback is available after event check-in.",
        )

        return redirect(
            event.get_absolute_url()
        )

    # ==========================================
    # PREVENT DUPLICATE FEEDBACK
    # ==========================================

    existing_feedback = Feedback.objects.filter(
        event=event,
        attendee=request.user,
    ).first()

    if existing_feedback:
        messages.info(
            request,
            "You have already submitted feedback for this event.",
        )

        return redirect(
            event.get_absolute_url()
        )

    # ==========================================
    # SUBMISSION
    # ==========================================

    if request.method == "POST":

        form = FeedbackForm(
            request.POST,
        )

        if form.is_valid():

            feedback = form.save(
                commit=False,
            )

            feedback.event = event
            feedback.attendee = request.user

            try:

                feedback.save()

            except IntegrityError:

                messages.info(
                    request,
                    "You have already submitted feedback for this event.",
                )

                return redirect(
                    event.get_absolute_url()
                )

            messages.success(
                request,
                "Thank you! Your feedback has been submitted.",
            )

            return redirect(
                event.get_absolute_url()
            )

    else:

        form = FeedbackForm()

    return render(
        request,
        "feedback/submit_feedback.html",
        {
            "event": event,
            "form": form,
        },
    )