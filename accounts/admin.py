from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Role, RolePermission, SystemModule,
    UserPermissionOverride, LoginAudit, AuditTrail,
    PasswordResetToken, SystemSetting, AcademicSession
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display    = ['email', 'get_full_name', 'role', 'is_active', 'is_staff', 'created_at']
    list_filter     = ['role', 'is_active', 'is_staff', 'gender']
    search_fields   = ['email', 'first_name', 'last_name', 'staff_id']
    ordering        = ['last_name', 'first_name']

    fieldsets = (
        ('Login',        {'fields': ('email', 'password')}),
        ('Personal',     {'fields': ('first_name', 'last_name', 'other_names', 'gender', 'date_of_birth', 'phone', 'profile_photo')}),
        ('Professional', {'fields': ('staff_id', 'role', 'department', 'job_title', 'qualification', 'reg_number', 'digital_signature')}),
        ('Status',       {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'must_change_password')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields':  ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display  = ['name', 'is_system_role', 'is_active', 'created_at']
    list_filter   = ['is_system_role', 'is_active']
    search_fields = ['name']


@admin.register(SystemModule)
class SystemModuleAdmin(admin.ModelAdmin):
    list_display  = ['name', 'slug', 'parent', 'sort_order', 'is_active']
    list_filter   = ['is_active']
    search_fields = ['name', 'slug']
    ordering      = ['sort_order']


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display  = ['role', 'module', 'can_view', 'can_create', 'can_edit', 'can_delete', 'can_export']
    list_filter   = ['role', 'can_view', 'can_create']


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display  = ['setting_key', 'setting_value', 'setting_type', 'updated_at']
    search_fields = ['setting_key']


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ['session_name', 'start_date', 'end_date', 'is_current']


@admin.register(LoginAudit)
class LoginAuditAdmin(admin.ModelAdmin):
    list_display  = ['attempted_email', 'status', 'ip_address', 'created_at']
    list_filter   = ['status']
    search_fields = ['attempted_email', 'ip_address']
    readonly_fields = ['user', 'attempted_email', 'ip_address', 'user_agent', 'status', 'failure_reason', 'created_at']


@admin.register(AuditTrail)
class AuditTrailAdmin(admin.ModelAdmin):
    list_display  = ['user', 'action', 'module', 'record_id', 'ip_address', 'created_at']
    list_filter   = ['action', 'module']
    search_fields = ['user__email', 'module', 'record_id']
    readonly_fields = ['user', 'action', 'module', 'record_id', 'old_values', 'new_values', 'ip_address', 'description', 'created_at']