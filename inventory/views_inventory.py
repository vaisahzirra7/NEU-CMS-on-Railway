from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.permissions import permission_required

from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Sum
from django.views.decorators.http import require_POST

from inventory.models import Drug, DrugCategory, StockBatch, StockTransaction


# ══════════════════════════════════════════════════════════════════════════════
# DRUG LIST
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('inventory', 'view')
def drug_list(request):
    drugs = Drug.objects.filter(is_active=True).select_related('category').order_by('name')

    search      = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    stock_filter= request.GET.get('stock', '')

    if search:
        drugs = drugs.filter(
            Q(name__icontains=search) |
            Q(generic_name__icontains=search) |
            Q(drug_code__icontains=search) |
            Q(supplier__icontains=search)
        )
    if category_id:
        drugs = drugs.filter(category_id=category_id)

    # Annotate total stock
    drugs = list(drugs)

    if stock_filter == 'low':
        drugs = [d for d in drugs if d.is_low_stock and d.total_stock > 0]
    elif stock_filter == 'out':
        drugs = [d for d in drugs if d.total_stock == 0]
    elif stock_filter == 'expired':
        drugs = [d for d in drugs if d.has_expired_batches]

    today = timezone.localdate()
    context = {
        'drugs':         drugs,
        'categories':    DrugCategory.objects.filter(is_active=True).order_by('name'),
        'search':        search,
        'filter_cat':    category_id,
        'filter_stock':  stock_filter,
        # Stats
        'total_drugs':   Drug.objects.filter(is_active=True).count(),
        'low_stock_ct':  sum(1 for d in Drug.objects.filter(is_active=True) if d.is_low_stock and d.total_stock > 0),
        'out_of_stock':  sum(1 for d in Drug.objects.filter(is_active=True) if d.total_stock == 0),
        'expiring_soon': StockBatch.objects.filter(
                             is_active=True,
                             expiry_date__lte=today + timezone.timedelta(days=90),
                             expiry_date__gte=today
                         ).count(),
    }
    return render(request, 'inventory/list.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# DRUG CREATE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('inventory', 'create')
def drug_create(request):
    categories = DrugCategory.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        p      = request.POST
        errors = []

        if not p.get('name', '').strip():
            errors.append('Drug name is required.')
        if not p.get('dosage_form', '').strip():
            errors.append('Dosage form is required.')
        if not p.get('unit', '').strip():
            errors.append('Unit of measure is required.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'inventory/create.html', {
            'categories': categories,
            'drug_forms': Drug.DOSAGE_FORM_CHOICES,
            'drug_units': Drug.UNIT_CHOICES,
            'post': p,
        })

        category = DrugCategory.objects.filter(pk=p.get('category')).first() if p.get('category') else None

        drug = Drug.objects.create(
            name          = p['name'].strip(),
            generic_name  = p.get('generic_name', '').strip(),
            category      = category,
            dosage_form   = p['dosage_form'],
            strength      = p.get('strength', '').strip(),
            unit          = p['unit'],
            reorder_level = int(p.get('reorder_level', 10) or 10),
            supplier      = p.get('supplier', '').strip(),
            manufacturer  = p.get('manufacturer', '').strip(),
            description   = p.get('description', '').strip(),
            created_by    = request.user,
        )

        messages.success(request, f'✅ Drug <strong>{drug.name}</strong> added to inventory.')
        return redirect('drug_detail', pk=drug.pk)

    return render(request, 'inventory/create.html', {
        'categories': categories,
        'drug_forms': Drug.DOSAGE_FORM_CHOICES,
        'drug_units': Drug.UNIT_CHOICES,
        'post': {},
    })


