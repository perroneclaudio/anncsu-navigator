from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class AuthType(models.TextChoices):
        LOCAL = "LOCAL", "Locale"
        LDAP = "LDAP", "LDAP / Active Directory"

    auth_type = models.CharField(
        "Tipo autenticazione",
        max_length=10,
        choices=AuthType.choices,
        default=AuthType.LOCAL,
        db_index=True,
    )

    def __str__(self):
        full_name = self.get_full_name().strip()
        if full_name:
            return f"{full_name} ({self.username})"
        return self.username
