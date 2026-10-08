from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.forms import (
    RicercaAccessiForm,
    RicercaIndirizzoForm,
    RicercaProgressivoForm,
    RicercaStradaForm,
    VerificaIndirizzoForm,
)

from core.services.anncsu import (
    ANNCSUClient,
    ANNCSUConfigurationError,
    ANNCSUError,
)


def anncsu_error(request, exc):
    messages.error(
        request,
        f"Errore ANNCSU: {exc}",
    )


@login_required
def home(request):
    return render(
        request,
        "core/home.html",
    )


@login_required
def verifica_indirizzo(request):
    form = VerificaIndirizzoForm(
        request.POST or None
    )

    risultato = None

    if request.method == "POST" and form.is_valid():
        try:
            client = ANNCSUClient()

            strada_esiste = client.esiste_odonimo(
                form.cleaned_data["codcom"],
                form.cleaned_data["denominazione"],
            )

            accesso = form.costruisci_accesso()

            accesso_esiste = None

            if strada_esiste and accesso:
                accesso_esiste = client.esiste_accesso(
                    form.cleaned_data["codcom"],
                    form.cleaned_data["denominazione"],
                    accesso,
                )

            risultato = {
                "strada_esiste": strada_esiste,
                "accesso_esiste": accesso_esiste,
                "accesso": accesso,
            }

        except (
            ANNCSUConfigurationError,
            ANNCSUError,
        ) as exc:
            anncsu_error(request, exc)

    return render(
        request,
        "core/verifica_indirizzo.html",
        {
            "form": form,
            "risultato": risultato,
        },
    )


@login_required
def ricerca_indirizzo(request):
    form = RicercaIndirizzoForm(
        request.GET or None
    )

    strade = None
    accessi = None
    strada_scelta = None

    if request.GET and form.is_valid():
        codcom = form.cleaned_data["codcom"]
        denomparz = form.cleaned_data["denomparz"]
        civico_cercato = form.cleaned_data["civico"].strip().upper()

        progressivo_area = request.GET.get(
            "prognaz",
            "",
        ).strip()

        try:
            client = ANNCSUClient()

            # PRIMO PASSAGGIO:
            # cerca esclusivamente gli odonimi.
            if not progressivo_area:
                strade = client.elenco_odonimi_progressivo(
                    codcom,
                    denomparz,
                )

                if not strade:
                    messages.info(
                        request,
                        "Nessuna strada trovata.",
                    )

            # SECONDO PASSAGGIO:
            # l'utente ha scelto una precisa area di circolazione.
            else:
                strada_scelta = {
                    "prognaz": progressivo_area,
                    "dug": request.GET.get("dug", ""),
                    "duf": request.GET.get("duf", ""),
                    "denomloc": request.GET.get(
                        "denomloc",
                        "",
                    ),
                }

                candidati = (
                    client.elenco_accessi_progressivo(
                        progressivo_area,
                        civico_cercato,
                    )
                )

                # ANNCSU esegue una ricerca parziale.
                # In Ricerca indirizzo vogliamo invece
                # esclusivamente il civico esatto.
                accessi = []

                for accesso in candidati:
                    civico_restituito = str(
                        accesso.get(
                            "civico",
                            "",
                        )
                    ).strip().upper()

                    if civico_restituito != civico_cercato:
                        continue

                    accessi.append(accesso)

                if not accessi:
                    messages.info(
                        request,
                        "Il civico indicato non è presente "
                        "nell'area di circolazione selezionata.",
                    )

        except (
            ANNCSUConfigurationError,
            ANNCSUError,
        ) as exc:
            anncsu_error(request, exc)

    return render(
        request,
        "core/ricerca_indirizzo.html",
        {
            "form": form,
            "strade": strade,
            "accessi": accessi,
            "strada_scelta": strada_scelta,
        },
    )


@login_required
def esplora_stradario(request):
    ricerca_form = RicercaStradaForm(
        request.POST or None,
        prefix="strada",
    )

    risultati = None

    if (
        request.method == "POST"
        and "cerca_strada" in request.POST
        and ricerca_form.is_valid()
    ):
        try:
            risultati = (
                ANNCSUClient()
                .elenco_odonimi_progressivo(
                    ricerca_form.cleaned_data["codcom"],
                    ricerca_form.cleaned_data["denomparz"],
                )
            )

        except (
            ANNCSUConfigurationError,
            ANNCSUError,
        ) as exc:
            anncsu_error(request, exc)

    return render(
        request,
        "core/esplora_stradario.html",
        {
            "form": ricerca_form,
            "risultati": risultati,
        },
    )


@login_required
def dettaglio_area(
    request,
    progressivo_area,
):
    area = None
    accessi = None

    form = RicercaAccessiForm(
        request.GET or None
    )

    try:
        client = ANNCSUClient()

        area = client.area_da_progressivo(
            progressivo_area
        )

        filtro_accesso = ""

        if request.GET:
            if form.is_valid():
                filtro_accesso = form.cleaned_data["accparz"]
        else:
            form = RicercaAccessiForm()

        accessi = client.elenco_accessi_progressivo(
            progressivo_area,
            filtro_accesso,
        )

        paginator = Paginator(accessi, 25)
        page_obj = paginator.get_page(
            request.GET.get("page")
        )

    except (
        ANNCSUConfigurationError,
        ANNCSUError,
    ) as exc:
        anncsu_error(request, exc)

    return render(
        request,
        "core/dettaglio_area.html",
        {
            "area": area,
            "form": form,
            "accessi": accessi,
            "page_obj": page_obj if accessi is not None else None,
            "progressivo_area": progressivo_area,
        },
    )


@login_required
def dettaglio_accesso(
    request,
    progressivo_accesso,
):
    accesso = None

    try:
        accesso = (
            ANNCSUClient()
            .accesso_da_progressivo(
                progressivo_accesso
            )
        )

    except (
        ANNCSUConfigurationError,
        ANNCSUError,
    ) as exc:
        anncsu_error(request, exc)

    return render(
        request,
        "core/dettaglio_accesso.html",
        {
            "accesso": accesso,
        },
    )


@login_required
def ricerca_progressivo(request):
    form = RicercaProgressivoForm(
        request.POST or None
    )

    risultato = None
    tipo = None

    if request.method == "POST" and form.is_valid():
        tipo = form.cleaned_data["tipo"]
        progressivo = form.cleaned_data["progressivo"]

        try:
            client = ANNCSUClient()

            if tipo == RicercaProgressivoForm.TIPO_AREA:
                risultato = client.area_da_progressivo(
                    progressivo
                )

            else:
                risultato = client.accesso_da_progressivo(
                    progressivo
                )

        except (
            ANNCSUConfigurationError,
            ANNCSUError,
        ) as exc:
            anncsu_error(request, exc)

    return render(
        request,
        "core/ricerca_progressivo.html",
        {
            "form": form,
            "risultato": risultato,
            "tipo": tipo,
        },
    )
