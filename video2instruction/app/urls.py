from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_view, name='upload'),
    path('describe/', views.describe_view, name='describe'),
    path("generate/", views.generate_view, name="generate"),
]
