from datetime import timedelta

import requests

from django.db.models import F
from django.utils import timezone

from core.models import (
    CacheANNCSU,
    ConfigurazionePDND,
    ContatoreRichiesteANNCSU,
)

from core.services.pdnd import (
    PDNDClient,
    PDNDConfigurationError,
    PDNDError,
)


class ANNCSUError(Exception):
    pass


class ANNCSUConfigurationError(ANNCSUError):
    pass


class ANNCSUClient:
    def __init__(self):
        config = (
            ConfigurazionePDND.objects
            .filter(attiva=True)
            .order_by("pk")
            .first()
        )

        if config is None:
            raise ANNCSUConfigurationError(
                "Nessuna configurazione PDND attiva."
            )

        self.config = config
        self.pdnd = PDNDClient(config)

    # ------------------------------------------------------------------
    # CACHE
    # ------------------------------------------------------------------

    def _cache_get(self, chiave):
        now = timezone.now()

        item = (
            CacheANNCSU.objects
            .filter(
                chiave=chiave,
                scade_il__gt=now,
            )
            .first()
        )

        if item is None:
            return None

        CacheANNCSU.objects.filter(
            pk=item.pk
        ).update(
            numero_hit=F("numero_hit") + 1,
            ultimo_accesso=now,
        )

        return item.risposta_json

    def _cache_set(
        self,
        *,
        tipo,
        chiave,
        richiesta,
        risposta,
        ttl_ore,
    ):
        now = timezone.now()

        CacheANNCSU.objects.update_or_create(
            chiave=chiave,
            defaults={
                "tipo": tipo,
                "richiesta_json": richiesta,
                "risposta_json": risposta,
                "scade_il": now + timedelta(
                    hours=max(1, int(ttl_ore))
                ),
                "ultimo_accesso": now,
                "numero_hit": 0,
            },
        )

        return risposta

    # ------------------------------------------------------------------
    # HTTP ANNCSU
    # ------------------------------------------------------------------

    def _post(self, endpoint, payload):
        """
        Effettua realmente una chiamata esterna ANNCSU.

        La cache viene quindi controllata PRIMA di arrivare qui.
        """

        try:
            token = self.pdnd.get_access_token()

        except PDNDConfigurationError as exc:
            raise ANNCSUConfigurationError(
                str(exc)
            ) from exc

        except PDNDError as exc:
            raise ANNCSUError(
                str(exc)
            ) from exc

        url = (
            self.config.base_url_eservice.rstrip("/")
            + "/"
            + endpoint.lstrip("/")
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Da questo punto stiamo realmente per consumare
        # una chiamata verso l'e-service ANNCSU.
        oggi = timezone.localdate()

        contatore, _ = ContatoreRichiesteANNCSU.objects.get_or_create(
            giorno=oggi,
            defaults={
                "richieste": 0,
            },
        )

        ContatoreRichiesteANNCSU.objects.filter(
            pk=contatore.pk
        ).update(
            richieste=F("richieste") + 1,
            ultima_richiesta=timezone.now(),
        )

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.config.timeout,
            )

        except requests.RequestException as exc:
            raise ANNCSUError(
                f"Errore di connessione ad ANNCSU: {exc}"
            ) from exc

        if response.status_code >= 400:
            detail = response.text[:1500]

            raise ANNCSUError(
                f"ANNCSU HTTP {response.status_code}: {detail}"
            )

        try:
            return response.json()

        except ValueError as exc:
            raise ANNCSUError(
                "ANNCSU ha restituito una risposta non JSON."
            ) from exc

    # ------------------------------------------------------------------
    # VERIFICHE
    # ------------------------------------------------------------------

    def esiste_odonimo(
        self,
        codice_comune,
        denominazione,
    ):
        result = self._post(
            "esisteodonimo",
            {
                "req": "esisteodonimo",
                "codcom": codice_comune.strip().upper(),
                "denom": denominazione.strip().upper(),
            },
        )

        value = result.get("data")

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.strip().lower() == "true"

        return False

    def esiste_accesso(
        self,
        codice_comune,
        denominazione,
        accesso,
    ):
        result = self._post(
            "esisteaccesso",
            {
                "req": "esisteaccesso",
                "codcom": codice_comune.strip().upper(),
                "denom": denominazione.strip().upper(),
                "accesso": accesso.strip().upper(),
            },
        )

        value = result.get("data")

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.strip().lower() == "true"

        return False

    # ------------------------------------------------------------------
    # ODONIMI
    # ------------------------------------------------------------------

    def elenco_odonimi_progressivo(
        self,
        codice_comune,
        denominazione_parziale,
    ):
        codice_comune = str(
            codice_comune or ""
        ).strip().upper()

        denominazione_parziale = str(
            denominazione_parziale or ""
        ).strip().upper()

        chiave = (
            f"odonimi:{codice_comune}:"
            f"{denominazione_parziale}"
        )

        # Prima controlliamo se questa stessa ricerca
        # è già stata eseguita nelle ultime ore.
        result = self._cache_get(
            chiave
        )

        if result is None:
            payload = {
                "req": "elencoodonimiprog",
                "codcom": codice_comune,
                "denomparz": denominazione_parziale,
            }

            result = self._post(
                "elencoodonimiprog",
                payload,
            )

            self._cache_set(
                tipo=CacheANNCSU.TIPO_ODONIMI,
                chiave=chiave,
                richiesta=payload,
                risposta=result,
                ttl_ore=self.config.cache_accessi_ore,
            )

            # La ricerca odonimi ci ha già restituito
            # le informazioni delle aree trovate.
            # Le salviamo quindi anche per progressivo,
            # evitando una futura chiamata prognazarea.
            data = result.get(
                "data",
                [],
            )

            if isinstance(data, list):
                for area in data:
                    if not isinstance(area, dict):
                        continue

                    progressivo_area = str(
                        area.get("prognaz", "")
                    ).strip()

                    if not progressivo_area:
                        continue

                    self._cache_set(
                        tipo=CacheANNCSU.TIPO_AREA,
                        chiave=f"area:{progressivo_area}",
                        richiesta={
                            "origine": "elencoodonimiprog",
                            "prognaz": progressivo_area,
                        },
                        risposta={
                            "data": [area],
                        },
                        ttl_ore=self.config.cache_accessi_ore,
                    )

        return result.get(
            "data",
            [],
        )

    @staticmethod
    def _accesso_matches(accesso, filtro):
        """
        Replica localmente la ricerca parziale sugli accessi.

        La cache contiene SEMPRE l'intero elenco della via.
        """

        filtro = str(filtro or "").strip().upper()

        if not filtro:
            return True

        civico = str(
            accesso.get("civico", "")
        ).strip().upper()

        esp = str(
            accesso.get("esp", "")
        ).strip().upper()

        specif = str(
            accesso.get("specif", "")
        ).strip().upper()

        metrico = str(
            accesso.get("metrico", "")
        ).strip().upper()

        valori = []

        if civico:
            valori.append(civico)

            if esp:
                valori.append(
                    f"{civico}-{esp}"
                )
                valori.append(
                    f"{civico} {esp}"
                )

            if specif:
                valori.append(
                    f"{civico}-{specif}"
                )

            if esp and specif:
                valori.append(
                    f"{civico}-{esp}-{specif}"
                )

        if metrico:
            valori.append(metrico)

        return any(
            filtro in valore
            for valore in valori
        )

    def elenco_accessi_progressivo(
        self,
        progressivo_area,
        accesso_parziale="",
    ):
        progressivo_area = str(
            progressivo_area
        ).strip()

        chiave = (
            f"accessi:{progressivo_area}"
        )

        # Prima controlliamo PostgreSQL.
        # Se presente: zero voucher e zero chiamate ANNCSU.
        result = self._cache_get(
            chiave
        )

        if result is None:
            payload = {
                "req": "elencoaccessiprog",
                "prognaz": progressivo_area,
                "accparz": "",
            }

            # Una sola chiamata ANNCSU per scaricare
            # TUTTI gli accessi della via.
            result = self._post(
                "elencoaccessiprog",
                payload,
            )

            self._cache_set(
                tipo=CacheANNCSU.TIPO_ACCESSI,
                chiave=chiave,
                richiesta=payload,
                risposta=result,
                ttl_ore=self.config.cache_accessi_ore,
            )

        data = result.get(
            "data",
            [],
        )

        if not isinstance(data, list):
            data = []

        # Ogni accesso presente nell'elenco completo possiede
        # già il proprio prognazacc.
        #
        # Lo rendiamo quindi disponibile anche tramite
        # accesso:<prognazacc>, senza effettuare prognazacc.
        #
        # Non sovrascriviamo cache singole ancora valide:
        # questo evita di resettarne hit/scadenza inutilmente.
        now = timezone.now()

        for accesso in data:
            if not isinstance(accesso, dict):
                continue

            progressivo_accesso = str(
                accesso.get("prognazacc", "")
            ).strip()

            if not progressivo_accesso:
                continue

            chiave_accesso = (
                f"accesso:{progressivo_accesso}"
            )

            presente = (
                CacheANNCSU.objects
                .filter(
                    chiave=chiave_accesso,
                    scade_il__gt=now,
                )
                .exists()
            )

            if not presente:
                self._cache_set(
                    tipo=CacheANNCSU.TIPO_ACCESSO,
                    chiave=chiave_accesso,
                    richiesta={
                        "origine": "elencoaccessiprog",
                        "prognaz": progressivo_area,
                        "prognazacc": progressivo_accesso,
                    },
                    risposta={
                        "data": [accesso],
                    },
                    ttl_ore=self.config.cache_dettaglio_accesso_ore,
                )

        filtro = str(
            accesso_parziale or ""
        ).strip()

        if not filtro:
            return data

        return [
            accesso
            for accesso in data
            if self._accesso_matches(
                accesso,
                filtro,
            )
        ]

    def area_da_progressivo(
        self,
        progressivo_area,
    ):
        progressivo_area = str(
            progressivo_area
        ).strip()

        chiave = (
            f"area:{progressivo_area}"
        )

        result = self._cache_get(
            chiave
        )

        if result is None:
            payload = {
                "req": "prognazarea",
                "prognaz": progressivo_area,
            }

            result = self._post(
                "prognazarea",
                payload,
            )

            self._cache_set(
                tipo=CacheANNCSU.TIPO_AREA,
                chiave=chiave,
                richiesta=payload,
                risposta=result,
                ttl_ore=self.config.cache_accessi_ore,
            )

        data = result.get(
            "data",
            [],
        )

        if isinstance(data, list):
            return data[0] if data else None

        return data

    def accesso_da_progressivo(
        self,
        progressivo_accesso,
    ):
        progressivo_accesso = str(
            progressivo_accesso
        ).strip()

        chiave = (
            f"accesso:{progressivo_accesso}"
        )

        # Se il civico è già arrivato tramite
        # elencoaccessiprog, sarà già disponibile qui.
        result = self._cache_get(
            chiave
        )

        if result is None:
            payload = {
                "req": "prognazacc",
                "prognazacc": progressivo_accesso,
            }

            result = self._post(
                "prognazacc",
                payload,
            )

            self._cache_set(
                tipo=CacheANNCSU.TIPO_ACCESSO,
                chiave=chiave,
                richiesta=payload,
                risposta=result,
                ttl_ore=self.config.cache_dettaglio_accesso_ore,
            )

        data = result.get(
            "data",
            [],
        )

        if isinstance(data, list):
            return data[0] if data else None

        return data

