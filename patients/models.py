# ══════════════════════════════════════════════════════════════════════════════
# 
# Patients App - Models
# ══════════════════════════════════════════════════════════════════════════════

from django.db import models
from django.conf import settings
from django.utils import timezone


# ══════════════════════════════════════════════════════════════════════════════
# FACULTY
# ══════════════════════════════════════════════════════════════════════════════

class Faculty(models.Model):
    name       = models.CharField(max_length=200, unique=True)
    code       = models.CharField(max_length=20, unique=True, blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Faculties'
        ordering = ['name']

    def __str__(self):
        return self.name


# ══════════════════════════════════════════════════════════════════════════════
# DEPARTMENT
# ══════════════════════════════════════════════════════════════════════════════

class Department(models.Model):
    faculty    = models.ForeignKey(
                    Faculty, on_delete=models.CASCADE,
                    related_name='departments'
                 )
    name       = models.CharField(max_length=200)
    code       = models.CharField(max_length=20, blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['faculty__name', 'name']
        unique_together = ['faculty', 'name']

    def __str__(self):
        return f'{self.name} ({self.faculty.name})'


# ══════════════════════════════════════════════════════════════════════════════
# PROGRAMME
# ══════════════════════════════════════════════════════════════════════════════

class Programme(models.Model):
    faculty    = models.ForeignKey(
                    Faculty, on_delete=models.CASCADE,
                    related_name='programmes'
                 )
    department = models.ForeignKey(
                    Department, on_delete=models.CASCADE,
                    related_name='programmes',
                    null=True, blank=True
                 )
    name       = models.CharField(max_length=200)
    code       = models.CharField(max_length=20, blank=True)
    duration   = models.PositiveSmallIntegerField(
                    default=5,
                    help_text='Programme duration in years (e.g. 4, 5, 6)'
                 )
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['faculty__name', 'name']
        unique_together = ['faculty', 'name']

    def __str__(self):
        return f'{self.name} — {self.faculty.name}'


# ══════════════════════════════════════════════════════════════════════════════
# CHOICES
# ══════════════════════════════════════════════════════════════════════════════

BLOOD_GROUP_CHOICES = [
    ('A+', 'A+'), ('A-', 'A-'),
    ('B+', 'B+'), ('B-', 'B-'),
    ('AB+', 'AB+'), ('AB-', 'AB-'),
    ('O+', 'O+'),  ('O-', 'O-'),
    ('Unknown', 'Unknown'),
]

GENOTYPE_CHOICES = [
    ('AA', 'AA'), ('AS', 'AS'),
    ('SS', 'SS'), ('AC', 'AC'),
    ('SC', 'SC'), ('Unknown', 'Unknown'),
]

GENDER_CHOICES = [
    ('Male', 'Male'),
    ('Female', 'Female'),
    ('Other', 'Other'),
]

MARITAL_CHOICES = [
    ('Single', 'Single'),
    ('Married', 'Married'),
    ('Divorced', 'Divorced'),
    ('Widowed', 'Widowed'),
]

LEVEL_CHOICES = [
    ('100', '100 Level'),
    ('200', '200 Level'),
    ('300', '300 Level'),
    ('400', '400 Level'),
    ('500', '500 Level'),
    ('Postgraduate', 'Postgraduate'),
]

RELIGION_CHOICES = [
    ('Christianity', 'Christianity'),
    ('Islam', 'Islam'),
    ('Traditional', 'Traditional'),
    ('Other', 'Other'),
    ('None', 'None / Prefer not to say'),
]

PATIENT_TYPE_CHOICES = [
    ('Student',   'Student'),
    ('Staff',     'Staff'),
    ('Dependant', 'Dependant'),
    ('External',  'External / Walk-in'),
]


# ══════════════════════════════════════════════════════════════════════════════
# PATIENT
# ══════════════════════════════════════════════════════════════════════════════

def patient_photo_path(instance, filename):
    ext = filename.split('.')[-1].lower()
    return f'patients/photos/{instance.matric_no}.{ext}'


class Patient(models.Model):

    # ── Primary Identifier ────────────────────────────────────────────────────
    matric_no    = models.CharField(
                        max_length=30, unique=True,
                        verbose_name='Matric / Student ID',
                        help_text='This is the patient\'s unique identifier.'
                   )
    patient_type = models.CharField(
                        max_length=20,
                        choices=PATIENT_TYPE_CHOICES,
                        default='Student'
                   )

    # ── Personal ──────────────────────────────────────────────────────────────
    first_name      = models.CharField(max_length=100)
    last_name       = models.CharField(max_length=100)
    other_names     = models.CharField(max_length=100, blank=True)
    photo           = models.ImageField(upload_to=patient_photo_path, null=True, blank=True)
    date_of_birth   = models.DateField(null=True, blank=True)
    gender          = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    marital_status  = models.CharField(max_length=15, choices=MARITAL_CHOICES, blank=True)
    religion        = models.CharField(max_length=20, choices=RELIGION_CHOICES, blank=True)
    nationality     = models.CharField(max_length=100, blank=True, default='Nigerian')
    state_of_origin = models.CharField(max_length=100, blank=True)
    lga             = models.CharField(max_length=100, blank=True, verbose_name='LGA of Origin')
    home_address    = models.TextField(blank=True)
    phone           = models.CharField(max_length=20, blank=True)
    email           = models.EmailField(blank=True)
    nin             = models.CharField(max_length=20, blank=True, verbose_name='National ID (NIN)')

    # ── Academic ──────────────────────────────────────────────────────────────
    faculty          = models.ForeignKey(
                            Faculty, on_delete=models.SET_NULL,
                            null=True, blank=True, related_name='patients'
                       )
    department       = models.ForeignKey(
                            Department, on_delete=models.SET_NULL,
                            null=True, blank=True, related_name='patients'
                       )
    programme        = models.ForeignKey(
                            Programme, on_delete=models.SET_NULL,
                            null=True, blank=True, related_name='patients',
                            verbose_name='Programme of Study'
                       )
    level            = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True)
    academic_session = models.CharField(
                            max_length=20, blank=True,
                            verbose_name='Entry Session',
                            help_text='e.g. 2023/2024'
                       )

    # ── Medical ───────────────────────────────────────────────────────────────
    blood_group         = models.CharField(max_length=10, choices=BLOOD_GROUP_CHOICES, default='Unknown')
    genotype            = models.CharField(max_length=10, choices=GENOTYPE_CHOICES, default='Unknown')
    allergies           = models.TextField(blank=True, help_text='One allergy per line')
    chronic_conditions  = models.TextField(blank=True, help_text='One condition per line')
    disabilities        = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)
    surgical_history    = models.TextField(blank=True)
    family_history      = models.TextField(blank=True)

    # ── Emergency Contact ─────────────────────────────────────────────────────
    emergency_name         = models.CharField(max_length=200, blank=True)
    emergency_relationship = models.CharField(max_length=100, blank=True)
    emergency_phone        = models.CharField(max_length=20, blank=True)
    emergency_address      = models.TextField(blank=True)

    # ── Next of Kin ───────────────────────────────────────────────────────────
    nok_name         = models.CharField(max_length=200, blank=True, verbose_name='Next of Kin Name')
    nok_relationship = models.CharField(max_length=100, blank=True, verbose_name='Relationship')
    nok_phone        = models.CharField(max_length=20, blank=True, verbose_name='Next of Kin Phone')
    nok_address      = models.TextField(blank=True, verbose_name='Next of Kin Address')

    # ── Record Meta ───────────────────────────────────────────────────────────
    is_active     = models.BooleanField(default=True)
    notes         = models.TextField(blank=True, help_text='Internal notes visible to clinic staff only')
    registered_by = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='registered_patients',
                    )
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    # ── Future Sync ───────────────────────────────────────────────────────────
    external_id = models.CharField(max_length=100, blank=True)
    sync_source = models.CharField(max_length=50, blank=True, default='MANUAL',
                                   help_text='MANUAL | CSV_IMPORT | NEU_PORTAL')

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.get_full_name()} ({self.matric_no})'

    def get_full_name(self):
        parts = [self.first_name, self.other_names, self.last_name]
        return ' '.join(p for p in parts if p).strip()

    def get_short_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_initials(self):
        initials = ''
        if self.first_name: initials += self.first_name[0].upper()
        if self.last_name:  initials += self.last_name[0].upper()
        return initials or '??'

    def age(self):
        if not self.date_of_birth:
            return None
        today = timezone.now().date()
        dob   = self.date_of_birth
        return today.year - dob.year - (
            (today.month, today.day) < (dob.month, dob.day)
        )

    def allergies_list(self):
        return [a.strip() for a in self.allergies.splitlines() if a.strip()]

    def conditions_list(self):
        return [c.strip() for c in self.chronic_conditions.splitlines() if c.strip()]

    def programme_display(self):
        """Returns a clean programme/level string e.g. 'Medicine & Surgery · 300L'"""
        parts = []
        if self.programme:  parts.append(self.programme.name)
        if self.level:      parts.append(f'{self.level}L' if self.level.isdigit() else self.level)
        return ' · '.join(parts) if parts else '—'


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN REGISTRATION  (uncomment and add to your admin.py)
# ══════════════════════════════════════════════════════════════════════════════

# from django.contrib import admin
# from .models import Patient, Faculty, Department, Programme
#
# @admin.register(Faculty)
# class FacultyAdmin(admin.ModelAdmin):
#     list_display = ['name', 'code', 'is_active']
#
# @admin.register(Department)
# class DepartmentAdmin(admin.ModelAdmin):
#     list_display = ['name', 'faculty', 'is_active']
#     list_filter  = ['faculty']
#
# @admin.register(Programme)
# class ProgrammeAdmin(admin.ModelAdmin):
#     list_display = ['name', 'faculty', 'department', 'duration', 'is_active']
#     list_filter  = ['faculty']
#
# @admin.register(Patient)
# class PatientAdmin(admin.ModelAdmin):
#     list_display  = ['matric_no', 'get_full_name', 'programme', 'level', 'blood_group', 'is_active']
#     search_fields = ['first_name', 'last_name', 'matric_no', 'nin']
#     list_filter   = ['faculty', 'programme', 'level', 'blood_group', 'is_active']

