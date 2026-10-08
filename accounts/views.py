from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import LoginForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:home")

    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"].strip()
        password = form.cleaned_data["password"]

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)

            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)

            return redirect("core:home")

        messages.error(
            request,
            "Credenziali non valide oppure modalità di autenticazione non consentita.",
        )

    return render(
        request,
        "accounts/login.html",
        {
            "form": form,
        },
    )


def logout_view(request):
    logout(request)
    return redirect(reverse("accounts:login"))
