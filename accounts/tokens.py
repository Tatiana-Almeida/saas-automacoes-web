from rest_framework_simplejwt.tokens import RefreshToken

from .models import BlacklistedToken


def blacklist_refresh_token(refresh_token_str: str):
    try:
        token = RefreshToken(refresh_token_str)
        jti = token.get("jti")
        if jti:
            BlacklistedToken.objects.get_or_create(jti=jti)
            return True
    except Exception:
        pass
    return False


def is_token_blacklisted(jti: str) -> bool:
    return BlacklistedToken.objects.filter(jti=jti).exists()
