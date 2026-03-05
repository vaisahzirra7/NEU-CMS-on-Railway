from django.db import models
from django.conf import settings


# ══════════════════════════════════════════════════════════════════════════════
# CONSULTATION MODEL
# ══════════════════════════════════════════════════════════════════════════════

class Consultation(models.Model):

    STATUS_CHOICES = [
        ('Open',        'Open'),
        ('In Progress', 'In Progress'),
        ('Completed',   'Completed'),
    ]

    # ── Reference ─────────────────────────────────────────────────────────────
    consultation_id = models.CharField(
        max_length=30, unique=True, editable=False,
        help_text='Auto-generated e.g. CON-2024-00001'
    )

    # ── Links ──────────────────────────────────────────────────────────────────
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.PROTECT,
        related_name='consultations',
    )
    appointment = models.OneToOneField(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='consultation',
        help_text='Leave blank for walk-in consultations',
    )

    # ── Doctor ─────────────────────────────────────────────────────────────────
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='consultations_as_doctor',
    )

    # ── Vitals ─────────────────────────────────────────────────────────────────
    bp_systolic   = models.PositiveIntegerField(null=True, blank=True, help_text='mmHg')
    bp_diastolic  = models.PositiveIntegerField(null=True, blank=True, help_text='mmHg')
    temperature   = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, help_text='°C')
    pulse         = models.PositiveIntegerField(null=True, blank=True, help_text='bpm')
    # Custom extra vitals stored as JSON  {label: value}
    extra_vitals  = models.JSONField(default=dict, blank=True)

    # ── Clinical Notes ─────────────────────────────────────────────────────────
    chief_complaint = models.TextField(blank=True, help_text='Patient\'s main complaint')
    history         = models.TextField(blank=True, help_text='History of presenting illness')
    examination     = models.TextField(blank=True, help_text='Physical examination findings')

    # ── Diagnosis ──────────────────────────────────────────────────────────────
    diagnosis       = models.TextField(blank=True, help_text='Doctor\'s diagnosis (free text)')
    icd10_code      = models.CharField(max_length=20, blank=True, help_text='Optional ICD-10 code e.g. J06.9')
    icd10_label     = models.CharField(max_length=255, blank=True, help_text='ICD-10 description')

    # ── Management ─────────────────────────────────────────────────────────────
    management_plan = models.TextField(blank=True, help_text='Treatment and management plan')
    follow_up_date  = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)

    # ── End actions (flags — actual records created in respective modules) ──────
    has_prescription  = models.BooleanField(default=False)
    has_lab_request   = models.BooleanField(default=False)
    has_ward_referral = models.BooleanField(default=False)
    has_clearance     = models.BooleanField(default=False)

    # ── Status ────────────────────────────────────────────────────────────────
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')

    # ── Meta ──────────────────────────────────────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_consultations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Consultation'
        verbose_name_plural = 'Consultations'

    def __str__(self):
        return f'{self.consultation_id} — {self.patient} ({self.created_at.date()})'

    def save(self, *args, **kwargs):
        if not self.consultation_id:
            self.consultation_id = self._generate_id()
        super().save(*args, **kwargs)

    def _generate_id(self):
        from django.utils import timezone
        year   = timezone.now().year
        prefix = f'CON-{year}-'
        last   = Consultation.objects.filter(
                     consultation_id__startswith=prefix
                 ).order_by('-consultation_id').first()
        if last:
            try:
                num = int(last.consultation_id.split('-')[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        return f'{prefix}{num:05d}'

    @property
    def bp_display(self):
        if self.bp_systolic and self.bp_diastolic:
            return f'{self.bp_systolic}/{self.bp_diastolic} mmHg'
        return '—'

    @property
    def status_color(self):
        return {
            'Open':        'info',
            'In Progress': 'warning',
            'Completed':   'success',
        }.get(self.status, 'slate')