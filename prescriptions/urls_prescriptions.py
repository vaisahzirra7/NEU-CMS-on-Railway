from django.urls import path
from prescriptions import views_prescriptions

urlpatterns = [
    path('prescriptions/',                  views_prescriptions.prescription_list,          name='prescription_list'),
    path('prescriptions/create/',           views_prescriptions.prescription_create,        name='prescription_create'),
    path('prescriptions/<int:pk>/',         views_prescriptions.prescription_detail,        name='prescription_detail'),
    path('prescriptions/<int:pk>/status/',  views_prescriptions.prescription_update_status, name='prescription_update_status'),

    # AJAX
    path('ajax/prescriptions/patient-consultations/', views_prescriptions.patient_consultations_ajax, name='patient_consultations_ajax'),
]