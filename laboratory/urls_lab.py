from django.urls import path
from laboratory import views_lab

urlpatterns = [
    path('laboratory/',                         views_lab.lab_list,           name='lab_list'),
    path('laboratory/create/',                  views_lab.lab_create,         name='lab_create'),
    path('laboratory/<int:pk>/',                views_lab.lab_detail,         name='lab_detail'),
    path('laboratory/<int:pk>/results/',        views_lab.lab_enter_results,  name='lab_enter_results'),
    path('laboratory/<int:pk>/status/',         views_lab.lab_update_status,  name='lab_update_status'),
    path('laboratory/<int:pk>/report/',         views_lab.lab_report,         name='lab_report'),
    path('laboratory/catalog/',                 views_lab.lab_catalog,        name='lab_catalog'),

    # AJAX
    path('ajax/lab/patient-consultations/',     views_lab.lab_patient_consultations_ajax, name='lab_patient_consultations_ajax'),
]