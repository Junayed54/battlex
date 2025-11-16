import uuid
from uuid import UUID
from django.utils.timezone import now
from .models import UserOpenAccount, UserActivityLog
from user_agents import parse
from rest_framework.authentication import BaseAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import UntypedToken
from jwt.exceptions import InvalidTokenError
from django.conf import settings
import jwt

class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_account = None

        if request.user.is_authenticated:
            # Link to registered user’s open account (if one exists or create one)
            user_account, _ = UserOpenAccount.objects.get_or_create(
                user=request.user,
                defaults={
                    "id": str(uuid.uuid4()),
                    "ip_address": self.get_client_ip(request),
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                    "device": "Unknown",
                    "browser": "Unknown",
                    "os": "Unknown",
                    "first_seen_at": now(),
                    "last_seen_at": now(),
                    "status": "active",
                }
            )
        else:
            # Try to get guest info from Authorization header
            guest_id = self.extract_guest_id_from_jwt(request)
            if guest_id:
                user_account, _ = UserOpenAccount.objects.get_or_create(
                    id=guest_id,
                    defaults={
                        "ip_address": self.get_client_ip(request),
                        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                        "device": "Unknown",
                        "browser": "Unknown",
                        "os": "Unknown",
                        "first_seen_at": now(),
                        "last_seen_at": now(),
                        "status": "active",
                    }
                )
            else:
                # Generate a unique guest ID based on the IP address (only for new guests)
                guest_id = self.generate_guest_id(request)
                user_account, _ = UserOpenAccount.objects.get_or_create(
                    id=guest_id,
                    defaults={
                        "ip_address": self.get_client_ip(request),
                        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                        "device": "Unknown",
                        "browser": "Unknown",
                        "os": "Unknown",
                        "first_seen_at": now(),
                        "last_seen_at": now(),
                        "status": "active",
                    }
                )

        if user_account:
            user_account.last_seen_at = now()
            user_account.save(update_fields=["last_seen_at"])

            # Log activity
            UserActivityLog.objects.create(
                user=user_account,
                url=request.path,
                timestamp=now()
            )

        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get("REMOTE_ADDR")

    def extract_guest_id_from_jwt(self, request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split("Bearer ")[1].strip()
        try:
            decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            if decoded.get("is_guest") is True and decoded.get("open_account_id"):
                return decoded["open_account_id"]
        except jwt.ExpiredSignatureError:
            # Optional: log or return a specific error
            return None
        except jwt.DecodeError:
            return None
        except jwt.InvalidTokenError:
            return None

    def generate_guest_id(self, request):
        """Generate a unique guest ID based on the IP address."""
        ip_address = self.get_client_ip(request)
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, ip_address))  # Use IP to generate unique guest ID

class GuestAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            print("No Authorization header found.")
            return None  # No token, no guest authentication

        try:
            token = auth_header.split(' ')[1]  # Extract token after "Bearer"
            print(f"Processing guest token: {token}")

            guest_account = UserOpenAccount.objects.filter(id=token, status='active').first()

            if not guest_account:
                print(f"Error: No active guest account found for token: {token}")
                raise AuthenticationFailed("Invalid or inactive guest token")

            print(f"Authenticated guest: {guest_account.id}")
            return (guest_account, None)

        except Exception as e:
            print(f"Authentication failed: {str(e)}")
            raise AuthenticationFailed(f"Given token not valid for any token type: {str(e)}")



class CombinedJWTOrGuestAuthentication(BaseAuthentication):
    def authenticate(self, request):
        jwt_auth = JWTAuthentication()

        try:
            user_auth = jwt_auth.authenticate(request)
            if user_auth is not None:
                user, _ = user_auth
                request.user = user
                return (user, None)
        except AuthenticationFailed:
            pass

        # Guest Authentication
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                if decoded.get("is_guest") is True and decoded.get("open_account_id"):
                    guest_id = decoded["open_account_id"]
                    guest_user = UserOpenAccount.objects.filter(id=guest_id, status='active').first()
                    if guest_user:
                        request.user = guest_user
                        return (guest_user, None)
            except (jwt.ExpiredSignatureError, jwt.DecodeError, jwt.InvalidTokenError):
                pass

        return None