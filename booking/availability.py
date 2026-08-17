"""Logic for computing a staff member's open appointment slots on a given date."""
import datetime

from .models import Appointment, StaffAvailability, TimeOff


def get_available_slots(staff, service, target_date, slot_interval_minutes=15):
    """Return a list of datetime.time objects representing valid start times
    for `service` with `staff` on `target_date`, given their weekly
    availability, time off, and existing appointments.
    """
    duration = datetime.timedelta(minutes=service.duration_minutes)
    interval = datetime.timedelta(minutes=slot_interval_minutes)

    # Staff on approved time off that day -> no slots.
    if TimeOff.objects.filter(staff=staff, start_date__lte=target_date, end_date__gte=target_date).exists():
        return []

    day_of_week = target_date.weekday()  # Monday = 0, matches model choices
    availability_blocks = StaffAvailability.objects.filter(staff=staff, day_of_week=day_of_week)
    if not availability_blocks.exists():
        return []

    existing_appointments = list(
        Appointment.objects.filter(staff=staff, date=target_date).exclude(status=Appointment.STATUS_CANCELLED)
    )

    now = datetime.datetime.now()
    slots = []

    for block in availability_blocks:
        cursor = datetime.datetime.combine(target_date, block.start_time)
        block_end = datetime.datetime.combine(target_date, block.end_time)

        while cursor + duration <= block_end:
            candidate_start = cursor.time()
            candidate_end = (cursor + duration).time()

            # Skip slots in the past for today's date.
            if target_date == now.date() and cursor <= now:
                cursor += interval
                continue

            conflict = any(
                appt.start_time < candidate_end and candidate_start < appt.end_time
                for appt in existing_appointments
            )
            if not conflict:
                slots.append(candidate_start)

            cursor += interval

    return sorted(set(slots))
