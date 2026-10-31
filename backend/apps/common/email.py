from django.conf import settings
from django.core.mail import send_mail


def send_password_reset(user, uid, token):
    link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"
    send_mail(
        subject="Reset your Concord password",
        message=(
            f"Hello {user.name or user.email},\n\n"
            f"Use this link to choose a new password. It works once and expires in one hour:\n{link}\n\n"
            "If you didn't ask for this, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
