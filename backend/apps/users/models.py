import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class EmailVerificationToken(models.Model):
    """Simple email verification token model.

    Tokens are single-use and expire after a configurable period.
    This model intentionally keeps fields minimal for an MVP flow.
    """

    user = models.ForeignKey(
        "users.User", related_name="email_tokens", on_delete=models.CASCADE
    )
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    used = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["token"])]

    def is_expired(self, hours=48):
        return timezone.now() > (self.created_at + timezone.timedelta(hours=hours))

    def mark_used(self):
        self.used = True
        self.save(update_fields=["used"])


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, nome_completo, password, **extra_fields):
        if not email:
            raise ValueError("O email deve ser informado")
        email = self.normalize_email(email)
        user = self.model(email=email, nome_completo=nome_completo, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self,
        email=None,
        password=None,
        nome_completo=None,
        **extra_fields,
    ):
        # Support callers that provide `username` instead of `email`.
        username = extra_fields.pop("username", None)
        if not email:
            if username:
                email = f"{username}@noemail.invalid"
            else:
                raise ValueError("Users must have an email address or username")

        email = self.normalize_email(email)
        nome = nome_completo or extra_fields.pop("nome_completo", "") or ""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, nome, password, **extra_fields)

    def create_superuser(
        self,
        email=None,
        password=None,
        nome_completo=None,
        **extra_fields,
    ):
        username = extra_fields.pop("username", None)
        if not email:
            if username:
                email = f"{username}@noemail.invalid"
            else:
                raise ValueError("Superuser must have an email or username")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(
            email, nome_completo or "Admin", password, **extra_fields
        )


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("email address", unique=True)
    nome_completo = models.CharField("nome completo", max_length=255)
    telefone = models.CharField("telefone", max_length=50, blank=True, null=True)
    empresa = models.CharField("empresa", max_length=255, blank=True, null=True)
    pais = models.CharField("pais", max_length=100, blank=True, null=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome_completo"]

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def get_full_name(self):
        return self.nome_completo

    def get_short_name(self):
        return self.nome_completo.split(" ")[0] if self.nome_completo else self.email

    def __str__(self):
        return self.email
