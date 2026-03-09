from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string

from prescriptions.models import Prescription, PrescriptionItem
from inventory.models import Drug, StockBatch, StockTransaction


DISPENSE_ROLES = [
    'Nurse', 'nurse',
    'Pharmacist', 'pharmacist',
    'Admin', 'admin',
    'Super Admin', 'super admin',
]


def can_dispense(user):
    role = getattr(user, 'role', None)
    if role is None:
        return False
    role_name = str(role)
    return any(r.lower() == role_name.lower() for r in DISPENSE_ROLES)


# ══════════════════════════════════════════════════════════════════════════════
# DISPENSING QUEUE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def dispensing_queue(request):
    search = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()  # Pending or In Progress

    qs = Prescription.objects.select_related(
        'patient', 'prescribed_by'
    ).filter(
        status__in=['Pending', 'In Progress']
    ).order_by('status', 'created_at')  # Pending first, then In Progress

    if search:
        qs = qs.filter(
            Q(prescription_id__icontains=search) |
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(patient__matric_no__icontains=search)
        ).distinct()

    if status:
        qs = qs.filter(status=status)

    today = timezone.localdate()
    context = {
        'queue':           qs,
        'search':          search,
        'filter_status':   status,
        'can_dispense':    can_dispense(request.user),
        'pending_ct':      Prescription.objects.filter(status='Pending').count(),
        'in_progress_ct':  Prescription.objects.filter(status='In Progress').count(),
        'dispensed_today': Prescription.objects.filter(
                               status='Dispensed', dispensed_at__date=today
                           ).count(),
    }
    return render(request, 'dispensing/queue.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# DISPENSE DETAIL — pharmacist reviews and confirms
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def dispense_detail(request, pk):
    rx    = get_object_or_404(
                Prescription.objects.select_related('patient', 'prescribed_by', 'consultation'),
                pk=pk
            )
    items = rx.items.select_related('drug').all()

    # Build item data with stock info
    item_data = []
    for item in items:
        stock     = item.drug.total_stock if item.drug else None
        sufficient = stock is None or stock >= item.quantity
        item_data.append({
            'item':       item,
            'stock':      stock,
            'sufficient': sufficient,
            'shortage':   max(0, item.quantity - stock) if stock is not None else 0,
        })

    all_sufficient = all(d['sufficient'] for d in item_data)

    context = {
        'rx':            rx,
        'item_data':     item_data,
        'all_sufficient':all_sufficient,
        'can_dispense':  can_dispense(request.user),
    }
    return render(request, 'dispensing/detail.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# MARK IN PROGRESS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def mark_in_progress(request, pk):
    if not can_dispense(request.user):
        messages.error(request, 'You do not have permission to update dispensing status.')
        return redirect('dispense_detail', pk=pk)

    rx = get_object_or_404(Prescription, pk=pk)
    if rx.status != 'Pending':
        messages.error(request, f'Cannot mark as In Progress — current status is {rx.status}.')
        return redirect('dispense_detail', pk=pk)

    rx.status = 'In Progress'
    rx.save(update_fields=['status'])
    messages.success(request, f'✅ <strong>{rx.prescription_id}</strong> marked as In Progress.')
    return redirect('dispense_detail', pk=pk)


# ══════════════════════════════════════════════════════════════════════════════
# CONFIRM DISPENSE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def confirm_dispense(request, pk):
    if not can_dispense(request.user):
        messages.error(request, 'You do not have permission to dispense.')
        return redirect('dispense_detail', pk=pk)

    rx = get_object_or_404(Prescription, pk=pk)

    if rx.status not in ['Pending', 'In Progress']:
        messages.error(request, f'Cannot dispense — status is already {rx.status}.')
        return redirect('dispense_detail', pk=pk)

    # Process each item — use confirmed quantities from POST
    items = rx.items.select_related('drug').all()
    for item in items:
        field_name  = f'qty_{item.pk}'
        raw_qty     = request.POST.get(field_name, '').strip()
        try:
            qty_to_dispense = max(0, int(raw_qty)) if raw_qty else item.quantity
        except (ValueError, TypeError):
            qty_to_dispense = item.quantity

        if qty_to_dispense > 0 and item.drug:
            _deduct_stock(item.drug, qty_to_dispense, rx.prescription_id, request.user)
            item.dispensed_qty = qty_to_dispense
            item.save(update_fields=['dispensed_qty'])

    rx.status       = 'Dispensed'
    rx.dispensed_by = request.user
    rx.dispensed_at = timezone.now()
    rx.save(update_fields=['status', 'dispensed_by', 'dispensed_at'])

    messages.success(
        request,
        f'✅ Prescription <strong>{rx.prescription_id}</strong> dispensed successfully.'
    )
    return redirect('dispense_slip', pk=rx.pk)


# ══════════════════════════════════════════════════════════════════════════════
# DISPENSING SLIP — printable
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def dispense_slip(request, pk):
    rx    = get_object_or_404(
                Prescription.objects.select_related(
                    'patient', 'prescribed_by', 'dispensed_by', 'consultation'
                ),
                pk=pk
            )
    items = rx.items.select_related('drug').all()
    return render(request, 'dispensing/slip.html', {'rx': rx, 'items': items})


# ══════════════════════════════════════════════════════════════════════════════
# STOCK DEDUCTION (FEFO)
# ══════════════════════════════════════════════════════════════════════════════

def _deduct_stock(drug, qty_needed, reference, user):
    batches = StockBatch.objects.filter(
        drug=drug,
        is_active=True,
        quantity_remaining__gt=0,
    ).order_by('expiry_date', 'created_at')

    remaining = qty_needed
    for batch in batches:
        if remaining <= 0:
            break
        deduct = min(batch.quantity_remaining, remaining)
        batch.quantity_remaining -= deduct
        if batch.quantity_remaining == 0:
            batch.is_active = False
        batch.save(update_fields=['quantity_remaining', 'is_active'])

        StockTransaction.objects.create(
            drug         = drug,
            batch        = batch,
            type         = 'OUT',
            quantity     = -deduct,
            reference    = reference,
            notes        = f'Dispensed via {reference}',
            performed_by = user,
        )
        remaining -= deduct


# ══════════════════════════════════════════════════════════════════════════════
# DISPENSING HISTORY
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def dispensing_history(request):
    search    = request.GET.get('q', '').strip()
    date_from = request.GET.get('from', '').strip()
    date_to   = request.GET.get('to', '').strip()

    qs = Prescription.objects.select_related(
        'patient', 'prescribed_by', 'dispensed_by'
    ).filter(status='Dispensed').order_by('-dispensed_at')

    if search:
        qs = qs.filter(
            Q(prescription_id__icontains=search) |
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(patient__matric_no__icontains=search) |
            Q(dispensed_by__first_name__icontains=search) |
            Q(dispensed_by__last_name__icontains=search)
        ).distinct()
    if date_from:
        qs = qs.filter(dispensed_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(dispensed_at__date__lte=date_to)

    today = timezone.localdate()
    context = {
        'history':         qs,
        'search':          search,
        'date_from':       date_from,
        'date_to':         date_to,
        'dispensed_today': Prescription.objects.filter(
                               status='Dispensed', dispensed_at__date=today
                           ).count(),
        'dispensed_total': Prescription.objects.filter(status='Dispensed').count(),
    }
    return render(request, 'dispensing/history.html', context)