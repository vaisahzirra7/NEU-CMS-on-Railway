from django.db import models
from django.conf import settings
from django.utils import timezone


# ══════════════════════════════════════════════════════════════════════════════
# TEST CATALOG
# ══════════════════════════════════════════════════════════════════════════════

class LabTest(models.Model):
    """Master catalog of available lab tests."""
    name         = models.CharField(max_length=120, unique=True)
    short_code   = models.CharField(max_length=20, blank=True, help_text='e.g. MP, FBC, URS')
    description  = models.TextField(blank=True)
    reference_range = models.TextField(blank=True, help_text='Normal reference range text')
    unit         = models.CharField(max_length=40, blank=True, help_text='e.g. cells/μL, mg/dL')
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.short_code})' if self.short_code else self.name


# ══════════════════════════════════════════════════════════════════════════════
# LAB REQUEST
# ══════════════════════════════════════════════════════════════════════════════

class LabRequest(models.Model):

    STATUS_CHOICES = [
        ('Pending',     'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed',   'Completed'),
        ('Cancelled',   'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('Routine', 'Routine'),
        ('Urgent',  'Urgent'),
        ('STAT',    'STAT'),
    ]

    lab_id       = models.CharField(max_length=30, unique=True, editable=False)

    patient      = models.ForeignKey(
                       'patients.Patient',
                       on_delete=models.PROTECT,
                       related_name='lab_requests',
                   )
    consultation = models.ForeignKey(
                       'consultations.Consultation',
                       on_delete=models.SET_NULL,
                       null=True, blank=True,
                       related_name='lab_requests',
                       help_text='Leave blank for walk-in request',
                   )
    requested_by = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.SET_NULL, null=True,
                       related_name='lab_requests_made',
                   )
    processed_by = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.SET_NULL, null=True, blank=True,
                       related_name='lab_requests_processed',
                       help_text='Lab scientist who processed this request',
                   )
    processed_at = models.DateTimeField(null=True, blank=True)

    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    priority     = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Routine')
    clinical_notes = models.TextField(blank=True, help_text='Clinical history / notes for the lab')

    created_by   = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.SET_NULL, null=True,
                       related_name='lab_requests_created',
                   )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.lab_id} — {self.patient}'

    def save(self, *args, **kwargs):
        if not self.lab_id:
            self.lab_id = self._generate_id()
        super().save(*args, **kwargs)

    def _generate_id(self):
        year   = timezone.now().year
        prefix = f'LAB-{year}-'
        last   = LabRequest.objects.filter(
                     lab_id__startswith=prefix
                 ).order_by('-lab_id').first()
        num = 1
        if last:
            try:
                num = int(last.lab_id.split('-')[-1]) + 1
            except (ValueError, IndexError):
                pass
        return f'{prefix}{num:05d}'

    @property
    def status_color(self):
        return {
            'Pending':     'info',
            'In Progress': 'warning',
            'Completed':   'success',
            'Cancelled':   'slate',
        }.get(self.status, 'slate')

    @property
    def priority_color(self):
        return {
            'Routine': 'slate',
            'Urgent':  'warning',
            'STAT':    'danger',
        }.get(self.priority, 'slate')

    @property
    def test_count(self):
        return self.results.count()

    @property
    def completed_count(self):
        return self.results.exclude(result_value='').count()


# ══════════════════════════════════════════════════════════════════════════════
# LAB RESULT (one per test per request)
# ══════════════════════════════════════════════════════════════════════════════

class LabResult(models.Model):

    INTERPRETATION_CHOICES = [
        ('',         '— Not set —'),
        ('Normal',   'Normal'),
        ('Abnormal', 'Abnormal'),
        ('Critical', 'Critical'),
    ]

    request         = models.ForeignKey(LabRequest, on_delete=models.CASCADE, related_name='results')
    test            = models.ForeignKey(LabTest, on_delete=models.PROTECT, related_name='results')

    result_value    = models.TextField(blank=True, help_text='Free-form result text')
    reference_range = models.CharField(max_length=200, blank=True,
                                       help_text='Copied from catalog, editable per result')
    unit            = models.CharField(max_length=40, blank=True)
    interpretation  = models.CharField(max_length=20, choices=INTERPRETATION_CHOICES, blank=True)
    remarks         = models.TextField(blank=True, help_text='Additional remarks / comments')

    entered_by      = models.ForeignKey(
                          settings.AUTH_USER_MODEL,
                          on_delete=models.SET_NULL, null=True, blank=True,
                          related_name='lab_results_entered',
                      )
    entered_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering    = ['test__name']
        unique_together = [['request', 'test']]

    def __str__(self):
        return f'{self.request.lab_id} — {self.test.name}'

    @property
    def has_result(self):
        return bool(self.result_value.strip())

    @property
    def interpretation_color(self):
        return {
            'Normal':   'success',
            'Abnormal': 'warning',
            'Critical': 'danger',
        }.get(self.interpretation, 'slate')