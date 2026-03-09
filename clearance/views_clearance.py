import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.permissions import permission_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_POST

from clearance.models import ClearanceSession, ClearanceQuestion, ClearanceSubmission, ClearanceAnswer, DefaultQuestion


# ══════════════════════════════════════════════════════════════════════════════
# STAFF — SESSION LIST / DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('clearance', 'view')
def clearance_dashboard(request):
    sessions = ClearanceSession.objects.all()
    context  = {
        'sessions':     sessions,
        'total_submissions': ClearanceSubmission.objects.count(),
        'approved_ct':  ClearanceSubmission.objects.filter(status='Approved').count(),
    }
    return render(request, 'clearance/dashboard.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# STAFF — CREATE / EDIT SESSION
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('clearance', 'create')
def session_create(request):
    if request.method == 'POST':
        p = request.POST
        academic_session = p.get('academic_session', '').strip()
        stream           = p.get('stream', '').strip()
        title            = p.get('title', '').strip()
        opens_at         = p.get('opens_at', '').strip()
        closes_at        = p.get('closes_at', '').strip()
        instructions     = p.get('instructions', '').strip()

        errors = []
        if not academic_session: errors.append('Academic session is required.')
        if not stream:           errors.append('Stream is required.')
        if not opens_at:         errors.append('Opening date/time is required.')
        if not closes_at:        errors.append('Closing date/time is required.')
        if ClearanceSession.objects.filter(academic_session=academic_session, stream=stream).exists():
            errors.append(f'A clearance session for {academic_session} Stream {stream} already exists.')

        if errors:
            for e in errors: messages.error(request, e)
            return render(request, 'clearance/session_form.html', {'post': p, 'action': 'Create'})

        session = ClearanceSession.objects.create(
            academic_session=academic_session,
            stream=stream,
            title=title,
            opens_at=opens_at,
            closes_at=closes_at,
            instructions=instructions,
            created_by=request.user,
        )
        messages.success(request, f'✅ Session <strong>{session.display_title}</strong> created.')
        return redirect('session_questions', pk=session.pk)

    return render(request, 'clearance/session_form.html', {'post': {}, 'action': 'Create'})


@login_required
@permission_required('clearance', 'edit')
def session_edit(request, pk):
    session = get_object_or_404(ClearanceSession, pk=pk)
    if request.method == 'POST':
        p = request.POST
        session.academic_session = p.get('academic_session', session.academic_session).strip()
        session.stream           = p.get('stream', session.stream).strip()
        session.title            = p.get('title', '').strip()
        session.opens_at         = p.get('opens_at', '').strip()
        session.closes_at        = p.get('closes_at', '').strip()
        session.instructions     = p.get('instructions', '').strip()
        session.is_active        = p.get('is_active') == 'on'
        session.save()
        messages.success(request, f'✅ Session updated.')
        return redirect('clearance_dashboard')
    return render(request, 'clearance/session_form.html', {'post': session, 'action': 'Edit', 'session': session})


# ══════════════════════════════════════════════════════════════════════════════
# STAFF — QUESTION BUILDER
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('clearance', 'edit')
def session_questions(request, pk):
    session   = get_object_or_404(ClearanceSession, pk=pk)
    questions = session.questions.all()

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'add_question':
            q_text  = request.POST.get('question_text', '').strip()
            q_type  = request.POST.get('question_type', 'text')
            q_req   = request.POST.get('is_required') == 'on'
            q_key   = request.POST.get('field_key', '').strip()
            # Choices — one per line
            raw_choices = request.POST.get('choices', '').strip()
            choices_list = [c.strip() for c in raw_choices.splitlines() if c.strip()]

            if not q_text:
                messages.error(request, 'Question text is required.')
            else:
                order = session.questions.count() + 1
                q = ClearanceQuestion.objects.create(
                    session=session,
                    question_text=q_text,
                    question_type=q_type,
                    choices_json=json.dumps(choices_list),
                    is_required=q_req,
                    field_key=q_key,
                    order=order,
                )
                messages.success(request, f'✅ Question added.')

        elif action == 'edit_question':
            qid          = request.POST.get('question_id', '')
            q_text       = request.POST.get('question_text', '').strip()
            q_type       = request.POST.get('question_type', 'text')
            q_req        = request.POST.get('is_required') == 'on'
            q_key        = request.POST.get('field_key', '').strip()
            raw_choices  = request.POST.get('choices', '').strip()
            choices_list = [c.strip() for c in raw_choices.splitlines() if c.strip()]
            if not q_text:
                messages.error(request, 'Question text is required.')
            else:
                try:
                    q = ClearanceQuestion.objects.get(pk=qid, session=session)
                    if q.is_preloaded:
                        messages.error(request, 'Preloaded questions cannot be edited here. Go to Default Questions to make changes.')
                    else:
                        q.question_text = q_text
                        q.question_type = q_type
                        q.is_required   = q_req
                        q.field_key     = q_key
                        q.choices_json  = json.dumps(choices_list)
                        q.save()
                        messages.success(request, '✅ Question updated.')
                except ClearanceQuestion.DoesNotExist:
                    messages.error(request, 'Question not found.')

        elif action == 'delete_question':
            qid = request.POST.get('question_id', '')
            try:
                q = ClearanceQuestion.objects.get(pk=qid, session=session)
                q.delete()
                messages.success(request, 'Question deleted.')
            except ClearanceQuestion.DoesNotExist:
                messages.error(request, 'Question not found.')

        elif action == 'reorder':
            order_data = request.POST.get('order_data', '')
            try:
                ids = json.loads(order_data)
                for idx, qid in enumerate(ids, start=1):
                    ClearanceQuestion.objects.filter(pk=qid, session=session).update(order=idx)
                messages.success(request, '✅ Order saved.')
            except (json.JSONDecodeError, ValueError):
                messages.error(request, 'Could not save order.')

        elif action == 'preload_defaults':
            _preload_default_questions(session)
            messages.success(request, '✅ Default medical questions added.')

        return redirect('session_questions', pk=pk)

    context = {
        'session':   session,
        'questions': questions,
        'field_key_choices': ClearanceQuestion.FIELD_KEY_CHOICES,
        'type_choices':      ClearanceQuestion.TYPE_CHOICES,
    }
    return render(request, 'clearance/questions.html', context)


def _preload_default_questions(session):
    """Copy from DefaultQuestion master template into this session."""
    defaults     = DefaultQuestion.objects.all().order_by('order', 'pk')
    start_order  = session.questions.count() + 1

    if not defaults.exists():
        # Fallback: seed the DefaultQuestion table first then preload
        _seed_default_questions()
        defaults = DefaultQuestion.objects.all().order_by('order', 'pk')

    for idx, d in enumerate(defaults, start=start_order):
        # Skip if a question with the same field_key already exists in session
        if d.field_key and session.questions.filter(field_key=d.field_key).exists():
            continue
        ClearanceQuestion.objects.create(
            session       = session,
            question_text = d.question_text,
            question_type = d.question_type,
            choices_json  = d.choices_json,
            is_required   = d.is_required,
            field_key     = d.field_key,
            order         = idx,
            is_preloaded  = True,
        )


def _seed_default_questions():
    """Populate DefaultQuestion table if empty."""
    SEED = [
        {'question_text': 'What is your Blood Group?',             'question_type': 'single',   'choices': ['A+','A-','B+','B-','AB+','AB-','O+','O-','Unknown'], 'is_required': True,  'field_key': 'blood_group'},
        {'question_text': 'What is your Genotype?',                'question_type': 'single',   'choices': ['AA','AS','SS','AC','SC','Unknown'],                  'is_required': True,  'field_key': 'genotype'},
        {'question_text': 'Do you have any known allergies? If yes, list them.',            'question_type': 'textarea', 'choices': [], 'is_required': False, 'field_key': 'known_allergies'},
        {'question_text': 'Do you have any chronic medical conditions? If yes, list them.', 'question_type': 'textarea', 'choices': [], 'is_required': False, 'field_key': 'chronic_conditions'},
        {'question_text': 'Do you have any physical or mental disabilities?',               'question_type': 'textarea', 'choices': [], 'is_required': False, 'field_key': 'disabilities'},
        {'question_text': 'What is your Blood Pressure reading? (e.g. 120/80 mmHg)',       'question_type': 'text',     'choices': [], 'is_required': False, 'field_key': 'blood_pressure'},
    ]
    for idx, d in enumerate(SEED, start=1):
        DefaultQuestion.objects.get_or_create(
            field_key=d['field_key'],
            defaults={
                'question_text': d['question_text'],
                'question_type': d['question_type'],
                'choices_json':  json.dumps(d['choices']),
                'is_required':   d['is_required'],
                'order':         idx,
            }
        )
        # For questions without a field_key just create them
    for idx, d in enumerate([s for s in SEED if not s['field_key']], start=len(SEED)+1):
        DefaultQuestion.objects.create(
            question_text=d['question_text'],
            question_type=d['question_type'],
            choices_json=json.dumps(d['choices']),
            is_required=d['is_required'],
            field_key='',
            order=idx,
        )


# ══════════════════════════════════════════════════════════════════════════════
# STAFF — MANAGE DEFAULT QUESTIONS TEMPLATE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('clearance', 'edit')
def default_questions(request):
    """Global default question template — staff edits once, sessions preload from here."""

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'add':
            q_text       = request.POST.get('question_text', '').strip()
            q_type       = request.POST.get('question_type', 'text')
            q_req        = request.POST.get('is_required') == 'on'
            q_key        = request.POST.get('field_key', '').strip()
            raw_choices  = request.POST.get('choices', '').strip()
            choices_list = [c.strip() for c in raw_choices.splitlines() if c.strip()]
            if not q_text:
                messages.error(request, 'Question text is required.')
            else:
                order = DefaultQuestion.objects.count() + 1
                DefaultQuestion.objects.create(
                    question_text=q_text, question_type=q_type,
                    choices_json=json.dumps(choices_list),
                    is_required=q_req, field_key=q_key, order=order,
                )
                messages.success(request, '✅ Default question added.')

        elif action == 'edit':
            qid          = request.POST.get('question_id', '')
            q_text       = request.POST.get('question_text', '').strip()
            q_type       = request.POST.get('question_type', 'text')
            q_req        = request.POST.get('is_required') == 'on'
            q_key        = request.POST.get('field_key', '').strip()
            raw_choices  = request.POST.get('choices', '').strip()
            choices_list = [c.strip() for c in raw_choices.splitlines() if c.strip()]
            if not q_text:
                messages.error(request, 'Question text is required.')
            else:
                try:
                    q = DefaultQuestion.objects.get(pk=qid)
                    q.question_text = q_text
                    q.question_type = q_type
                    q.is_required   = q_req
                    q.field_key     = q_key
                    q.choices_json  = json.dumps(choices_list)
                    q.save()
                    messages.success(request, '✅ Default question updated.')
                except DefaultQuestion.DoesNotExist:
                    messages.error(request, 'Question not found.')

        elif action == 'delete':
            qid = request.POST.get('question_id', '')
            try:
                q = DefaultQuestion.objects.get(pk=qid)
                q.delete()
                messages.success(request, '✅ Question removed from defaults.')
            except DefaultQuestion.DoesNotExist:
                messages.error(request, 'Question not found.')

        elif action == 'seed':
            # Seed initial defaults if table is empty
            _seed_default_questions()
            messages.success(request, '✅ Default questions seeded.')

        return redirect('default_questions')

    # Auto-seed if empty
    if not DefaultQuestion.objects.exists():
        _seed_default_questions()

    questions = DefaultQuestion.objects.all().order_by('order', 'pk')
    context = {
        'questions':         questions,
        'field_key_choices': DefaultQuestion.FIELD_KEY_CHOICES,
        'type_choices':      DefaultQuestion.TYPE_CHOICES,
    }
    return render(request, 'clearance/default_questions.html', context)



@login_required
@permission_required('clearance', 'view')
def submission_list(request, pk):
    session = get_object_or_404(ClearanceSession, pk=pk)
    search  = request.GET.get('q', '').strip()
    status  = request.GET.get('status', '').strip()

    qs = session.submissions.select_related('patient', 'reviewed_by').order_by('-submitted_at')
    if search:
        qs = qs.filter(
            Q(submission_id__icontains=search) |
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(patient__matric_no__icontains=search)
        ).distinct()
    if status:
        qs = qs.filter(status=status)

    context = {
        'session':     session,
        'submissions': qs,
        'search':      search,
        'filter_status': status,
        'approved_ct': session.submissions.filter(status='Approved').count(),
        'rejected_ct': session.submissions.filter(status='Rejected').count(),
        'total_ct':    session.submissions.count(),
    }
    return render(request, 'clearance/submissions.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# STAFF — SUBMISSION DETAIL + GRANT RESUBMIT / EXTEND DEADLINE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('clearance', 'view')
def submission_detail(request, pk):
    sub = get_object_or_404(
        ClearanceSubmission.objects.select_related(
            'patient', 'session', 'reviewed_by', 'resubmit_granted_by'
        ),
        pk=pk
    )
    answers = sub.answers.select_related('question').order_by('question__order')

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'grant_resubmit':
            sub.resubmit_granted    = True
            sub.resubmit_granted_by = request.user
            sub.resubmit_granted_at = timezone.now()
            sub.save(update_fields=['resubmit_granted', 'resubmit_granted_by', 'resubmit_granted_at'])
            messages.success(request, f'✅ Resubmit permission granted to {sub.patient.get_full_name()}.')

        elif action == 'extend_deadline':
            new_deadline = request.POST.get('extended_deadline', '').strip()
            if not new_deadline:
                messages.error(request, 'Please provide a new deadline date/time.')
            else:
                sub.extended_deadline = new_deadline
                sub.save(update_fields=['extended_deadline'])
                messages.success(request, f'✅ Deadline extended.')

        elif action == 'reject':
            remarks = request.POST.get('remarks', '').strip()
            if not remarks:
                messages.error(request, 'Reason is required when rejecting.')
            else:
                sub.status      = 'Rejected'
                sub.reviewed_by = request.user
                sub.reviewed_at = timezone.now()
                sub.remarks     = remarks
                sub.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'remarks'])
                messages.success(request, 'Submission rejected.')

        elif action == 'approve':
            sub.status      = 'Approved'
            sub.reviewed_by = request.user
            sub.reviewed_at = timezone.now()
            sub.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
            sub.sync_to_patient()
            messages.success(request, f'✅ Submission approved.')

        return redirect('submission_detail', pk=pk)

    context = {'sub': sub, 'answers': answers}
    return render(request, 'clearance/submission_detail.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# STAFF — PRINT CERTIFICATE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('clearance', 'export')
def clearance_certificate(request, pk):
    sub = get_object_or_404(
        ClearanceSubmission.objects.select_related(
            'patient', 'session', 'reviewed_by'
        ),
        pk=pk, status='Approved'
    )
    answers = sub.answers.select_related('question').order_by('question__order')
    return render(request, 'clearance/certificate.html', {'sub': sub, 'answers': answers})


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC — STEP 1: VERIFY IDENTITY
# ══════════════════════════════════════════════════════════════════════════════

def clearance_verify(request):
    """Student enters matric + DOB to verify identity."""
    open_sessions = ClearanceSession.objects.filter(is_active=True).order_by('-academic_session', 'stream')

    errors = []
    if request.method == 'POST':
        from patients.models import Patient
        matric_no = request.POST.get('matric_no', '').strip()
        dob       = request.POST.get('date_of_birth', '').strip()
        session_id= request.POST.get('session_id', '').strip()

        if not matric_no:   errors.append('Matric number is required.')
        if not dob:         errors.append('Date of birth is required.')
        if not session_id:  errors.append('Please select a clearance session.')

        if not errors:
            try:
                patient = Patient.objects.get(matric_no__iexact=matric_no, is_active=True)
            except Patient.DoesNotExist:
                errors.append('No active student record found for this matric number.')
                patient = None

            if patient:
                dob_str = str(patient.date_of_birth)
                if dob_str != dob:
                    errors.append('One of the field does not match our records.')
                    patient = None

            if patient:
                try:
                    session = ClearanceSession.objects.get(pk=session_id, is_active=True)
                except ClearanceSession.DoesNotExist:
                    errors.append('Selected session not found.')
                    session = None

                if session:
                    now = timezone.now()
                    # Check if student has a personal extended deadline
                    existing_sub = ClearanceSubmission.objects.filter(
                        session=session, patient=patient
                    ).first()
                    has_extension = (
                        existing_sub and
                        existing_sub.extended_deadline and
                        now <= existing_sub.extended_deadline
                    )

                    if not session.is_open and not has_extension:
                        if now < session.opens_at:
                            errors.append(
                                f'This clearance session has not opened yet. '
                                f'It opens on {session.opens_at.strftime("%d %b %Y, %H:%M")}.'
                            )
                        else:
                            errors.append(
                                f'This clearance session closed on '
                                f'{session.closes_at.strftime("%d %b %Y, %H:%M")}. '
                                f'Please visit the clinic if you need access.'
                            )
                    else:
                        # All good — store in session and redirect to form
                        request.session['clr_patient_id'] = patient.pk
                        request.session['clr_session_id'] = session.pk
                        return redirect('clearance_form')

    context = {
        'open_sessions': open_sessions,
        'errors':        errors,
        'post':          request.POST,
    }
    return render(request, 'clearance/verify.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC — STEP 2: FILL FORM
# ══════════════════════════════════════════════════════════════════════════════

def clearance_form(request):
    """Student fills the clearance form after verification."""
    patient_id = request.session.get('clr_patient_id')
    session_id = request.session.get('clr_session_id')

    if not patient_id or not session_id:
        return redirect('clearance_verify')

    from patients.models import Patient
    try:
        patient = Patient.objects.get(pk=patient_id, is_active=True)
        session = ClearanceSession.objects.get(pk=session_id)
    except (Patient.DoesNotExist, ClearanceSession.DoesNotExist):
        return redirect('clearance_verify')

    # Check for existing submission
    existing = ClearanceSubmission.objects.filter(session=session, patient=patient).first()

    if existing:
        # Block unless resubmit was granted
        if not existing.resubmit_granted:
            return render(request, 'clearance/already_submitted.html', {
                'sub': existing, 'patient': patient, 'session': session
            })
        # Resubmit mode — delete old answers so they can refill
        # (keep submission object, just clear answers)

    questions = session.questions.all().order_by('order')

    errors = []
    if request.method == 'POST':
        # Validate required questions
        for q in questions:
            if q.is_required:
                if q.question_type == 'multiple':
                    val = request.POST.getlist(f'q_{q.pk}')
                else:
                    val = request.POST.get(f'q_{q.pk}', '').strip()
                if not val:
                    errors.append(f'"{q.question_text}" is required.')

        if not errors:
            now = timezone.now()
            if existing:
                # Clear old answers and reset resubmit flag
                existing.answers.all().delete()
                existing.resubmit_granted    = False
                existing.resubmit_granted_by = None
                existing.resubmit_granted_at = None
                existing.submitted_at        = now
                existing.status              = 'Approved'
                existing.reviewed_by         = None
                existing.reviewed_at         = None
                existing.save()
                sub = existing
            else:
                sub = ClearanceSubmission.objects.create(
                    session=session,
                    patient=patient,
                    status='Approved',
                    reviewed_at=now,
                )

            # Save answers
            for q in questions:
                if q.question_type == 'multiple':
                    val = json.dumps(request.POST.getlist(f'q_{q.pk}'))
                else:
                    val = request.POST.get(f'q_{q.pk}', '').strip()

                ClearanceAnswer.objects.update_or_create(
                    submission=sub, question=q,
                    defaults={'answer_text': val}
                )

            # Sync medical fields to patient record
            sub.sync_to_patient()

            # Clear session vars
            del request.session['clr_patient_id']
            del request.session['clr_session_id']

            return redirect('clearance_success', pk=sub.pk)

    context = {
        'patient':   patient,
        'session':   session,
        'questions': questions,
        'errors':    errors,
        'post':      request.POST,
        'is_resubmit': bool(existing and existing.resubmit_granted),
    }
    return render(request, 'clearance/form.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC — SUCCESS PAGE
# ══════════════════════════════════════════════════════════════════════════════

def clearance_success(request, pk):
    sub = get_object_or_404(
        ClearanceSubmission.objects.select_related('patient', 'session'),
        pk=pk
    )
    return render(request, 'clearance/success.html', {'sub': sub})


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC — STATUS CHECK
# ══════════════════════════════════════════════════════════════════════════════

def clearance_status_check(request):
    result = None
    errors = []
    if request.method == 'POST':
        matric_no    = request.POST.get('matric_no', '').strip()
        submission_id= request.POST.get('submission_id', '').strip()

        if not matric_no:     errors.append('Matric number is required.')
        if not submission_id: errors.append('Reference ID is required.')

        if not errors:
            try:
                result = ClearanceSubmission.objects.select_related(
                    'patient', 'session', 'reviewed_by'
                ).get(
                    submission_id__iexact=submission_id,
                    patient__matric_no__iexact=matric_no
                )
            except ClearanceSubmission.DoesNotExist:
                errors.append('No clearance found matching these details. Please check and try again.')

    return render(request, 'clearance/status_check.html', {
        'result': result, 'errors': errors, 'post': request.POST
    })