from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import CustomLoginView, register, register_done, set_password

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', register, name='register'),
    path('register/done/', register_done, name='register_done'),
    path('set-password/<uidb64>/<token>/', set_password, name='set_password'),
]
