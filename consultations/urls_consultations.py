from django.urls import path
from consultations import views_consultations

urlpatterns = [

    path('consultations/',
         views_consultations.consultation_list,
         name='consultation_list'),

    path('consultations/start/',
         views_consultations.consultation_create,
         name='consultation_create'),

    path('consultations/<int:pk>/',
         views_consultations.consultation_detail,
         name='consultation_detail'),

    path('consultations/<int:pk>/edit/',
         views_consultations.consultation_edit,
         name='consultation_edit'),

    path('consultations/<int:pk>/status/',
         views_consultations.consultation_update_status,
         name='consultation_update_status'),

    # AJAX
    path('ajax/consultations/patient-appointments/',
         views_consultations.patient_appointments,
         name='patient_appointments_ajax'),
]