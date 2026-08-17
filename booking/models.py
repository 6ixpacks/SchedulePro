import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse


class Service(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(help_text="How long this service takes, in minutes.")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)
    staff = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="services_offered",
        limit_choices_to={"profile__role__in": ["staff", "admin"]},
        blank=True,
        help_text="Staff members who can perform this service.",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.duration_minutes} min)"


class StaffAvailability(models.Model):
    """A weekly recurring block of time a staff member is available for bookings."""

    MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY = range(7)
    DAY_CHOICES = [
        (MONDAY, "Monday"),
        (TUESDAY, "Tuesday"),
        (WEDNESDAY, "Wednesday"),
        (THURSDAY, "Thursday"),
        (FRIDAY, "Friday"),
        (SATURDAY, "Saturday"),
        (SUNDAY, "Sunday"),
    ]

    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availability_slots",
        limit_choices_to={"profile__role__in": ["staff", "admin"]},
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["staff", "day_of_week", "start_time"]
        unique_together = ("staff", "day_of_week", "start_time", "end_time")
        verbose_name_plural = "Staff availability"

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time.")

    def __str__(self):
        return f"{self.staff} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class TimeOff(models.Model):
    """Blocks out a staff member's availability for a specific date range (holiday, sick day, etc)."""

    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="time_off")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["start_date"]

    def clean(self):
        if self.start_date > self.end_date:
            raise ValidationError("Start date must be on or before end date.")

    def __str__(self):
        return f"{self.staff} off {self.start_date} - {self.end_date}"


class Appointment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_COMPLETED, "Completed"),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appointments_as_customer"
    )
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appointments_as_staff"
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="appointments")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "start_time"]

    def __str__(self):
        return f"{self.service.name} - {self.customer} with {self.staff} on {self.date} {self.start_time}"

    def get_absolute_url(self):
        return reverse("booking:appointment_detail", args=[self.pk])

    @property
    def start_datetime(self):
        return datetime.datetime.combine(self.date, self.start_time)

    @property
    def end_datetime(self):
        return datetime.datetime.combine(self.date, self.end_time)

    def overlaps(self, other_start, other_end):
        return self.start_time < other_end and other_start < self.end_time

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time.")

        conflict_qs = Appointment.objects.filter(
            staff=self.staff, date=self.date
        ).exclude(status=self.STATUS_CANCELLED)
        if self.pk:
            conflict_qs = conflict_qs.exclude(pk=self.pk)

        for appt in conflict_qs:
            if appt.overlaps(self.start_time, self.end_time):
                raise ValidationError(
                    f"{self.staff} already has an appointment from {appt.start_time} to {appt.end_time} on {self.date}."
                )
