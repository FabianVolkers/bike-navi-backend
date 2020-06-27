from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path(r'/search/', views.search),
    path(r'/weather/', views.weather),
    path(r'/directions/', views.directions),
    path(r'/features/', views.features)
]