from django.urls import path
from .views import CustomLoginView, ProtectedLogoutView

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    # path('logout/', auth_views.CustomLogoutView.as_view(), name='logout'),
    path('logout/', ProtectedLogoutView.as_view(), name='logout'),

]