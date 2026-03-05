from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


# =============================================================================
# SYSTEM MODULES — Every page/section in VanaraUniCare registered here
# This is what the admin sees when building the permission checklist for a role
# =============================================================================
class SystemModule(models.Model):
    name        = models.CharField(max_length=100)
    slug        = models.SlugField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    icon        = models.CharField(max_length=100, blank=True)       # e.g. "fa-user-injured"
    parent      = models.ForeignKey(
                    'self', null=True, blank=True,
                    on_delete=models.SET_NULL, related_name='children'
                  )
    sort_order  = models.PositiveIntegerField(default=0)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'system_modules'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


# =============================================================================
# ROLES — Created and named by admin e.g. "Doctor", "QA Team", "Management"
# =============================================================================
class Role(models.Model):
    name           = models.CharField(max_length=100, unique=True)
    slug           = models.SlugField(max_length=100, unique=True)
    description    = models.TextField(blank=True)
    is_system_role = models.BooleanField(default=False)   # Built-in roles cannot be deleted
    is_active      = models.BooleanField(default=True)
    created_by     = models.ForeignKey(
                        'User', null=True, blank=True,
                        on_delete=models.SET_NULL, related_name='roles_created'
                     )
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roles'
        ordering = ['name']

    def __str__(self):
        return self.name


# =============================================================================
# ROLE PERMISSIONS — The checkbox matrix: role + module + what they can do
# =============================================================================
class RolePermission(models.Model):
    role       = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='permissions')
    module     = models.ForeignKey(SystemModule, on_delete=models.CASCADE, related_name='role_permissions')
    can_view   = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit   = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'role_permissions'
        unique_together = ('role', 'module')

    def __str__(self):
        return f"{self.role.name} → {self.module.name}"


# =============================================================================
# CUSTOM USER MANAGER
# =============================================================================
class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        user  = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)
        return self.create_user(email, password, **extra_fields)


