from django import forms

from core.models import ConfigurazioneApplicazione


def codice_belfiore_default():
    config = (
        ConfigurazioneApplicazione.objects
        .filter(attiva=True)
        .order_by("pk")
        .first()
    )

    if config:
        return config.codice_belfiore_default

    return ""


class BelfioreMixin:
    def set_belfiore_default(self):
        if not self.is_bound:
            self.fields["codcom"].initial = codice_belfiore_default()


class RicercaStradaForm(BelfioreMixin, forms.Form):
    codcom = forms.CharField(
        label="Codice Belfiore Comune",
        max_length=4,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Codice Belfiore",
            }
        ),
    )

    denomparz = forms.CharField(
        label="Strada",
        max_length=250,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Es. ROMA",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_belfiore_default()

    def clean_codcom(self):
        return self.cleaned_data["codcom"].strip().upper()

    def clean_denomparz(self):
        return self.cleaned_data["denomparz"].strip().upper()


class RicercaIndirizzoForm(BelfioreMixin, forms.Form):
    codcom = forms.CharField(
        label="Codice Belfiore Comune",
        max_length=4,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Codice Belfiore",
            }
        ),
    )

    denomparz = forms.CharField(
        label="Strada",
        max_length=250,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Es. ROMA",
            }
        ),
    )

    civico = forms.CharField(
        label="Civico",
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Es. 27 oppure 27 A",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_belfiore_default()

    def clean_codcom(self):
        return self.cleaned_data["codcom"].strip().upper()

    def clean_denomparz(self):
        return self.cleaned_data["denomparz"].strip().upper()

    def clean_civico(self):
        return self.cleaned_data["civico"].strip().upper()


class VerificaIndirizzoForm(BelfioreMixin, forms.Form):
    codcom = forms.CharField(
        label="Codice Belfiore Comune",
        max_length=4,
        widget=forms.TextInput(
            attrs={"class": "form-control"}
        ),
    )

    denominazione = forms.CharField(
        label="Denominazione completa strada",
        max_length=250,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Es. VIA ROMA",
            }
        ),
    )

    civico = forms.CharField(
        label="Civico",
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Es. 12",
            }
        ),
    )

    esponente = forms.CharField(
        label="Esponente",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Es. A",
            }
        ),
    )

    specificita = forms.CharField(
        label="Specificità",
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Es. ROSSO",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_belfiore_default()

    def clean_codcom(self):
        return self.cleaned_data["codcom"].strip().upper()

    def clean_denominazione(self):
        return self.cleaned_data["denominazione"].strip().upper()

    def costruisci_accesso(self):
        parts = []

        civico = self.cleaned_data.get("civico", "").strip().upper()
        esponente = self.cleaned_data.get("esponente", "").strip().upper()
        specificita = self.cleaned_data.get("specificita", "").strip().upper()

        if civico:
            parts.append(civico)

        if esponente:
            parts.append(esponente)

        if specificita:
            parts.append(specificita)

        return "-".join(parts)


class RicercaAccessiForm(forms.Form):
    accparz = forms.CharField(
        label="Filtra civico / accesso",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Lascia vuoto per mostrare tutti gli accessi",
            }
        ),
    )

    def clean_accparz(self):
        return self.cleaned_data.get("accparz", "").strip().upper()


class RicercaProgressivoForm(forms.Form):
    TIPO_AREA = "area"
    TIPO_ACCESSO = "accesso"

    TIPO_CHOICES = (
        (TIPO_AREA, "Area di circolazione"),
        (TIPO_ACCESSO, "Accesso"),
    )

    tipo = forms.ChoiceField(
        label="Tipo ricerca",
        choices=TIPO_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )

    progressivo = forms.CharField(
        label="Progressivo nazionale",
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Inserisci il progressivo nazionale",
            }
        ),
    )

    def clean_progressivo(self):
        return self.cleaned_data["progressivo"].strip()
