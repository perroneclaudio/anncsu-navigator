import logging
import os

import ldap

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


logger = logging.getLogger(__name__)

User = get_user_model()


def env_bool(name, default=False):
    value = os.environ.get(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def normalize_username(username):
    """
    Accetta:
      username
      DOMINIO\\username
      username@dominio

    e restituisce il solo username applicativo.
    """

    username = (username or "").strip()

    if "\\" in username:
        username = username.rsplit("\\", 1)[-1]

    if "@" in username:
        username = username.split("@", 1)[0]

    return username.strip()


class LocalUserBackend(ModelBackend):
    """
    Autentica esclusivamente utenti auth_type=LOCAL.
    """

    def authenticate(
        self,
        request,
        username=None,
        password=None,
        **kwargs,
    ):
        username = normalize_username(
            username or kwargs.get(User.USERNAME_FIELD)
        )

        if not username or not password:
            return None

        try:
            user = User.objects.get(
                username__iexact=username
            )
        except User.DoesNotExist:
            User().set_password(password)
            return None

        if user.auth_type != User.AuthType.LOCAL:
            return None

        if (
            user.check_password(password)
            and self.user_can_authenticate(user)
        ):
            return user

        return None


class LDAPUserBackend(ModelBackend):
    """
    Autentica esclusivamente utenti locali marcati auth_type=LDAP.

    La password viene verificata direttamente su Active Directory.

    Il server LDAP secondario viene usato solo in caso di problemi
    di comunicazione con il primario.

    In caso di credenziali errate NON viene eseguito un secondo bind
    sul DC di backup, evitando di raddoppiare i tentativi password AD.
    """

    def authenticate(
        self,
        request,
        username=None,
        password=None,
        **kwargs,
    ):
        if not env_bool("LDAP_ENABLED", False):
            return None

        username = normalize_username(
            username or kwargs.get(User.USERNAME_FIELD)
        )

        if not username or not password:
            return None

        try:
            user = User.objects.get(
                username__iexact=username
            )
        except User.DoesNotExist:
            return None

        if user.auth_type != User.AuthType.LDAP:
            return None

        if not self.user_can_authenticate(user):
            return None

        bind_template = os.environ.get(
            "LDAP_USER_BIND_TEMPLATE",
            "{username}",
        )

        bind_username = bind_template.format(
            username=username
        )

        timeout = int(
            os.environ.get(
                "LDAP_CONNECT_TIMEOUT",
                "5",
            )
        )

        servers = [
            os.environ.get("LDAP_SERVER_URI", "").strip(),
            os.environ.get(
                "LDAP_SERVER_URI_BACKUP",
                "",
            ).strip(),
        ]

        servers = [
            server
            for server in servers
            if server
        ]

        for index, server in enumerate(servers):
            connection = None

            try:
                logger.info(
                    "Tentativo autenticazione LDAP su server %s",
                    index + 1,
                )

                connection = ldap.initialize(server)

                connection.set_option(
                    ldap.OPT_PROTOCOL_VERSION,
                    ldap.VERSION3,
                )

                connection.set_option(
                    ldap.OPT_NETWORK_TIMEOUT,
                    timeout,
                )

                try:
                    connection.set_option(
                        ldap.OPT_REFERRALS,
                        0,
                    )
                except (ldap.LDAPError, ValueError):
                    pass

                connection.simple_bind_s(
                    bind_username,
                    password,
                )

                logger.info(
                    "Autenticazione LDAP riuscita per %s",
                    username,
                )

                return user

            except ldap.INVALID_CREDENTIALS:
                logger.warning(
                    "Credenziali LDAP non valide per %s",
                    username,
                )

                # IMPORTANTISSIMO:
                # non provare il secondo DC con la stessa password errata.
                return None

            except (
                ldap.SERVER_DOWN,
                ldap.TIMEOUT,
            ) as exc:
                logger.warning(
                    "Server LDAP %s non disponibile: %s",
                    index + 1,
                    exc,
                )

                # In questo caso soltanto passiamo al backup.
                continue

            except ldap.LDAPError as exc:
                logger.exception(
                    "Errore LDAP sul server %s: %s",
                    index + 1,
                    exc,
                )

                # Errore LDAP non classificato:
                # non rischiamo altri bind inutili.
                return None

            finally:
                if connection is not None:
                    try:
                        connection.unbind_s()
                    except ldap.LDAPError:
                        pass

        logger.error(
            "Nessun server LDAP disponibile per %s",
            username,
        )

        return None
