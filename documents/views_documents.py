import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from django.http import JsonResponse

from documents.models import OfficialDocument


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def documents_dashboard(request):
    docs     = OfficialDocument.objects.select_related('patient', 'issued_by')
    q        = request.GET.get('q', '').strip()
    doc_type = request.GET.get('type', '')
    status   = request.GET.get('status', '')

    if q:
        docs = docs.filter(
            Q(doc_id__icontains=q) |
            Q(patient__first_name__icontains=q) |
            Q(patient__last_name__icontains=q) |
            Q(patient__matric_no__icontains=q)
        )
    if doc_type:
        docs = docs.filter(doc_type=doc_type)
    if status:
        docs = docs.filter(status=status)

    context = {
        'docs':        docs[:60],
        'q':           q,
        'doc_type':    doc_type,
        'status':      status,
        'total':       OfficialDocument.objects.count(),
        'issued_ct':   OfficialDocument.objects.filter(status='issued').count(),
        'draft_ct':    OfficialDocument.objects.filter(status='draft').count(),
        'revoked_ct':  OfficialDocument.objects.filter(status='revoked').count(),
        'type_choices': OfficialDocument.DOC_TYPE_CHOICES,
        'recent':      OfficialDocument.objects.filter(status='issued').order_by('-created_at')[:5],
    }
    return render(request, 'documents/dashboard.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# CREATE DOCUMENT
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def document_create(request):
    from patients.models import Patient
    try:
        from consultations.models import Consultation
        consultations_available = True
    except Exception:
        consultations_available = False

    if request.method == 'POST':
        p = request.POST
        patient_id   = p.get('patient_id', '').strip()
        doc_type     = p.get('doc_type', '').strip()
        date_issued  = p.get('date_issued') or datetime.date.today().isoformat()
        status       = p.get('status', 'draft')
        errors       = []

        if not patient_id:
            errors.append('Patient is required.')
        if not doc_type:
            errors.append('Document type is required.')

        if not errors:
            try:
                patient = Patient.objects.get(pk=patient_id)
            except Patient.DoesNotExist:
                errors.append('Patient not found.')

        if not errors:
            doc = OfficialDocument(
                doc_type    = doc_type,
                status      = status,
                patient     = patient,
                issued_by   = request.user,
                date_issued = date_issued,
                diagnosis        = p.get('diagnosis', '').strip(),
                notes            = p.get('notes', '').strip(),
                additional_info  = p.get('additional_info', '').strip(),
            )

            # consultation
            consult_id = p.get('consultation_id', '').strip()
            if consult_id and consultations_available:
                try:
                    from consultations.models import Consultation
                    doc.consultation = Consultation.objects.get(pk=consult_id, patient=patient)
                except Exception:
                    pass

            # type-specific
            if doc_type == 'sick_leave':
                doc.leave_from = p.get('leave_from') or None
                doc.leave_to   = p.get('leave_to')   or None

            elif doc_type == 'fit_to_resume':
                doc.resume_date = p.get('resume_date') or None

            elif doc_type == 'referral':
                doc.referral_to         = p.get('referral_to', '').strip()
                doc.referral_department = p.get('referral_department', '').strip()
                doc.referral_reason     = p.get('referral_reason', '').strip()
                doc.referral_urgency    = p.get('referral_urgency', '').strip()

            doc.save()
            messages.success(request, f'✅ Document {doc.doc_id} created.')
            if status == 'issued':
                return redirect('document_print', pk=doc.pk)
            return redirect('document_detail', pk=doc.pk)

        context = {
            'errors':   errors,
            'post':     p,
            'patients': Patient.objects.filter(is_active=True).order_by('last_name'),
            'type_choices': OfficialDocument.DOC_TYPE_CHOICES,
            'today':    datetime.date.today().isoformat(),
        }
        return render(request, 'documents/create.html', context)

    context = {
        'patients': Patient.objects.filter(is_active=True).order_by('last_name'),
        'type_choices': OfficialDocument.DOC_TYPE_CHOICES,
        'today':    datetime.date.today().isoformat(),
        'post':     {},
        'errors':   [],
    }
    return render(request, 'documents/create.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# DETAIL
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def document_detail(request, pk):
    doc = get_object_or_404(OfficialDocument, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'issue':
            doc.status = 'issued'
            doc.save()
            messages.success(request, f'✅ {doc.doc_id} has been issued.')
            return redirect('document_print', pk=doc.pk)

        elif action == 'revoke':
            doc.status = 'revoked'
            doc.save()
            messages.warning(request, f'⚠️ {doc.doc_id} has been revoked.')
            return redirect('document_detail', pk=doc.pk)

        elif action == 'redraft':
            doc.status = 'draft'
            doc.save()
            messages.info(request, f'Document {doc.doc_id} moved back to draft.')
            return redirect('document_detail', pk=doc.pk)

    return render(request, 'documents/detail.html', {'doc': doc})


# ══════════════════════════════════════════════════════════════════════════════
# EDIT
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def document_edit(request, pk):
    doc = get_object_or_404(OfficialDocument, pk=pk)

    if doc.status == 'issued':
        messages.error(request, 'Issued documents cannot be edited. Revoke first.')
        return redirect('document_detail', pk=doc.pk)

    if request.method == 'POST':
        p = request.POST
        doc.diagnosis       = p.get('diagnosis', '').strip()
        doc.notes           = p.get('notes', '').strip()
        doc.additional_info = p.get('additional_info', '').strip()
        doc.date_issued     = p.get('date_issued') or datetime.date.today().isoformat()
        doc.status          = p.get('status', doc.status)

        if doc.doc_type == 'sick_leave':
            doc.leave_from = p.get('leave_from') or None
            doc.leave_to   = p.get('leave_to')   or None

        elif doc.doc_type == 'fit_to_resume':
            doc.resume_date = p.get('resume_date') or None

        elif doc.doc_type == 'referral':
            doc.referral_to         = p.get('referral_to', '').strip()
            doc.referral_department = p.get('referral_department', '').strip()
            doc.referral_reason     = p.get('referral_reason', '').strip()
            doc.referral_urgency    = p.get('referral_urgency', '').strip()

        consult_id = p.get('consultation_id', '').strip()
        if consult_id:
            try:
                from consultations.models import Consultation
                doc.consultation = Consultation.objects.get(pk=consult_id, patient=doc.patient)
            except Exception:
                doc.consultation = None
        else:
            doc.consultation = None

        doc.save()
        messages.success(request, '✅ Document updated.')
        return redirect('document_detail', pk=doc.pk)

    return render(request, 'documents/edit.html', {
        'doc':   doc,
        'today': datetime.date.today().isoformat(),
    })


# ══════════════════════════════════════════════════════════════════════════════
# PRINT / PREVIEW
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def document_print(request, pk):
    doc = get_object_or_404(OfficialDocument, pk=pk)
    import qrcode, io, base64
    from django.urls import reverse

    # Build QR pointing to internal detail page
    verify_url = request.build_absolute_uri(
        reverse('document_verify_internal', args=[doc.verification_code])
    )
    qr  = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#08131F', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return render(request, 'documents/print.html', {
        'doc':    doc,
        'qr_b64': qr_b64,
        'current_year': timezone.now().year,
    })


# ══════════════════════════════════════════════════════════════════════════════
# INTERNAL VERIFICATION (QR scan → staff sees doc info)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def document_verify_internal(request, code):
    doc = get_object_or_404(OfficialDocument, verification_code=code)
    return render(request, 'documents/verify_internal.html', {'doc': doc})


# ══════════════════════════════════════════════════════════════════════════════
# AJAX — patient consultations
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def ajax_patient_consultations(request):
    patient_id = request.GET.get('patient_id', '')
    data = []
    if patient_id:
        try:
            from consultations.models import Consultation
            consults = Consultation.objects.filter(
                patient_id=patient_id
            ).order_by('-created_at')[:20]
            for c in consults:
                data.append({'id': c.pk, 'label': str(c)})
        except Exception:
            pass
    return JsonResponse({'consultations': data})