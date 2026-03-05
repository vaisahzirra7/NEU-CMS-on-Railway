from django.db import models
from django.conf import settings


# ══════════════════════════════════════════════════════════════════════════════
# APPOINTMENT MODEL
# ══════════════════════════════════════════════════════════════════════════════

class Appointment(models.Model):

    TYPE_CHOICES = [
        ('General Consultation', 'General Consultation'),
        ('Follow-up',            'Follow-up'),
        ('Dental',               'Dental'),
        ('Eye Clinic',           'Eye Clinic'),
        ('Antenatal',            'Antenatal'),
        ('Emergency',            'Emergency'),
        ('Other',                'Other'),
    ]

    STATUS_CHOICES = [
        ('Scheduled',   'Scheduled'),
        ('In Progress', 'In Progress'),
        ('Completed',   'Completed'),
        ('Cancelled',   'Cancelled'),
    ]

    TIME_SLOTS = [
        ('08:00', '8:00 AM'),
        ('08:30', '8:30 AM'),
        ('09:00', '9:00 AM'),
        ('09:30', '9:30 AM'),
        ('10:00', '10:00 AM'),
        ('10:30', '10:30 AM'),
        ('11:00', '11:00 AM'),
        ('11:30', '11:30 AM'),
        ('12:00', '12:00 PM'),
        ('12:30', '12:30 PM'),
        ('13:00', '1:00 PM'),
        ('13:30', '1:30 PM'),
        ('14:00', '2:00 PM'),
        ('14:30', '2:30 PM'),
        ('15:00', '3:00 PM'),
        ('15:30', '3:30 PM'),
        ('16:00', '4:00 PM'),
        ('16:30', '4:30 PM'),
    ]

    # ── Reference ────────────────────────────────────────────────────────────
    appointment_id = models.CharField(
        max_length=30, unique=True, editable=False,
        help_text='Auto-generated e.g. APT-2024-00001'
    )

    # ── Patient ───────────────────────────────────────────────────────────────
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.PROTECT,
        related_name='appointments',
    )

    # ── Appointment Details ───────────────────────────────────────────────────
    appointment_type = models.CharField(
        max_length=50, choices=TYPE_CHOICES,
        default='General Consultation'
    )
    custom_type = models.CharField(
        max_length=100, blank=True,
        help_text='Fill in if type is "Other"'
    )
    appointment_date = models.DateField()
    time_slot        = models.CharField(max_length=5, choices=TIME_SLOTS)
    reason           = models.TextField(blank=True, help_text='Reason for visit')
    notes            = models.TextField(blank=True, help_text='Staff notes')

    # ── Assignment ────────────────────────────────────────────────────────────
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_appointments',
        help_text='Doctor or staff member handling this appointment',
    )

    # ── Status ────────────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='Scheduled'
    )
    cancellation_reason = models.TextField(
        blank=True, help_text='Required if cancelled'
    )

    # ── Meta ──────────────────────────────────────────────────────────────────
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_appointments',
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-appointment_date', '-time_slot']
        verbose_name        = 'Appointment'
        verbose_name_plural = 'Appointments'

    def __str__(self):
        return f'{self.appointment_id} — {self.patient} ({self.appointment_date})'

    def save(self, *args, **kwargs):
        if not self.appointment_id:
            self.appointment_id = self._generate_id()
        super().save(*args, **kwargs)

    def _generate_id(self):
        from django.utils import timezone
        year    = timezone.now().year
        prefix  = f'APT-{year}-'
        last    = Appointment.objects.filter(
                      appointment_id__startswith=prefix
                  ).order_by('-appointment_id').first()
        if last:
            try:
                num = int(last.appointment_id.split('-')[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        return f'{prefix}{num:05d}'

    def get_type_display_full(self):
        if self.appointment_type == 'Other' and self.custom_type:
            return self.custom_type
        return self.appointment_type

    @property
    def status_color(self):
        return {
            'Scheduled':   'info',
            'In Progress': 'warning',
            'Completed':   'success',
            'Cancelled':   'danger',
        }.get(self.status, 'slate')

    @property
    def time_display(self):
        for val, label in self.TIME_SLOTS:
            if val == self.time_slot:
                return label
        return self.time_slot