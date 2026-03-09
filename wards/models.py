from django.db import models
from django.conf import settings
from django.utils import timezone


# ══════════════════════════════════════════════════════════════════════════════
# WARD
# ══════════════════════════════════════════════════════════════════════════════

class Ward(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def total_beds(self):
        return self.beds.count()

    @property
    def available_beds(self):
        return self.beds.filter(status='Available').count()

    @property
    def occupied_beds(self):
        return self.beds.filter(status='Occupied').count()

    @property
    def reserved_beds(self):
        return self.beds.filter(status='Reserved').count()

    @property
    def maintenance_beds(self):
        return self.beds.filter(status='Maintenance').count()

    @property
    def occupancy_percent(self):
        total = self.total_beds
        if total == 0:
            return 0
        return round((self.occupied_beds / total) * 100)


# ══════════════════════════════════════════════════════════════════════════════
# BED
# ══════════════════════════════════════════════════════════════════════════════

class Bed(models.Model):

    STATUS_CHOICES = [
        ('Available',   'Available'),
        ('Occupied',    'Occupied'),
        ('Reserved',    'Reserved'),
        ('Maintenance', 'Maintenance'),
    ]

    ward       = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='beds')
    bed_number = models.CharField(max_length=20, help_text='e.g. Bed 1, B-01')
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Available')
    notes      = models.TextField(blank=True, help_text='e.g. Near window, isolation bed')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ['ward', 'bed_number']
        unique_together = [['ward', 'bed_number']]

    def __str__(self):
        return f'{self.ward.name} — {self.bed_number}'

    @property
    def current_admission(self):
        return self.admissions.filter(status='Admitted').first()

    @property
    def status_color(self):
        return {
            'Available':   'success',
            'Occupied':    'danger',
            'Reserved':    'warning',
            'Maintenance': 'slate',
        }.get(self.status, 'slate')


# ══════════════════════════════════════════════════════════════════════════════
# ADMISSION
# ══════════════════════════════════════════════════════════════════════════════

class Admission(models.Model):

    STATUS_CHOICES = [
        ('Admitted',    'Admitted'),
        ('Transferred', 'Transferred'),
        ('Discharged',  'Discharged'),
    ]

    admission_id = models.CharField(max_length=30, unique=True, editable=False)

    patient      = models.ForeignKey(
                       'patients.Patient',
                       on_delete=models.PROTECT,
                       related_name='admissions',
                   )
    ward         = models.ForeignKey(Ward, on_delete=models.PROTECT, related_name='admissions')
    bed          = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='admissions')

    consultation = models.ForeignKey(
                       'consultations.Consultation',
                       on_delete=models.SET_NULL,
                       null=True, blank=True,
                       related_name='admissions',
                   )
    admitting_doctor = models.ForeignKey(
                           settings.AUTH_USER_MODEL,
                           on_delete=models.SET_NULL, null=True,
                           related_name='admissions_made',
                       )

    reason       = models.TextField(help_text='Reason for admission / diagnosis')
    notes        = models.TextField(blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Admitted')

    admitted_at  = models.DateTimeField(default=timezone.now)
    discharged_at= models.DateTimeField(null=True, blank=True)
    discharge_notes = models.TextField(blank=True)

    discharged_by= models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.SET_NULL, null=True, blank=True,
                       related_name='admissions_discharged',
                   )

    created_by   = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.SET_NULL, null=True,
                       related_name='admissions_created',
                   )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-admitted_at']

    def __str__(self):
        return f'{self.admission_id} — {self.patient}'

    def save(self, *args, **kwargs):
        if not self.admission_id:
            self.admission_id = self._generate_id()
        super().save(*args, **kwargs)

    def _generate_id(self):
        year   = timezone.now().year
        prefix = f'ADM-{year}-'
        last   = Admission.objects.filter(
                     admission_id__startswith=prefix
                 ).order_by('-admission_id').first()
        num = 1
        if last:
            try:
                num = int(last.admission_id.split('-')[-1]) + 1
            except (ValueError, IndexError):
                pass
        return f'{prefix}{num:05d}'

    @property
    def days_admitted(self):
        end = self.discharged_at or timezone.now()
        return (end - self.admitted_at).days

    @property
    def status_color(self):
        return {
            'Admitted':    'success',
            'Transferred': 'warning',
            'Discharged':  'slate',
        }.get(self.status, 'slate')


# ══════════════════════════════════════════════════════════════════════════════
# TRANSFER LOG
# ══════════════════════════════════════════════════════════════════════════════

class TransferLog(models.Model):
    admission     = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='transfers')
    from_ward     = models.ForeignKey(Ward, on_delete=models.PROTECT, related_name='transfers_out')
    from_bed      = models.ForeignKey(Bed,  on_delete=models.PROTECT, related_name='transfers_out')
    to_ward       = models.ForeignKey(Ward, on_delete=models.PROTECT, related_name='transfers_in')
    to_bed        = models.ForeignKey(Bed,  on_delete=models.PROTECT, related_name='transfers_in')
    reason        = models.TextField(blank=True)
    transferred_by= models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.SET_NULL, null=True,
                        related_name='transfers_done',
                    )
    transferred_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-transferred_at']

    def __str__(self):
        return f'Transfer {self.admission.admission_id}: {self.from_bed} → {self.to_bed}'