from django.urls import path
from wards import views_wards

urlpatterns = [
    path('wards/',                              views_wards.ward_overview,      name='ward_overview'),
    path('wards/setup/',                        views_wards.ward_setup,         name='ward_setup'),
    path('wards/<int:pk>/',                     views_wards.ward_detail,        name='ward_detail'),
    path('wards/admissions/',                   views_wards.admission_list,     name='admission_list'),
    path('wards/admissions/admit/',             views_wards.admit_patient,      name='admit_patient'),
    path('wards/admissions/<int:pk>/',          views_wards.admission_detail,   name='admission_detail'),
    path('wards/admissions/<int:pk>/transfer/', views_wards.transfer_patient,   name='transfer_patient'),
    path('wards/admissions/<int:pk>/discharge/',views_wards.discharge_patient,  name='discharge_patient'),

    # AJAX
    path('ajax/wards/available-beds/',          views_wards.available_beds_ajax, name='available_beds_ajax'),
]