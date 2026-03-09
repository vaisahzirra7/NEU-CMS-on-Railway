from django.db import models
from django.conf import settings
from django.utils import timezone
import json


# ══════════════════════════════════════════════════════════════════════════════
# DEFAULT QUESTION TEMPLATE
# Global master list — staff edits once, sessions preload from here
# ══════════════════════════════════════════════════════════════════════════════

class DefaultQuestion(models.Model):

    TYPE_CHOICES = [
        ('text',     'Short Text'),
        ('textarea', 'Long Text'),
        ('single',   'Single Choice'),
        ('multiple', 'Multiple Choice'),
    ]

    FIELD_KEY_CHOICES = [
        ('',                   '— None —'),
        ('blood_group',        'Blood Group'),
        ('genotype',           'Genotype'),
        ('known_allergies',    'Known Allergies'),
        ('chronic_conditions', 'Chronic Conditions'),
        ('disabilities',       'Disabilities'),
        ('blood_pressure',     'Blood Pressure'),
    ]

    question_text = models.CharField(max_length=500)
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='text')
    choices_json  = models.TextField(blank=True, default='[]')
    is_required   = models.BooleanField(default=False)
    field_key     = models.CharField(max_length=30, choices=FIELD_KEY_CHOICES, blank=True)
    order         = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'pk']

    def __str__(self):
        return f'[Default] {self.question_text[:60]}'

    @property
    def choices(self):
        try:
            return json.loads(self.choices_json) if self.choices_json else []
        except (json.JSONDecodeError, TypeError):
            return []


# ══════════════════════════════════════════════════════════════════════════════
# CLEARANCE SESSION
# ══════════════════════════════════════════════════════════════════════════════

class ClearanceSession(models.Model):

    STREAM_CHOICES = [
        ('I',  'Stream I'),
        ('II', 'Stream II'),
    ]

    academic_session = models.CharField(max_length=25, help_text='e.g. 2024/2025')
    stream           = models.CharField(max_length=5, choices=STREAM_CHOICES)
    title            = models.CharField(
        max_length=200, blank=True,
        help_text='Optional display title e.g. "2024/2025 Stream I Medical Clearance"'
    )
    opens_at         = models.DateTimeField()
    closes_at        = models.DateTimeField()
    is_active        = models.BooleanField(default=True)
    instructions     = models.TextField(blank=True)
    created_by       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='clearance_sessions_created'
    )
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-academic_session', 'stream']
        unique_together = [['academic_session', 'stream']]

    def __str__(self):
        return f'{self.academic_session} Stream {self.stream}'

    @property
    def display_title(self):
        return self.title or f'{self.academic_session} Stream {self.stream} Medical Clearance'

    @property
    def is_open(self):
        now = timezone.now()
        return self.is_active and self.opens_at <= now <= self.closes_at

    @property
    def status_label(self):
        now = timezone.now()
        if not self.is_active: return 'Inactive'
        if now < self.opens_at: return 'Upcoming'
        if now > self.closes_at: return 'Closed'
        return 'Open'

    @property
    def status_color(self):
        return {'Open':'success','Upcoming':'info','Closed':'slate','Inactive':'slate'}.get(self.status_label,'slate')

    @property
    def submission_count(self):
        return self.submissions.count()

    @property
    def approved_count(self):
        return self.submissions.filter(status='Approved').count()


# ══════════════════════════════════════════════════════════════════════════════
# CLEARANCE QUESTION
# ══════════════════════════════════════════════════════════════════════════════

class ClearanceQuestion(models.Model):

    TYPE_CHOICES = [
        ('text',     'Short Text'),
        ('textarea', 'Long Text'),
        ('single',   'Single Choice'),
        ('multiple', 'Multiple Choice'),
    ]

    FIELD_KEY_CHOICES = [
        ('',                   '— None —'),
        ('blood_group',        'Blood Group'),
        ('genotype',           'Genotype'),
        ('known_allergies',    'Known Allergies'),
        ('chronic_conditions', 'Chronic Conditions'),
        ('disabilities',       'Disabilities'),
        ('blood_pressure',     'Blood Pressure'),
    ]

    session       = models.ForeignKey(ClearanceSession, on_delete=models.CASCADE, related_name='questions')
    question_text = models.CharField(max_length=500)
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='text')
    choices_json  = models.TextField(blank=True, default='[]')
    is_required   = models.BooleanField(default=False)
    field_key     = models.CharField(max_length=30, choices=FIELD_KEY_CHOICES, blank=True)
    order         = models.PositiveIntegerField(default=0)
    is_preloaded  = models.BooleanField(
        default=False,
        help_text='Copied from default template — edit via Default Questions page only.'
    )

    class Meta:
        ordering = ['order', 'pk']

    def __str__(self):
        return f'[{self.session}] {self.question_text[:60]}'

    @property
    def choices(self):
        try:
            return json.loads(self.choices_json) if self.choices_json else []
        except (json.JSONDecodeError, TypeError):
            return []

    @choices.setter
    def choices(self, value):
        self.choices_json = json.dumps(value)


