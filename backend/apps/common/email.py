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


def send_invoice(invoice):
    lines = "\n".join(
        f"  {line.description} x {line.quantity}: {invoice.currency} {line.line_total}"
        for line in invoice.lines.all()
    )
    send_mail(
        subject=f"Invoice {invoice.number} from Brightloop Software",
        message=(
            f"Hello {invoice.customer_name},\n\n"
            f"Invoice {invoice.number} for {invoice.period_start} to {invoice.period_end}:\n\n{lines}\n\n"
            f"Total: {invoice.currency} {invoice.total}\n"
            f"Due by: {invoice.due_date}\n\n"
            f"View it in your portal: {settings.FRONTEND_URL}/portal"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invoice.customer_email],
    )
