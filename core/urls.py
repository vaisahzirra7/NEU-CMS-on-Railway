"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/',      admin.site.urls),
    path('auth/',       include('accounts.urls')),
    path('',            include('accounts.urls')),
    path('',            include('patients.urls_patients')),
    path('', include('accounts.urls_settings')),
    path('', include('appointments.urls_appointments')),
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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)