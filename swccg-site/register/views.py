from django.shortcuts import redirect, render
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import login
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings

from .forms import RegistrationForm, SetPasswordForm


class CustomLoginView(LoginView):
    redirect_authenticated_user = True

    def get_redirect_url(self):
        return self.request.GET.get("next") or reverse('home')


@transaction.atomic
def _register_user(username: str, email: str, set_password_url_base: str) -> None:
    user = User.objects.create_user(username=username, email=email, is_active=False)
    user.set_unusable_password()
    user.save()

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    set_password_url = set_password_url_base.replace('UIDB64', uid).replace('TOKEN', token)

    ctx = {'username': user.username, 'set_password_url': set_password_url}
    text_body = (
        f"Hi {user.username},\n\n"
        f"Click the link below to set your password and activate your account:\n\n"
        f"{set_password_url}\n\n"
        f"This link expires in 10 minutes.\n"
    )
    html_body = render_to_string('registration/activation_email.html', ctx)
    msg = EmailMultiAlternatives(
        subject="Complete your registration",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()


def register(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            url_base = request.build_absolute_uri(
                reverse('set_password', kwargs={'uidb64': 'UIDB64', 'token': 'TOKEN'})
            )
            try:
                _register_user(form.cleaned_data['username'], form.cleaned_data['email'], url_base)
                return redirect('register_done')
            except Exception:
                form.add_error(None, "We couldn't send the activation email. Please try again later.")
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


def register_done(request: HttpRequest):
    return render(request, 'registration/register_done.html')


def set_password(request: HttpRequest, uidb64: str, token: str):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, ObjectDoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(request, 'registration/set_password_invalid.html', status=400)

    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['password1'])
            user.is_active = True
            user.save()
            login(request, user)
            messages.success(request, "Welcome! Your account is now active.")
            return redirect('home')
    else:
        form = SetPasswordForm()

    return render(request, 'registration/set_password.html', {'form': form})
