from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('sick/', views.sick, name='sick'),
    path('trade/', views.trade, name='trade'),
    path('about/', views.about, name='about'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),


    # 登入/登出：使用 Django 內建功能即可
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # 註冊：自訂 view
    path('register/', views.register, name='register'),
]
