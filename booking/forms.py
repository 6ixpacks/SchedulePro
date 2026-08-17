import datetime

from django import forms

from .models import Appointment, Service, StaffAvailability, TimeOff


class BookingStep1Form(forms.Form):
    """Choose a service and staff member."""

    service = forms.ModelChoiceField(queryset=Service.objects.filter(is_active=True))
    staff = forms.ModelChoiceField(queryset=None, label="Preferred staff member")
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["staff"].queryset = self.fields["staff"].queryset  # placeholder, set below

    def clean_date(self):
        date = self.cleaned_data["date"]
        if date < datetime.date.today():
            raise forms.ValidationError("Please choose a date in the future.")
        return date


class AppointmentNotesForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Anything the staff should know?"})}


class StaffAvailabilityForm(forms.ModelForm):
    class Meta:
        model = StaffAvailability
        fields = ["day_of_week", "start_time", "end_time"]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }


class TimeOffForm(forms.ModelForm):
    class Meta:
        model = TimeOff
        fields = ["start_date", "end_date", "reason"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "description", "duration_minutes", "price", "is_active", "staff"]
        widgets = {"staff": forms.CheckboxSelectMultiple}
