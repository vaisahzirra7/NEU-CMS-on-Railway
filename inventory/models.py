from django.db import models
from django.conf import settings
from django.utils import timezone


# ══════════════════════════════════════════════════════════════════════════════
# DRUG CATEGORY
# ══════════════════════════════════════════════════════════════════════════════

class DrugCategory(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering    = ['name']
        verbose_name_plural = 'Drug Categories'

    def __str__(self):
        return self.name


# ══════════════════════════════════════════════════════════════════════════════
# DRUG — Master catalogue entry
# ══════════════════════════════════════════════════════════════════════════════

class Drug(models.Model):

    DOSAGE_FORM_CHOICES = [
        ('Tablet',     'Tablet'),
        ('Capsule',    'Capsule'),
        ('Syrup',      'Syrup'),
        ('Suspension', 'Suspension'),
        ('Injection',  'Injection'),
        ('Infusion',   'Infusion'),
        ('Cream',      'Cream'),
        ('Ointment',   'Ointment'),
        ('Drops',      'Drops'),
        ('Inhaler',    'Inhaler'),
        ('Suppository','Suppository'),
        ('Patch',      'Patch'),
        ('Other',      'Other'),
    ]

    UNIT_CHOICES = [
        ('Tablets',  'Tablets'),
        ('Capsules', 'Capsules'),
        ('Bottles',  'Bottles'),
        ('Vials',    'Vials'),
        ('Ampoules', 'Ampoules'),
        ('Sachets',  'Sachets'),
        ('Tubes',    'Tubes'),
        ('Packs',    'Packs'),
        ('mL',       'mL'),
        ('Units',    'Units'),
    ]

    # Identity
    drug_code    = models.CharField(max_length=30, unique=True, editable=False)
    name         = models.CharField(max_length=200, help_text='Brand/trade name')
    generic_name = models.CharField(max_length=200, blank=True, help_text='Generic/INN name')
    category     = models.ForeignKey(
                        DrugCategory, on_delete=models.SET_NULL,
                        null=True, blank=True, related_name='drugs'
                   )

    # Properties
    dosage_form  = models.CharField(max_length=20, choices=DOSAGE_FORM_CHOICES)
    strength     = models.CharField(max_length=100, blank=True, help_text='e.g. 500mg, 250mg/5mL')
    unit         = models.CharField(max_length=20, choices=UNIT_CHOICES, default='Tablets')

    # Stock control
    reorder_level = models.PositiveIntegerField(default=10, help_text='Alert when stock falls below this')

    # Supplier
    supplier      = models.CharField(max_length=200, blank=True)
    manufacturer  = models.CharField(max_length=200, blank=True)

    # Meta
    description  = models.TextField(blank=True)
    is_active    = models.BooleanField(default=True)
    created_by   = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.SET_NULL, null=True,
                        related_name='drugs_added'
                   )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        parts = [self.name]
        if self.strength:
            parts.append(self.strength)
        if self.dosage_form:
            parts.append(self.dosage_form)
        return ' — '.join(parts)

    def save(self, *args, **kwargs):
        if not self.drug_code:
            self.drug_code = self._generate_code()
        super().save(*args, **kwargs)

    def _generate_code(self):
        from django.utils import timezone
        year   = timezone.now().year
        prefix = f'DRG-{year}-'
        last   = Drug.objects.filter(
                     drug_code__startswith=prefix
                 ).order_by('-drug_code').first()
        num = 1
        if last:
            try:
                num = int(last.drug_code.split('-')[-1]) + 1
            except (ValueError, IndexError):
                pass
        return f'{prefix}{num:04d}'

    # ── Stock helpers ──────────────────────────────────────────────────────────

    @property
    def total_stock(self):
        """Sum of all non-expired, active batch quantities."""
        return self.batches.filter(
            is_active=True
        ).aggregate(
            total=models.Sum('quantity_remaining')
        )['total'] or 0

    @property
    def is_low_stock(self):
        return self.total_stock <= self.reorder_level

    @property
    def has_expired_batches(self):
        return self.batches.filter(
            is_active=True,
            expiry_date__lt=timezone.localdate()
        ).exists()

    @property
    def stock_status(self):
        if self.total_stock == 0:
            return 'out'
        if self.is_low_stock:
            return 'low'
        return 'ok'


# ══════════════════════════════════════════════════════════════════════════════
# STOCK BATCH — Every delivery of a drug creates a batch
# ══════════════════════════════════════════════════════════════════════════════

class StockBatch(models.Model):

    drug              = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='batches')
    batch_number      = models.CharField(max_length=100, blank=True, help_text='Manufacturer batch/lot number')
    quantity_received = models.PositiveIntegerField()
    quantity_remaining= models.PositiveIntegerField()
    unit_cost         = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expiry_date       = models.DateField(null=True, blank=True)
    date_received     = models.DateField(default=timezone.localdate)
    supplier          = models.CharField(max_length=200, blank=True)
    notes             = models.TextField(blank=True)
    is_active         = models.BooleanField(default=True)
    received_by       = models.ForeignKey(
                            settings.AUTH_USER_MODEL,
                            on_delete=models.SET_NULL, null=True,
                            related_name='batches_received'
                        )
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['expiry_date', 'created_at']
        verbose_name_plural = 'Stock Batches'

    def __str__(self):
        return f'{self.drug.name} — Batch {self.batch_number or self.pk} ({self.quantity_remaining} left)'

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.localdate()
        return False

    @property
    def days_to_expiry(self):
        if self.expiry_date:
            return (self.expiry_date - timezone.localdate()).days
        return None

    @property
    def expiry_status(self):
        days = self.days_to_expiry
        if days is None:
            return 'unknown'
        if days < 0:
            return 'expired'
        if days <= 30:
            return 'critical'
        if days <= 90:
            return 'warning'
        return 'ok'


# ══════════════════════════════════════════════════════════════════════════════
# STOCK TRANSACTION — Log of every stock movement (in/out)
# ══════════════════════════════════════════════════════════════════════════════

class StockTransaction(models.Model):

    TYPE_CHOICES = [
        ('IN',       'Stock In'),
        ('OUT',      'Dispensed'),
        ('ADJUST',   'Adjustment'),
        ('EXPIRED',  'Expired/Removed'),
        ('RETURNED', 'Returned'),
    ]

    drug         = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='transactions')
    batch        = models.ForeignKey(StockBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    type         = models.CharField(max_length=10, choices=TYPE_CHOICES)
    quantity     = models.IntegerField(help_text='Positive for IN, negative for OUT')
    reference    = models.CharField(max_length=100, blank=True, help_text='e.g. prescription ID, batch number')
    notes        = models.TextField(blank=True)
    performed_by = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.SET_NULL, null=True,
                        related_name='stock_transactions'
                   )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.drug.name} {self.type} {self.quantity} @ {self.created_at:%Y-%m-%d}'