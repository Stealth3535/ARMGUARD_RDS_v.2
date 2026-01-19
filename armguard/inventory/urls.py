from django.urls import path
from .views import ItemListView, ItemDetailView, update_item_status

app_name = 'inventory'

urlpatterns = [
    path('', ItemListView.as_view(), name='item_list'),
    path('<str:pk>/', ItemDetailView.as_view(), name='item_detail'),
    path('<str:pk>/update-status/', update_item_status, name='update_item_status'),
]

