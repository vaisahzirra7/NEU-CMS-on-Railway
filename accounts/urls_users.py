from django.urls import path
from accounts import views_users

urlpatterns = [

    # ── Users ─────────────────────────────────────────────────────────────────
    path('users/',
         views_users.user_list,
         name='user_list'),

    path('users/create/',
         views_users.user_create,
         name='user_create'),

    path('users/<int:pk>/',
         views_users.user_detail,
         name='user_detail'),

    path('users/<int:pk>/edit/',
         views_users.user_edit,
         name='user_edit'),

    path('users/<int:pk>/toggle-status/',
         views_users.user_toggle_status,
         name='user_toggle_status'),

    path('users/<int:pk>/reset-password/',
         views_users.user_reset_password,
         name='user_reset_password'),

    # ── Roles ──────────────────────────────────────────────────────────────────
    path('roles/',
         views_users.role_list,
         name='role_list'),

    path('roles/<int:pk>/permissions/',
         views_users.role_permissions,
         name='role_permissions'),

]