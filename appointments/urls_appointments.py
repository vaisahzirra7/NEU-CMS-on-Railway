from django.urls import path
from appointments import views_appointments

urlpatterns = [

    path('appointments/',
         views_appointments.appointment_list,
         name='appointment_list'),

    path('appointments/book/',
         views_appointments.appointment_create,
         name='appointment_create'),

    path('appointments/<int:pk>/',
         views_appointments.appointment_detail,
         name='appointment_detail'),

    path('appointments/<int:pk>/edit/',
         views_appointments.appointment_edit,
         name='appointment_edit'),

    path('appointments/<int:pk>/status/',
         views_appointments.appointment_update_status,
         name='appointment_update_status'),

    # AJAX
    path('ajax/appointments/booked-slots/',
         views_appointments.booked_slots,
         name='booked_slots'),
]