# ══════════════════════════════════════════════════════════════════════════════
# CLEARANCE SUBMISSION
# ══════════════════════════════════════════════════════════════════════════════

class ClearanceSubmission(models.Model):

    STATUS_CHOICES = [
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    submission_id       = models.CharField(max_length=30, unique=True, editable=False)
    session             = models.ForeignKey(ClearanceSession, on_delete=models.PROTECT, related_name='submissions')
    patient             = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, related_name='clearance_submissions')
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Approved')

    # Resubmit permission — staff must grant
    resubmit_granted    = models.BooleanField(default=False)
    resubmit_granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resubmit_grants'
    )
    resubmit_granted_at = models.DateTimeField(null=True, blank=True)

    # Per-student deadline extension
    extended_deadline   = models.DateTimeField(
        null=True, blank=True,
        help_text='If set, student can submit until this date even if session is closed'
    )

    submitted_at        = models.DateTimeField(auto_now_add=True)
    reviewed_by         = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='clearances_reviewed'
    )
    reviewed_at         = models.DateTimeField(null=True, blank=True)
    remarks             = models.TextField(blank=True)

    class Meta:
        ordering = ['-submitted_at']
        unique_together = [['session', 'patient']]

    def __str__(self):
        return f'{self.submission_id} — {self.patient}'

    def save(self, *args, **kwargs):
        if not self.submission_id:
            self.submission_id = self._generate_id()
        super().save(*args, **kwargs)

    def _generate_id(self):
        year   = timezone.now().year
        prefix = f'CLR-{year}-'
        last   = ClearanceSubmission.objects.filter(
            submission_id__startswith=prefix
        ).order_by('-submission_id').first()
        num = 1
        if last:
            try:
                num = int(last.submission_id.split('-')[-1]) + 1
            except (ValueError, IndexError):
                pass
        return f'{prefix}{num:05d}'

    @property
    def status_color(self):
        return {'Approved':'success','Rejected':'danger'}.get(self.status,'slate')

    def can_student_access(self):
        """Can the student currently submit / resubmit?"""
        now = timezone.now()
        if self.extended_deadline and now <= self.extended_deadline:
            return True
        return self.session.is_open

    def sync_to_patient(self):
        """Write medical field answers back to the patient record."""
        patient = self.patient
        changed = False
        FIELD_MAP = {
            'blood_group':        'blood_group',
            'genotype':           'genotype',
            'known_allergies':    'known_allergies',
            'chronic_conditions': 'chronic_conditions',
            'disabilities':       'disabilities',
            'blood_pressure':     'blood_pressure',
        }
        for answer in self.answers.select_related('question').all():
            key = answer.question.field_key
            if key and key in FIELD_MAP:
                if hasattr(patient, FIELD_MAP[key]):
                    setattr(patient, FIELD_MAP[key], answer.display_answer)
                    changed = True
        if changed:
            patient.save()


# ══════════════════════════════════════════════════════════════════════════════
# CLEARANCE ANSWER
# ══════════════════════════════════════════════════════════════════════════════

class ClearanceAnswer(models.Model):
    submission  = models.ForeignKey(ClearanceSubmission, on_delete=models.CASCADE, related_name='answers')
    question    = models.ForeignKey(ClearanceQuestion, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField(blank=True)

    class Meta:
        unique_together = [['submission', 'question']]

    def __str__(self):
        return f'{self.submission.submission_id} — Q{self.question.order}'

    @property
    def display_answer(self):
        if self.question.question_type == 'multiple':
            try:
                items = json.loads(self.answer_text)
                return ', '.join(items) if items else '—'
            except (json.JSONDecodeError, TypeError):
                return self.answer_text or '—'
        return self.answer_text or '—'