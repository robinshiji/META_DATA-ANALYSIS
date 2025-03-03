from django.urls import path
from .views import *

urlpatterns = [
    path('', upload_file, name='upload_file'),
	path('dash/',dashboard,name='dashboard'),
	  path('delete/<int:file_id>/', delete_file, name='delete_file'),
]