from django.utils import timezone

from core.models import (
    ConfigurazioneApplicazione,
    ConfigurazionePDND,
    ContatoreRichiesteANNCSU,
)


def configurazione_app(request):
    app_config = (
        ConfigurazioneApplicazione.objects
        .filter(attiva=True)
        .order_by("pk")
        .first()
    )

    pdnd_config = (
        ConfigurazionePDND.objects
        .filter(attiva=True)
        .order_by("pk")
        .first()
    )

    oggi = timezone.localdate()

    contatore = (
        ContatoreRichiesteANNCSU.objects
        .filter(giorno=oggi)
        .first()
    )

    richieste_oggi = (
        contatore.richieste
        if contatore
        else 0
    )

    limite_giornaliero = (
        pdnd_config.limite_richieste_giornaliere
        if pdnd_config
        else 100
    )

    return {
        "APP_CONFIG": app_config,
        "ANNCSU_RICHIESTE_OGGI": richieste_oggi,
        "ANNCSU_LIMITE_GIORNALIERO": limite_giornaliero,
    }
