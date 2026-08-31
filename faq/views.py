from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from events.models import Event

from .forms import FAQForm
from .models import FAQ


@login_required
def faq_list(request, event_id):
    """
    Display and manage FAQs for an organizer's event.
    """

    event = get_object_or_404(
        Event,
        id=event_id,
        organizer=request.user,
    )

    faqs = event.faqs.all()

    return render(
        request,
        "faq/faq_list.html",
        {
            "event": event,
            "faqs": faqs,
        },
    )


@login_required
def faq_create(request, event_id):
    """
    Create a new FAQ for an organizer's event.
    """

    event = get_object_or_404(
        Event,
        id=event_id,
        organizer=request.user,
    )

    if request.method == "POST":

        form = FAQForm(request.POST)

        if form.is_valid():

            faq = form.save(
                commit=False,
            )

            faq.event = event

            faq.save()

            messages.success(
                request,
                "FAQ added successfully.",
            )

            return redirect(
                "faq_list",
                event_id=event.id,
            )

    else:

        form = FAQForm()

    return render(
        request,
        "faq/faq_form.html",
        {
            "form": form,
            "event": event,
            "page_title": "Add FAQ",
        },
    )


@login_required
def faq_update(request, faq_id):
    """
    Update an FAQ belonging to the logged-in organizer.
    """

    faq = get_object_or_404(
        FAQ,
        id=faq_id,
        event__organizer=request.user,
    )

    if request.method == "POST":

        form = FAQForm(
            request.POST,
            instance=faq,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "FAQ updated successfully.",
            )

            return redirect(
                "faq_list",
                event_id=faq.event.id,
            )

    else:

        form = FAQForm(
            instance=faq,
        )

    return render(
        request,
        "faq/faq_form.html",
        {
            "form": form,
            "event": faq.event,
            "page_title": "Edit FAQ",
        },
    )


@login_required
def faq_delete(request, faq_id):
    """
    Delete an FAQ belonging to the logged-in organizer.
    """

    faq = get_object_or_404(
        FAQ,
        id=faq_id,
        event__organizer=request.user,
    )

    event_id = faq.event.id

    if request.method == "POST":

        faq.delete()

        messages.success(
            request,
            "FAQ deleted successfully.",
        )

    return redirect(
        "faq_list",
        event_id=event_id,
    )