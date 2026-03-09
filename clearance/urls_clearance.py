from django.urls import path
from clearance import views_clearance

urlpatterns = [
    path('clearance/default-questions/',            views_clearance.default_questions,      name='default_questions'),

    # ── Staff ──────────────────────────────────────────────────────────────
    path('clearance/',                              views_clearance.clearance_dashboard,    name='clearance_dashboard'),
    path('clearance/sessions/create/',              views_clearance.session_create,         name='session_create'),
    path('clearance/sessions/<int:pk>/edit/',       views_clearance.session_edit,           name='session_edit'),
    path('clearance/sessions/<int:pk>/questions/',  views_clearance.session_questions,      name='session_questions'),
    path('clearance/sessions/<int:pk>/submissions/',views_clearance.submission_list,        name='submission_list'),
    path('clearance/submissions/<int:pk>/',         views_clearance.submission_detail,      name='submission_detail'),
    path('clearance/submissions/<int:pk>/certificate/', views_clearance.clearance_certificate, name='clearance_certificate'),

    # ── Public (student-facing) ────────────────────────────────────────────
    path('medical-clearance/',                      views_clearance.clearance_verify,       name='clearance_verify'),
    path('medical-clearance/form/',                 views_clearance.clearance_form,         name='clearance_form'),
    path('medical-clearance/success/<int:pk>/',     views_clearance.clearance_success,      name='clearance_success'),
    path('medical-clearance/status/',               views_clearance.clearance_status_check, name='clearance_status_check'),
]