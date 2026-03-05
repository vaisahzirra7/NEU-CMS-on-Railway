from django.urls import path
from patients import views_patients

urlpatterns = [
    path('patients/',
         views_patients.patient_list,
         name='patient_list'),

    path('patients/register/',
         views_patients.patient_create,
         name='patient_create'),

    path('patients/import/',
         views_patients.patient_import,
         name='patient_import'),

    path('patients/import/template/',
         views_patients.download_csv_template,
         name='patient_csv_template'),

    # ── Named actions BEFORE the catch-all detail route ──
    path('patients/<path:matric_no>/edit/',
         views_patients.patient_edit,
         name='patient_edit'),

    path('patients/<path:matric_no>/toggle-status/',
         views_patients.patient_toggle_status,
         name='patient_toggle_status'),

    # ── Detail route LAST ─────────────────────────────────
    path('patients/<path:matric_no>/',
         views_patients.patient_detail,
         name='patient_detail'),

    # ── AJAX ─────────────────────────────────────────────
    path('ajax/faculty/<int:faculty_id>/departments/',
         views_patients.faculty_departments,
         name='faculty_departments'),

    path('ajax/faculty/<int:faculty_id>/programmes/',
         views_patients.faculty_programmes,
         name='faculty_programmes'),
]