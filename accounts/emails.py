from django.conf import settings
from django.core.mail import send_mail


def send_verification_email(user, token):
    subject = "Confirm your account"
    link = f"/api/v1/accounts/confirm-email/?token={token.token}"
    body = f"Olá {getattr(user, 'nome_completo', '')}\n\nPlease confirm your email by visiting: {link}\n"
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])


def send_password_reset_email(user, token):
    subject = "Password reset"
    link = f"/api/v1/accounts/reset-password/confirm/?token={token.token}"
    body = f"Olá {getattr(user, 'nome_completo', '')}\n\nReset your password: {link}\n"
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
