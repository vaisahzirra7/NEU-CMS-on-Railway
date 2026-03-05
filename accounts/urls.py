from django.urls import include, path
from . import views

urlpatterns = [
    path('',            views.login_view,    name='login'),
    path('login/',      views.login_view,    name='login'),
    path('logout/',     views.logout_view,   name='logout'),
    path('dashboard/',  views.dashboard,     name='dashboard'),
    path('', include('accounts.urls_users')),
    path('', include('patients.urls_patients')),
    path('', include('consultations.urls_consultations')),
]