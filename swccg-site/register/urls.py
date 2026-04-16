from django.urls import path
from .views import CustomLoginView, ProtectedLogoutView, register

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', ProtectedLogoutView.as_view(), name='logout'),
    path('register/', register, name='register'),
]