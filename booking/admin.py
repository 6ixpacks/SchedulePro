from django.contrib import admin

from .models import Appointment, Service, StaffAvailability, TimeOff


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_minutes", "price", "is_active")
    list_filter = ("is_active",)
    filter_horizontal = ("staff",)
    search_fields = ("name",)


@admin.register(StaffAvailability)
class StaffAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("staff", "day_of_week", "start_time", "end_time")
    list_filter = ("day_of_week", "staff")


@admin.register(TimeOff)
class TimeOffAdmin(admin.ModelAdmin):
    list_display = ("staff", "start_date", "end_date", "reason")
    list_filter = ("staff",)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("service", "customer", "staff", "date", "start_time", "end_time", "status")
    list_filter = ("status", "staff", "date")
    search_fields = ("customer__username", "staff__username", "service__name")
    date_hierarchy = "date"
