from django.urls import path
from inventory import views_inventory

urlpatterns = [
    path('inventory/',                          views_inventory.drug_list,            name='drug_list'),
    path('inventory/add/',                      views_inventory.drug_create,          name='drug_create'),
    path('inventory/<int:pk>/',                 views_inventory.drug_detail,          name='drug_detail'),
    path('inventory/<int:pk>/edit/',            views_inventory.drug_edit,            name='drug_edit'),
    path('inventory/<int:pk>/add-stock/',       views_inventory.drug_add_stock,       name='drug_add_stock'),
    path('inventory/categories/',               views_inventory.category_list,        name='drug_categories'),
    path('inventory/categories/create/',        views_inventory.category_create,      name='drug_category_create'),
    path('inventory/batch/<int:batch_pk>/remove-expired/', views_inventory.batch_remove_expired, name='batch_remove_expired'),

    # AJAX
    path('ajax/inventory/search/',              views_inventory.drug_search_ajax,     name='drug_search_ajax'),
]