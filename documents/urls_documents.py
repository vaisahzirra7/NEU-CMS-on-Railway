from django.urls import path
from documents import views_documents as v

urlpatterns = [
    path('documents/',                          v.documents_dashboard,        name='documents_dashboard'),
    path('documents/create/',                   v.document_create,            name='document_create'),
    path('documents/<int:pk>/',                 v.document_detail,            name='document_detail'),
    path('documents/<int:pk>/edit/',            v.document_edit,              name='document_edit'),
    path('documents/<int:pk>/print/',           v.document_print,             name='document_print'),
    path('documents/verify/<str:code>/',        v.document_verify_internal,   name='document_verify_internal'),
    path('ajax/documents/consultations/',       v.ajax_patient_consultations, name='doc_patient_consultations_ajax'),
]