# ══════════════════════════════════════════════════════════════════════════════
# DRUG DETAIL
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('inventory', 'view')
def drug_detail(request, pk):
    drug         = get_object_or_404(Drug.objects.select_related('category'), pk=pk)
    batches      = drug.batches.filter(is_active=True).order_by('expiry_date')
    transactions = drug.transactions.select_related('performed_by', 'batch').order_by('-created_at')[:30]
    today        = timezone.localdate()

    context = {
        'drug':         drug,
        'batches':      batches,
        'transactions': transactions,
        'today':        today,
    }
    return render(request, 'inventory/detail.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# DRUG EDIT
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('inventory', 'edit')
def drug_edit(request, pk):
    drug       = get_object_or_404(Drug, pk=pk)
    categories = DrugCategory.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        p        = request.POST
        category = DrugCategory.objects.filter(pk=p.get('category')).first() if p.get('category') else None

        drug.name          = p.get('name', drug.name).strip()
        drug.generic_name  = p.get('generic_name', '').strip()
        drug.category      = category
        drug.dosage_form   = p.get('dosage_form', drug.dosage_form)
        drug.strength      = p.get('strength', '').strip()
        drug.unit          = p.get('unit', drug.unit)
        drug.reorder_level = int(p.get('reorder_level', drug.reorder_level) or drug.reorder_level)
        drug.supplier      = p.get('supplier', '').strip()
        drug.manufacturer  = p.get('manufacturer', '').strip()
        drug.description   = p.get('description', '').strip()
        drug.save()

        messages.success(request, f'✅ <strong>{drug.name}</strong> updated.')
        return redirect('drug_detail', pk=drug.pk)

    return render(request, 'inventory/edit.html', {
        'drug': drug,
        'categories': categories,
        'drug_forms': Drug.DOSAGE_FORM_CHOICES,
        'drug_units': Drug.UNIT_CHOICES,
    })


# ══════════════════════════════════════════════════════════════════════════════
# ADD STOCK (new batch)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('inventory', 'edit')
def drug_add_stock(request, pk):
    drug = get_object_or_404(Drug, pk=pk)

    if request.method == 'POST':
        p        = request.POST
        qty      = int(p.get('quantity', 0) or 0)
        errors   = []

        if qty <= 0:
            errors.append('Quantity must be greater than zero.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect('drug_detail', pk=pk)

        expiry_date  = p.get('expiry_date', '').strip() or None
        unit_cost    = p.get('unit_cost', '').strip() or None
        batch_number = p.get('batch_number', '').strip()
        supplier     = p.get('supplier', drug.supplier).strip()
        notes        = p.get('notes', '').strip()

        batch = StockBatch.objects.create(
            drug               = drug,
            batch_number       = batch_number,
            quantity_received  = qty,
            quantity_remaining = qty,
            unit_cost          = unit_cost,
            expiry_date        = expiry_date,
            date_received      = timezone.localdate(),
            supplier           = supplier,
            notes              = notes,
            received_by        = request.user,
        )

        # Log the stock-in transaction
        StockTransaction.objects.create(
            drug         = drug,
            batch        = batch,
            type         = 'IN',
            quantity     = qty,
            reference    = batch_number or f'Batch {batch.pk}',
            notes        = notes,
            performed_by = request.user,
        )

        messages.success(
            request,
            f'✅ <strong>{qty} {drug.unit}</strong> of <strong>{drug.name}</strong> added to stock.'
        )
        return redirect('drug_detail', pk=pk)

    return redirect('drug_detail', pk=pk)


# ══════════════════════════════════════════════════════════════════════════════
# REMOVE EXPIRED BATCH
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('inventory', 'edit')
@require_POST
def batch_remove_expired(request, batch_pk):
    batch = get_object_or_404(StockBatch, pk=batch_pk)

    if not batch.is_expired:
        messages.error(request, 'This batch has not expired yet.')
        return redirect('drug_detail', pk=batch.drug.pk)

    qty_removed = batch.quantity_remaining
    StockTransaction.objects.create(
        drug         = batch.drug,
        batch        = batch,
        type         = 'EXPIRED',
        quantity     = -qty_removed,
        reference    = f'Batch {batch.batch_number or batch.pk}',
        notes        = 'Expired batch removed from inventory',
        performed_by = request.user,
    )

    batch.quantity_remaining = 0
    batch.is_active          = False
    batch.save(update_fields=['quantity_remaining', 'is_active'])

    messages.success(request, f'✅ Expired batch removed. {qty_removed} {batch.drug.unit} written off.')
    return redirect('drug_detail', pk=batch.drug.pk)


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORIES
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('inventory', 'view')
def category_list(request):
    categories = DrugCategory.objects.all().order_by('name')
    return render(request, 'inventory/categories.html', {'categories': categories})


@login_required
@permission_required('inventory', 'edit')
@require_POST
def category_create(request):
    name = request.POST.get('name', '').strip()
    if not name:
        messages.error(request, 'Category name is required.')
        return redirect('drug_categories')

    cat, created = DrugCategory.objects.get_or_create(name=name, defaults={
        'description': request.POST.get('description', '').strip()
    })
    if created:
        messages.success(request, f'✅ Category <strong>{name}</strong> added.')
    else:
        messages.warning(request, f'Category <strong>{name}</strong> already exists.')
    return redirect('drug_categories')


# ══════════════════════════════════════════════════════════════════════════════
# AJAX — Search drugs (for prescriptions)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@permission_required('inventory', 'view')
def drug_search_ajax(request):
    q = request.GET.get('q', '').strip()

    drugs = Drug.objects.filter(is_active=True).order_by('name')

    # If a real search term is given, filter by it; otherwise return all (browse mode)
    if q and q != ' ':
        drugs = drugs.filter(
            Q(name__icontains=q) | Q(generic_name__icontains=q)
        )

    drugs = drugs[:20]

    data = [
        {
            'id':           d.pk,
            'name':         d.name,
            'generic_name': d.generic_name,
            'strength':     d.strength,
            'dosage_form':  d.dosage_form,
            'unit':         d.unit,
            'stock':        d.total_stock,
            'label':        f'{d.name} {d.strength} {d.dosage_form} — {d.total_stock} {d.unit} in stock',
        }
        for d in drugs
    ]
    return JsonResponse({'drugs': data})