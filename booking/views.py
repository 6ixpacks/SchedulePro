import datetime
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from .availability import get_available_slots
from .forms import ServiceForm, StaffAvailabilityForm, TimeOffForm
from .models import Appointment, Service, StaffAvailability, TimeOff


def is_staff_member(user):
    return user.is_authenticated and hasattr(user, "profile") and user.profile.is_staff_member


def home(request):
    services = Service.objects.filter(is_active=True)
    return render(request, "booking/home.html", {"services": services})


@login_required
def dashboard(request):
    if is_staff_member(request.user):
        upcoming = Appointment.objects.filter(
            staff=request.user, date__gte=timezone.localdate()
        ).exclude(status=Appointment.STATUS_CANCELLED)[:20]
        return render(request, "booking/staff_dashboard.html", {"appointments": upcoming})

    upcoming = Appointment.objects.filter(
        customer=request.user, date__gte=timezone.localdate()
    ).exclude(status=Appointment.STATUS_CANCELLED)
    past = Appointment.objects.filter(customer=request.user, date__lt=timezone.localdate())
    return render(request, "booking/customer_dashboard.html", {"upcoming": upcoming, "past": past})


@login_required
def book_appointment(request):
    services = Service.objects.filter(is_active=True).prefetch_related("staff")

    if request.method == "POST":
        service_id = request.POST.get("service")
        staff_id = request.POST.get("staff")
        date_str = request.POST.get("date")
        time_str = request.POST.get("time")
        notes = request.POST.get("notes", "")

        service = get_object_or_404(Service, pk=service_id, is_active=True)
        staff = get_object_or_404(User, pk=staff_id)

        try:
            appt_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            start_time = datetime.datetime.strptime(time_str, "%H:%M").time()
        except (TypeError, ValueError):
            messages.error(request, "Invalid date or time selected.")
            return redirect("booking:book_appointment")

        end_dt = datetime.datetime.combine(appt_date, start_time) + datetime.timedelta(
            minutes=service.duration_minutes
        )

        # Re-validate the slot is still open (protects against double-booking races).
        valid_slots = get_available_slots(staff, service, appt_date)
        if start_time not in valid_slots:
            messages.error(request, "Sorry, that slot is no longer available. Please pick another time.")
            return redirect("booking:book_appointment")

        appointment = Appointment(
            customer=request.user,
            staff=staff,
            service=service,
            date=appt_date,
            start_time=start_time,
            end_time=end_dt.time(),
            notes=notes,
            status=Appointment.STATUS_PENDING,
        )
        try:
            appointment.full_clean()
        except ValidationError as e:
            messages.error(request, " ".join(e.messages))
            return redirect("booking:book_appointment")

        appointment.save()
        messages.success(request, "Your appointment request has been booked!")
        return redirect("booking:appointment_detail", pk=appointment.pk)

    return render(request, "booking/book_appointment.html", {"services": services})


@login_required
@require_GET
def api_staff_for_service(request):
    service_id = request.GET.get("service_id")
    service = get_object_or_404(Service, pk=service_id)
    staff = [{"id": s.id, "name": s.get_full_name() or s.username} for s in service.staff.all()]
    return JsonResponse({"staff": staff})


@login_required
@require_GET
def api_available_slots(request):
    service_id = request.GET.get("service_id")
    staff_id = request.GET.get("staff_id")
    date_str = request.GET.get("date")

    try:
        service = Service.objects.get(pk=service_id)
        staff = User.objects.get(pk=staff_id)
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except (Service.DoesNotExist, User.DoesNotExist, TypeError, ValueError):
        return JsonResponse({"slots": []})

    slots = get_available_slots(staff, service, target_date)
    return JsonResponse({"slots": [t.strftime("%H:%M") for t in slots]})


@login_required
def appointment_detail(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.user != appointment.customer and request.user != appointment.staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to view that appointment.")
        return redirect("booking:dashboard")
    return render(request, "booking/appointment_detail.html", {"appointment": appointment})


@login_required
def appointment_cancel(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.user != appointment.customer and request.user != appointment.staff:
        messages.error(request, "You don't have permission to cancel that appointment.")
        return redirect("booking:dashboard")

    if request.method == "POST":
        appointment.status = Appointment.STATUS_CANCELLED
        appointment.save(update_fields=["status", "updated_at"])
        messages.success(request, "Appointment cancelled.")
        return redirect("booking:dashboard")

    return render(request, "booking/appointment_cancel_confirm.html", {"appointment": appointment})


@login_required
def appointment_confirm(request, pk):
    """Staff marks a pending appointment as confirmed or completed."""
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.user != appointment.staff:
        messages.error(request, "Only the assigned staff member can update this appointment.")
        return redirect("booking:dashboard")

    new_status = request.POST.get("status")
    if new_status in dict(Appointment.STATUS_CHOICES):
        appointment.status = new_status
        appointment.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Appointment marked as {appointment.get_status_display()}.")
    return redirect("booking:dashboard")


# ---- Staff availability management ----

@login_required
@user_passes_test(is_staff_member)
def manage_availability(request):
    if request.method == "POST":
        form = StaffAvailabilityForm(request.POST)
        if form.is_valid():
            slot = form.save(commit=False)
            slot.staff = request.user
            try:
                slot.full_clean()
                slot.save()
                messages.success(request, "Availability added.")
            except ValidationError as e:
                messages.error(request, " ".join(e.messages))
            return redirect("booking:manage_availability")
    else:
        form = StaffAvailabilityForm()

    slots = StaffAvailability.objects.filter(staff=request.user)
    time_off = TimeOff.objects.filter(staff=request.user)
    time_off_form = TimeOffForm()
    return render(
        request,
        "booking/manage_availability.html",
        {"form": form, "slots": slots, "time_off": time_off, "time_off_form": time_off_form},
    )


@login_required
@user_passes_test(is_staff_member)
def delete_availability(request, pk):
    slot = get_object_or_404(StaffAvailability, pk=pk, staff=request.user)
    if request.method == "POST":
        slot.delete()
        messages.success(request, "Availability removed.")
    return redirect("booking:manage_availability")


@login_required
@user_passes_test(is_staff_member)
def add_time_off(request):
    if request.method == "POST":
        form = TimeOffForm(request.POST)
        if form.is_valid():
            time_off = form.save(commit=False)
            time_off.staff = request.user
            try:
                time_off.full_clean()
                time_off.save()
                messages.success(request, "Time off added.")
            except ValidationError as e:
                messages.error(request, " ".join(e.messages))
    return redirect("booking:manage_availability")


@login_required
@user_passes_test(is_staff_member)
def delete_time_off(request, pk):
    time_off = get_object_or_404(TimeOff, pk=pk, staff=request.user)
    if request.method == "POST":
        time_off.delete()
        messages.success(request, "Time off removed.")
    return redirect("booking:manage_availability")


# ---- Admin: service management ----

def is_business_admin(user):
    return user.is_authenticated and (
        user.is_superuser or (hasattr(user, "profile") and user.profile.role == "admin")
    )


@login_required
@user_passes_test(is_business_admin)
def manage_services(request):
    if request.method == "POST":
        form = ServiceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Service saved.")
            return redirect("booking:manage_services")
    else:
        form = ServiceForm()
    services = Service.objects.all()
    return render(request, "booking/manage_services.html", {"form": form, "services": services})


@login_required
@user_passes_test(is_business_admin)
def edit_service(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Service updated.")
            return redirect("booking:manage_services")
    else:
        form = ServiceForm(instance=service)
    return render(request, "booking/manage_services.html", {"form": form, "services": Service.objects.all(), "editing": service})