# =============================================================================
# USER — All staff accounts: doctors, nurses, pharmacists, admin, ICT etc.
# =============================================================================
class User(AbstractBaseUser, PermissionsMixin):

    GENDER_CHOICES = [
        ('Male',   'Male'),
        ('Female', 'Female'),
        ('Other',  'Other'),
    ]

    # Identity
    staff_id          = models.CharField(max_length=50, unique=True, null=True, blank=True)
    first_name        = models.CharField(max_length=100)
    last_name         = models.CharField(max_length=100)
    other_names       = models.CharField(max_length=100, blank=True)
    email             = models.EmailField(unique=True)
    phone             = models.CharField(max_length=20, blank=True)

    # Professional
    role              = models.ForeignKey(
                            Role, null=True, blank=True,
                            on_delete=models.RESTRICT, related_name='users'
                        )
    department        = models.CharField(max_length=150, blank=True)
    job_title         = models.CharField(max_length=150, blank=True)
    qualification     = models.CharField(max_length=255, blank=True)   # e.g. "MBBS, FWACS"
    reg_number        = models.CharField(max_length=100, blank=True)   # Professional reg number

    # Profile
    profile_photo     = models.ImageField(upload_to='staff/photos/', null=True, blank=True)
    digital_signature = models.ImageField(upload_to='staff/signatures/', null=True, blank=True)
    gender            = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    date_of_birth     = models.DateField(null=True, blank=True)
    date_joined       = models.DateField(null=True, blank=True)

    # Django required fields
    is_active         = models.BooleanField(default=True)
    is_staff          = models.BooleanField(default=False)   # Django admin access
    is_verified       = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=True) # Force change on first login

    # Activity tracking
    last_login_ip     = models.GenericIPAddressField(null=True, blank=True)
    created_by        = models.ForeignKey(
                            'self', null=True, blank=True,
                            on_delete=models.SET_NULL, related_name='users_created'
                        )
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def get_full_name(self):
        parts = [self.first_name, self.other_names, self.last_name]
        return ' '.join(p for p in parts if p).strip()

    def get_short_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_display_name(self):
        """Returns title + name e.g. Dr. Adebayo John"""
        title = ''
        if self.job_title:
            if 'doctor' in self.job_title.lower() or 'physician' in self.job_title.lower():
                title = 'Dr.'
            elif 'nurse' in self.job_title.lower():
                title = 'Nurse'
            elif 'pharmacist' in self.job_title.lower():
                title = 'Pharm.'
        return f"{title} {self.get_short_name()}".strip()

    # -------------------------------------------------------------------------
    # Permission helpers — check what this user can do on a given module
    # -------------------------------------------------------------------------
    def get_module_permission(self, module_slug):
        """
        Returns the effective permission for this user on a module.
        Checks individual override first, falls back to role permission.
        """
        # Check individual override first
        override = self.permission_overrides.filter(
            module__slug=module_slug
        ).first()

        if override:
            return {
                'can_view':   override.can_view,
                'can_create': override.can_create,
                'can_edit':   override.can_edit,
                'can_delete': override.can_delete,
                'can_export': override.can_export,
            }

        # Fall back to role permission
        if self.role:
            role_perm = self.role.permissions.filter(
                module__slug=module_slug
            ).first()
            if role_perm:
                return {
                    'can_view':   role_perm.can_view,
                    'can_create': role_perm.can_create,
                    'can_edit':   role_perm.can_edit,
                    'can_delete': role_perm.can_delete,
                    'can_export': role_perm.can_export,
                }

        # No permission found — deny everything
        return {
            'can_view':   False,
            'can_create': False,
            'can_edit':   False,
            'can_delete': False,
            'can_export': False,
        }

    def can_view(self, module_slug):
        if self.is_superuser:
            return True
        return self.get_module_permission(module_slug)['can_view']

    def can_create(self, module_slug):
        if self.is_superuser:
            return True
        return self.get_module_permission(module_slug)['can_create']

    def can_edit(self, module_slug):
        if self.is_superuser:
            return True
        return self.get_module_permission(module_slug)['can_edit']

    def can_delete(self, module_slug):
        if self.is_superuser:
            return True
        return self.get_module_permission(module_slug)['can_delete']

    def can_export(self, module_slug):
        if self.is_superuser:
            return True
        return self.get_module_permission(module_slug)['can_export']

    def get_accessible_modules(self):
        """Returns all modules this user has at least view access to."""
        if self.is_superuser:
            return SystemModule.objects.filter(is_active=True)

        accessible_slugs = set()

        # From role
        if self.role:
            role_slugs = self.role.permissions.filter(
                can_view=True, module__is_active=True
            ).values_list('module__slug', flat=True)
            accessible_slugs.update(role_slugs)

        # From overrides
        override_slugs = self.permission_overrides.filter(
            can_view=True, module__is_active=True
        ).values_list('module__slug', flat=True)
        accessible_slugs.update(override_slugs)

        return SystemModule.objects.filter(slug__in=accessible_slugs, is_active=True)


# =============================================================================
# USER PERMISSION OVERRIDES — Per-user exceptions above or below their role
# =============================================================================
class UserPermissionOverride(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permission_overrides')
    module     = models.ForeignKey(SystemModule, on_delete=models.CASCADE)
    can_view   = models.BooleanField(null=True, blank=True)   # None = inherit from role
    can_create = models.BooleanField(null=True, blank=True)
    can_edit   = models.BooleanField(null=True, blank=True)
    can_delete = models.BooleanField(null=True, blank=True)
    can_export = models.BooleanField(null=True, blank=True)
    reason     = models.TextField(blank=True)
    granted_by = models.ForeignKey(
                    User, null=True, blank=True,
                    on_delete=models.SET_NULL, related_name='overrides_granted'
                 )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_permission_overrides'
        unique_together = ('user', 'module')

    def __str__(self):
        return f"Override: {self.user.get_short_name()} → {self.module.name}"


# =============================================================================
# LOGIN AUDIT — Every login attempt, success or failure
# =============================================================================
class LoginAudit(models.Model):

    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed',  'Failed'),
        ('locked',  'Account Locked'),
    ]

    user            = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    attempted_email = models.EmailField()
    ip_address      = models.GenericIPAddressField()
    user_agent      = models.TextField(blank=True)
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES)
    failure_reason  = models.CharField(max_length=255, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'login_audit'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.attempted_email} — {self.status} — {self.created_at:%Y-%m-%d %H:%M}"


