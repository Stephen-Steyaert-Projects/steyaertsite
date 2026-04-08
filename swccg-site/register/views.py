from django.shortcuts import redirect, render
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.http import HttpRequest
from django.urls import reverse


class CustomLoginView(LoginView):
    redirect_authenticated_user = True

    def get_redirect_url(self):
        return self.request.GET.get("next") or reverse('home')


def register(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


class ProtectedLogoutView(LoginRequiredMixin, LogoutView):
    login_url = "/auth/login/"  # or whatever your login URL is

    def handle_no_permission(self):
        return redirect('index')