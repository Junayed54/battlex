from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils.timezone import now
from .models import UserOpenAccount

@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    ip_address = request.META.get("REMOTE_ADDR", "")
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    device = request.headers.get("Device", "Unknown")
    browser = request.headers.get("Browser", "Unknown")
    os = request.headers.get("OS", "Unknown")

    UserOpenAccount.objects.update_or_create(
        id=str(user.id),
        defaults={
            "ip_address": ip_address,
            "user_agent": user_agent,
            "device": device,
            "browser": browser,
            "os": os,
            "last_seen_at": now(),
            "status": "active",
        },
    )

@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    try:
        user_account = UserOpenAccount.objects.get(id=str(user.id))
        user_account.status = "limited"  # Mark as limited on logout
        user_account.save(update_fields=["status"])
    except UserOpenAccount.DoesNotExist:
        pass
