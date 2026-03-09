from django.urls import include, path
from . import views

urlpatterns = [
    path('',                                    views.login_view,              name='login'),
    path('login/',                              views.login_view,              name='login'),
    path('logout/',                             views.logout_view,             name='logout'),
    path('dashboard/',                          views.dashboard,               name='dashboard'),
    path('auth/change-password/',               views.force_password_change,   name='force_password_change'),
    path('auth/forgot-password/',               views.forgot_password,         name='forgot_password'),
    path('auth/reset-password/<str:token>/',    views.password_reset_confirm,  name='password_reset_confirm'),
    path('', include('accounts.urls_users')),
    path('', include('patients.urls_patients')),
    path('', include('consultations.urls_consultations')),
    path('', include('inventory.urls_inventory')),
    path('', include('prescriptions.urls_prescriptions')),
    path('', include('dispensing.urls_dispensing')),
    path('', include('wards.urls_wards')),
    path('', include('laboratory.urls_lab')),
    path('', include('clearance.urls_clearance')),
    path('', include('documents.urls_documents')),
    path('', include('reports.urls_reports')),
]