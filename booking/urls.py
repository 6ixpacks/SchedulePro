from django.urls import path

from . import views

app_name = "booking"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("book/", views.book_appointment, name="book_appointment"),
    path("appointment/<int:pk>/", views.appointment_detail, name="appointment_detail"),
    path("appointment/<int:pk>/cancel/", views.appointment_cancel, name="appointment_cancel"),
    path("appointment/<int:pk>/update-status/", views.appointment_confirm, name="appointment_confirm"),
    path("api/staff-for-service/", views.api_staff_for_service, name="api_staff_for_service"),
    path("api/available-slots/", views.api_available_slots, name="api_available_slots"),
    path("availability/", views.manage_availability, name="manage_availability"),
    path("availability/<int:pk>/delete/", views.delete_availability, name="delete_availability"),
    path("time-off/add/", views.add_time_off, name="add_time_off"),
    path("time-off/<int:pk>/delete/", views.delete_time_off, name="delete_time_off"),
    path("services/manage/", views.manage_services, name="manage_services"),
    path("services/manage/<int:pk>/", views.edit_service, name="edit_service"),
]
