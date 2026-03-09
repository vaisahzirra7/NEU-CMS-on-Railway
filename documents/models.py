from django.db import models
from django.conf import settings
from django.utils import timezone
import datetime


# ══════════════════════════════════════════════════════════════════════════════
# OFFICIAL DOCUMENT
# ══════════════════════════════════════════════════════════════════════════════

class OfficialDocument(models.Model):

    DOC_TYPE_CHOICES = [
        ('sick_leave',   'Sick Leave Letter'),
        ('fit_to_resume','Medical Certificate (Fit to Resume)'),
        ('referral',     'Referral Letter'),
        ('medical_report','Medical Report / Summary'),
    ]

    STATUS_CHOICES = [
        ('draft',    'Draft'),
        ('issued',   'Issued'),
        ('revoked',  'Revoked'),
    ]

    # ── Identity ──────────────────────────────────────────────────────────────
    doc_id      = models.CharField(max_length=20, unique=True, editable=False)
    doc_type    = models.CharField(max_length=30, choices=DOC_TYPE_CHOICES)
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')

    # ── Relations ─────────────────────────────────────────────────────────────
    patient     = models.ForeignKey(
        'patients.Patient', on_delete=models.PROTECT, related_name='official_documents'
    )
    consultation = models.ForeignKey(
        'consultations.Consultation', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='official_documents'
    )
    issued_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='documents_issued'
    )

    # ── Dates ─────────────────────────────────────────────────────────────────
    date_issued     = models.DateField(default=datetime.date.today)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    # ── Sick Leave specific ────────────────────────────────────────────────────
    leave_from      = models.DateField(null=True, blank=True)
    leave_to        = models.DateField(null=True, blank=True)

    # ── Fit to Resume specific ─────────────────────────────────────────────────
    resume_date     = models.DateField(null=True, blank=True)

    # ── Referral specific ─────────────────────────────────────────────────────
    referral_to         = models.CharField(max_length=200, blank=True)   # facility name
    referral_department = models.CharField(max_length=200, blank=True)
    referral_reason     = models.TextField(blank=True)
    referral_urgency    = models.CharField(max_length=10, blank=True, choices=[
        ('routine','Routine'), ('urgent','Urgent'), ('emergency','Emergency')
    ])

    # ── Shared content fields ──────────────────────────────────────────────────
    diagnosis       = models.TextField(blank=True)
    notes           = models.TextField(blank=True)          # free body text / additional notes
    additional_info = models.TextField(blank=True)          # shown on printed doc

    # ── Verification ──────────────────────────────────────────────────────────
    verification_code = models.CharField(max_length=12, unique=True, editable=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.doc_id} — {self.get_doc_type_display()} ({self.patient})'

    # ── Auto-generate IDs ──────────────────────────────────────────────────────
    def save(self, *args, **kwargs):
        if not self.doc_id:
            year  = timezone.now().year
            last  = OfficialDocument.objects.filter(doc_id__startswith=f'DOC-{year}-').count()
            self.doc_id = f'DOC-{year}-{last + 1:05d}'
        if not self.verification_code:
            import secrets, string
            alphabet = string.ascii_uppercase + string.digits
            self.verification_code = ''.join(secrets.choice(alphabet) for _ in range(10))
        super().save(*args, **kwargs)

    # ── Helpers ───────────────────────────────────────────────────────────────
    @property
    def type_icon(self):
        return {
            'sick_leave':    '🤒',
            'fit_to_resume': '✅',
            'referral':      '🏥',
            'medical_report':'📋',
        }.get(self.doc_type, '📄')

    @property
    def type_color(self):
        return {
            'sick_leave':    'amber',
            'fit_to_resume': 'green',
            'referral':      'blue',
            'medical_report':'slate',
        }.get(self.doc_type, 'slate')

    @property
    def leave_days(self):
        if self.leave_from and self.leave_to:
            return (self.leave_to - self.leave_from).days + 1
        return None

    @property
    def is_issued(self):
        return self.status == 'issued'