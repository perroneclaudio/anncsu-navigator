from django.urls import path

from . import views


app_name = "core"

urlpatterns = [
    path(
        "",
        views.home,
        name="home",
    ),

    path(
        "verifica-indirizzo/",
        views.verifica_indirizzo,
        name="verifica_indirizzo",
    ),

    path(
        "ricerca-indirizzo/",
        views.ricerca_indirizzo,
        name="ricerca_indirizzo",
    ),

    path(
        "esplora-stradario/",
        views.esplora_stradario,
        name="esplora_stradario",
    ),

    path(
        "area/<str:progressivo_area>/",
        views.dettaglio_area,
        name="dettaglio_area",
    ),

    path(
        "accesso/<str:progressivo_accesso>/",
        views.dettaglio_accesso,
        name="dettaglio_accesso",
    ),

    path(
        "ricerca-progressivo/",
        views.ricerca_progressivo,
        name="ricerca_progressivo",
    ),
]
