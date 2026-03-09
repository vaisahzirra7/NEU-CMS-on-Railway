from django.db import models
from django.conf import settings
from django.utils import timezone


# ══════════════════════════════════════════════════════════════════════════════
# PRESCRIPTION
# ══════════════════════════════════════════════════════════════════════════════

class Prescription(models.Model):

    STATUS_CHOICES = [
        ('Pending',     'Pending'),
        ('In Progress', 'In Progress'),
        ('Dispensed',   'Dispensed'),
        ('Cancelled',   'Cancelled'),
    ]

    # Reference
    prescription_id = models.CharField(max_length=30, unique=True, editable=False)

    # Links
    patient     = models.ForeignKey(
                      'patients.Patient',
                      on_delete=models.PROTECT,
                      related_name='prescriptions',
                  )
    consultation = models.ForeignKey(
                      'consultations.Consultation',
                      on_delete=models.SET_NULL,
                      null=True, blank=True,
                      related_name='prescriptions',
                      help_text='Leave blank for walk-in / independent prescription',
                  )

    # Doctor who prescribed
    prescribed_by = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.SET_NULL, null=True,
                        related_name='prescriptions_written',
                    )

    # Dispensed by (nurse/pharmacist)
    dispensed_by  = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.SET_NULL, null=True, blank=True,
                        related_name='prescriptions_dispensed',
                    )
    dispensed_at  = models.DateTimeField(null=True, blank=True)

    # Notes
    notes  = models.TextField(blank=True, help_text='General prescription notes')

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    # Meta
    created_by = models.ForeignKey(
                     settings.AUTH_USER_MODEL,
                     on_delete=models.SET_NULL, null=True,
                     related_name='prescriptions_created',
                 )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering     = ['-created_at']
        verbose_name = 'Prescription'

    def __str__(self):
        return f'{self.prescription_id} — {self.patient}'

    def save(self, *args, **kwargs):
        if not self.prescription_id:
            self.prescription_id = self._generate_id()
        super().save(*args, **kwargs)

    def _generate_id(self):
        year   = timezone.now().year
        prefix = f'RX-{year}-'
        last   = Prescription.objects.filter(
                     prescription_id__startswith=prefix
                 ).order_by('-prescription_id').first()
        num = 1
        if last:
            try:
                num = int(last.prescription_id.split('-')[-1]) + 1
            except (ValueError, IndexError):
                pass
        return f'{prefix}{num:05d}'

    @property
    def status_color(self):
        return {
            'Pending':     'info',
            'In Progress': 'warning',
            'Dispensed':   'success',
            'Cancelled':   'danger',
        }.get(self.status, 'slate')

    @property
    def item_count(self):
        return self.items.count()


# ══════════════════════════════════════════════════════════════════════════════
# PRESCRIPTION ITEM — One drug line on a prescription
# ══════════════════════════════════════════════════════════════════════════════

class PrescriptionItem(models.Model):

    ROUTE_CHOICES = [
        ('Oral',        'Oral'),
        ('IV',          'Intravenous (IV)'),
        ('IM',          'Intramuscular (IM)'),
        ('SC',          'Subcutaneous (SC)'),
        ('Topical',     'Topical'),
        ('Sublingual',  'Sublingual'),
        ('Inhaled',     'Inhaled'),
        ('Rectal',      'Rectal'),
        ('Ophthalmic',  'Ophthalmic (Eye)'),
        ('Otic',        'Otic (Ear)'),
        ('Nasal',       'Nasal'),
        ('Other',       'Other'),
    ]

    FREQUENCY_CHOICES = [
        ('Once daily',        'Once daily (OD)'),
        ('Twice daily',       'Twice daily (BD)'),
        ('Three times daily', 'Three times daily (TDS)'),
        ('Four times daily',  'Four times daily (QDS)'),
        ('Every 4 hours',     'Every 4 hours'),
        ('Every 6 hours',     'Every 6 hours'),
        ('Every 8 hours',     'Every 8 hours'),
        ('At night',          'At night (nocte)'),
        ('As needed',         'As needed (PRN)'),
        ('Stat',              'Immediately (Stat)'),
        ('Other',             'Other'),
    ]

    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')

    # Drug — either from inventory or free-typed
    drug         = models.ForeignKey(
                       'inventory.Drug',
                       on_delete=models.SET_NULL,
                       null=True, blank=True,
                       related_name='prescription_items',
                   )
    drug_name    = models.CharField(max_length=200, help_text='Auto-filled from inventory or typed manually')

    # Prescription details
    dosage       = models.CharField(max_length=100, blank=True, help_text='e.g. 500mg, 2 tablets')
    frequency    = models.CharField(max_length=50, choices=FREQUENCY_CHOICES, blank=True)
    duration     = models.CharField(max_length=100, blank=True, help_text='e.g. 7 days, 2 weeks')
    route        = models.CharField(max_length=20, choices=ROUTE_CHOICES, default='Oral')
    quantity     = models.PositiveIntegerField(default=1, help_text='Total quantity to dispense')
    instructions = models.TextField(blank=True, help_text='Special instructions e.g. take with food')

    # Dispensing
    dispensed_qty = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.drug_name} — {self.prescription.prescription_id}'

    @property
    def is_from_inventory(self):
        return self.drug is not None