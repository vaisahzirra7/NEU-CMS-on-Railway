from django.urls import path
from accounts import views_settings

urlpatterns = [

    # ── Settings Dashboard ────────────────────────────────────────────────────
    path('settings/',
         views_settings.settings_dashboard,
         name='settings_dashboard'),

    # ── Faculties ─────────────────────────────────────────────────────────────
    path('settings/faculties/',
         views_settings.faculty_list,
         name='faculty_list'),

    path('settings/faculties/create/',
         views_settings.faculty_create,
         name='faculty_create'),

    path('settings/faculties/<int:pk>/edit/',
         views_settings.faculty_edit,
         name='faculty_edit'),

    path('settings/faculties/<int:pk>/toggle/',
         views_settings.faculty_toggle,
         name='faculty_toggle'),

    # ── Departments ───────────────────────────────────────────────────────────
    path('settings/departments/',
         views_settings.department_list,
         name='department_list'),

    path('settings/departments/create/',
         views_settings.department_create,
         name='department_create'),

    path('settings/departments/<int:pk>/edit/',
         views_settings.department_edit,
         name='department_edit'),

    path('settings/departments/<int:pk>/toggle/',
         views_settings.department_toggle,
         name='department_toggle'),

    # ── Programmes ────────────────────────────────────────────────────────────
    path('settings/programmes/',
         views_settings.programme_list,
         name='programme_list'),

    path('settings/programmes/create/',
         views_settings.programme_create,
         name='programme_create'),

    path('settings/programmes/<int:pk>/edit/',
         views_settings.programme_edit,
         name='programme_edit'),

    path('settings/programmes/<int:pk>/toggle/',
         views_settings.programme_toggle,
         name='programme_toggle'),

]