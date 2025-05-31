from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_view, name='upload'),
    path('describe/', views.describe_view, name='describe'),
    path("generate/", views.generate_view, name="generate"),
    path("add_instruction/", views.add_instruction_view, name="add_instruction"),
    path("refine/", views.refine_instructions_view, name="refine"),
    path("save_instructions/", views.save_instructions_view, name="save_instructions"),
]
