import os
from django.core.management.base import BaseCommand
from accounts.models import User, UserRole, UserStatus

class Command(BaseCommand):
    help = "Creates or updates initial superuser/admin safely from environment variables."

    def handle(self, *args, **options):
        username = os.getenv("ADMIN_USERNAME", "admin")
        email = os.getenv("ADMIN_EMAIL", "admin@vau.edu.vn")
        password = os.getenv("ADMIN_PASSWORD")

        if not password:
            self.stdout.write(self.style.WARNING("ADMIN_PASSWORD không được cấu hình trong môi trường. Bỏ qua tạo admin."))
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'role': UserRole.ADMIN,
                'status': UserStatus.ACTIVE,
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Quản trị viên',
                'last_name': 'HVHK'
            }
        )

        user.set_password(password)
        user.role = UserRole.ADMIN
        user.status = UserStatus.ACTIVE
        user.is_staff = True
        user.is_superuser = True
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Đã tạo thành công tài khoản Quản trị viên: {username}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Đã cập nhật mật khẩu tài khoản Quản trị viên: {username}"))
