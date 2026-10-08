import time
import uuid
from pathlib import Path

import jwt
import requests


class PDNDError(Exception):
    pass


class PDNDConfigurationError(PDNDError):
    pass


class PDNDAuthenticationError(PDNDError):
    pass


class PDNDClient:
    def __init__(self, configurazione):
        self.config = configurazione

    def _validate_configuration(self):
        required = {
            "client_id": self.config.client_id,
            "purpose_id": self.config.purpose_id,
            "kid": self.config.kid,
            "audience_assertion": self.config.audience_assertion,
            "url_token": self.config.url_token,
            "percorso_chiave_privata": self.config.percorso_chiave_privata,
        }

        missing = [
            key
            for key, value in required.items()
            if not value
        ]

        if missing:
            raise PDNDConfigurationError(
                "Configurazione PDND incompleta: "
                + ", ".join(missing)
            )

        key_path = Path(
            self.config.percorso_chiave_privata
        )

        if not key_path.is_file():
            raise PDNDConfigurationError(
                f"Chiave privata non trovata: {key_path}"
            )

    def _read_private_key(self):
        self._validate_configuration()

        return Path(
            self.config.percorso_chiave_privata
        ).read_text()

    def create_client_assertion(self):
        private_key = self._read_private_key()

        now = int(time.time())

        issuer = (
            self.config.iss
            or self.config.client_id
        )

        subject = (
            self.config.sub
            or self.config.client_id
        )

        headers = {
            "kid": self.config.kid,
            "alg": self.config.algoritmo_jwt,
            "typ": self.config.tipo_jwt,
        }

        payload = {
            "iss": issuer,
            "sub": subject,
            "aud": self.config.audience_assertion,
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + 600,
            "purposeId": self.config.purpose_id,
        }

        return jwt.encode(
            payload,
            private_key,
            algorithm=self.config.algoritmo_jwt,
            headers=headers,
        )

    def get_access_token(self):
        assertion = self.create_client_assertion()

        data = {
            "client_id": self.config.client_id,
            "client_assertion": assertion,
            "client_assertion_type": (
                "urn:ietf:params:oauth:"
                "client-assertion-type:jwt-bearer"
            ),
            "grant_type": "client_credentials",
        }

        try:
            response = requests.post(
                self.config.url_token,
                data=data,
                timeout=self.config.timeout,
            )
        except requests.RequestException as exc:
            raise PDNDAuthenticationError(
                f"Errore di connessione al token endpoint PDND: {exc}"
            ) from exc

        if response.status_code != 200:
            detail = response.text[:1000]

            raise PDNDAuthenticationError(
                "Impossibile ottenere il voucher PDND. "
                f"HTTP {response.status_code}: {detail}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise PDNDAuthenticationError(
                "Risposta non JSON dal token endpoint PDND."
            ) from exc

        token = payload.get("access_token")

        if not token:
            raise PDNDAuthenticationError(
                "La risposta PDND non contiene access_token."
            )

        return token
