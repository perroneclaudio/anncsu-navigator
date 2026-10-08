from django.contrib import admin

from .models import (
    ConfigurazioneApplicazione,
    ConfigurazionePDND,
)


@admin.register(ConfigurazioneApplicazione)
class ConfigurazioneApplicazioneAdmin(admin.ModelAdmin):
    list_display = (
        "nome_app",
        "titolo_browser",
        "codice_belfiore_default",
        "attiva",
        "aggiornata_il",
    )

    readonly_fields = (
        "aggiornata_il",
    )

    def has_add_permission(self, request):
        if ConfigurazioneApplicazione.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ConfigurazionePDND)
class ConfigurazionePDNDAdmin(admin.ModelAdmin):
    list_display = (
        "client_id",
        "purpose_id",
        "attiva",
        "aggiornata_il",
    )

    readonly_fields = (
        "aggiornata_il",
    )

    fieldsets = (
        (
            "Stato",
            {
                "fields": (
                    "attiva",
                ),
            },
        ),
        (
            "Client PDND",
            {
                "fields": (
                    "client_id",
                    "purpose_id",
                    "kid",
                    "iss",
                    "sub",
                ),
            },
        ),
        (
            "Autenticazione",
            {
                "fields": (
                    "audience_assertion",
                    "url_token",
                    "algoritmo_jwt",
                    "tipo_jwt",
                    "percorso_chiave_privata",
                ),
            },
        ),
        (
            "E-service ANNCSU",
            {
                "fields": (
                    "audience_eservice",
                    "base_url_eservice",
                    "timeout",
                "limite_richieste_giornaliere",
                "cache_accessi_ore",
                "cache_dettaglio_accesso_ore",
                ),
            },
        ),
        (
            "Informazioni",
            {
                "fields": (
                    "aggiornata_il",
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        if ConfigurazionePDND.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False



from core.models import CacheANNCSU


@admin.register(CacheANNCSU)
class CacheANNCSUAdmin(admin.ModelAdmin):
    list_display = (
        "tipo",
        "chiave",
        "creata_il",
        "aggiornata_il",
        "scade_il",
        "ultimo_accesso",
        "numero_hit",
    )

    list_filter = (
        "tipo",
        "scade_il",
    )

    search_fields = (
        "chiave",
    )

    readonly_fields = (
        "tipo",
        "chiave",
        "richiesta_json",
        "risposta_json",
        "creata_il",
        "aggiornata_il",
        "scade_il",
        "ultimo_accesso",
        "numero_hit",
    )

    def has_add_permission(self, request):
        return False


from core.models import ContatoreRichiesteANNCSU


@admin.register(ContatoreRichiesteANNCSU)
class ContatoreRichiesteANNCSUAdmin(admin.ModelAdmin):
    list_display = (
        "giorno",
        "richieste",
        "ultima_richiesta",
    )

    ordering = (
        "-giorno",
    )

    readonly_fields = (
        "giorno",
        "richieste",
        "ultima_richiesta",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
