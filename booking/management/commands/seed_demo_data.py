from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import Profile
from booking.models import Service, StaffAvailability


class Command(BaseCommand):
    help = "Create a superuser, two demo staff members, and a few services so you can try the app immediately."

    def handle(self, *args, **options):
        if not User.objects.filter(username="admin").exists():
            admin = User.objects.create_superuser("admin", "admin@example.com", "admin12345")
            admin.profile.role = Profile.ROLE_ADMIN
            admin.profile.save()
            self.stdout.write(self.style.SUCCESS("Created superuser 'admin' / password 'admin12345'"))
        else:
            admin = User.objects.get(username="admin")

        staff_data = [
            ("jane", "Jane", "Doe", "Hair Stylist"),
            ("sam", "Sam", "Okoye", "Barber"),
        ]
        staff_members = []
        for username, first, last, title in staff_data:
            user, created = User.objects.get_or_create(
                username=username, defaults={"first_name": first, "last_name": last, "email": f"{username}@example.com"}
            )
            if created:
                user.set_password("staffpass123")
                user.save()
            user.profile.role = Profile.ROLE_STAFF
            user.profile.bio = title
            user.profile.save()
            staff_members.append(user)

            # Mon-Fri 9am-5pm availability
            for day in range(0, 5):
                StaffAvailability.objects.get_or_create(
                    staff=user, day_of_week=day, start_time="09:00", end_time="17:00"
                )

        services_data = [
            ("Haircut", "Classic haircut and style.", 30, 5000),
            ("Hair Coloring", "Full color treatment.", 90, 15000),
            ("Beard Trim", "Shape-up and trim.", 20, 3000),
        ]
        for name, desc, duration, price in services_data:
            service, _ = Service.objects.get_or_create(
                name=name, defaults={"description": desc, "duration_minutes": duration, "price": price}
            )
            service.staff.set(staff_members)

        self.stdout.write(self.style.SUCCESS("Demo data ready. Staff logins: jane / sam, password 'staffpass123'."))
