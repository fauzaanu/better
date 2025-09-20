from django.urls import path
from . import views

app_name = 'better'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Day View (for viewing past days)
    path('day/<int:pk>/', views.DayView.as_view(), name='day-view'),
    
    # Target Category Management
    path('category/create/', views.TargetCategoryCreateView.as_view(), name='category-create'),
    path('category/<int:pk>/update/', views.TargetCategoryUpdateView.as_view(), name='category-update'),
    path('category/<int:pk>/delete/', views.TargetCategoryDeleteView.as_view(), name='category-delete'),
    
    # Target Management
    path('target/create/', views.TargetCreateView.as_view(), name='target-create'),
    path('target/<int:pk>/toggle/', views.TargetAchievementView.as_view(), name='target-toggle'),
    
    # Importance Management
    path('importance/', views.ImportanceManagementView.as_view(), name='importance-manage'),
]