# =============================================================================
# AUDIT TRAIL — Every create, edit, delete action across the entire system
# =============================================================================
class AuditTrail(models.Model):

    ACTION_CHOICES = [
        ('CREATE',  'Create'),
        ('UPDATE',  'Update'),
        ('DELETE',  'Delete'),
        ('VIEW',    'View'),
        ('EXPORT',  'Export'),
        ('LOGIN',   'Login'),
        ('LOGOUT',  'Logout'),
    ]

    user        = models.ForeignKey(User, on_delete=models.RESTRICT, related_name='audit_logs')
    action      = models.CharField(max_length=10, choices=ACTION_CHOICES)
    module      = models.CharField(max_length=100)
    record_id   = models.CharField(max_length=50, blank=True)
    old_values  = models.JSONField(null=True, blank=True)
    new_values  = models.JSONField(null=True, blank=True)
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table  = 'audit_trail'
        ordering  = ['-created_at']
        indexes   = [
            models.Index(fields=['module', 'record_id']),
            models.Index(fields=['user', 'action']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.get_short_name()} {self.action} {self.module} [{self.created_at:%Y-%m-%d %H:%M}]"


# =============================================================================
# PASSWORD RESET TOKENS
# =============================================================================
class PasswordResetToken(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token      = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    used       = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'password_reset_tokens'

    def __str__(self):
        return f"Reset token for {self.user.email}"

    def is_valid(self):
        return not self.used and self.expires_at > timezone.now()


# =============================================================================
# SYSTEM SETTINGS — Key-value config for the application
# =============================================================================
class SystemSetting(models.Model):

    TYPE_CHOICES = [
        ('string',  'String'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('json',    'JSON'),
    ]

    setting_key   = models.CharField(max_length=150, unique=True)
    setting_value = models.TextField(blank=True)
    setting_type  = models.CharField(max_length=10, choices=TYPE_CHOICES, default='string')
    description   = models.TextField(blank=True)
    updated_by    = models.ForeignKey(
                        User, null=True, blank=True,
                        on_delete=models.SET_NULL, related_name='settings_updated'
                    )
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'system_settings'
        ordering = ['setting_key']

    def __str__(self):
        return f"{self.setting_key} = {self.setting_value}"

    def get_value(self):
        """Returns the value cast to the correct Python type."""
        if self.setting_type == 'integer':
            return int(self.setting_value)
        if self.setting_type == 'boolean':
            return self.setting_value.lower() in ('true', '1', 'yes')
        if self.setting_type == 'json':
            import json
            return json.loads(self.setting_value)
        return self.setting_value

    @classmethod
    def get(cls, key, default=None):
        """Convenient class method: SystemSetting.get('clinic_name')"""
        try:
            return cls.objects.get(setting_key=key).get_value()
        except cls.DoesNotExist:
            return default


# =============================================================================
# ACADEMIC SESSIONS
# =============================================================================
class AcademicSession(models.Model):
    session_name = models.CharField(max_length=20, unique=True)  # e.g. "2025/2026"
    start_date   = models.DateField()
    end_date     = models.DateField()
    is_current   = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'academic_sessions'
        ordering = ['-session_name']

    def __str__(self):
        return self.session_name

    def save(self, *args, **kwargs):
        # Only one session can be current at a time
        if self.is_current:
            AcademicSession.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_current(cls):
        return cls.objects.filter(is_current=True).first()



