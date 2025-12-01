from django.contrib import admin
from django.urls import path, include
from django.urls import path
from myapp.views import trade

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('myapp.urls')),  # 將路由指到 main app
    path("rice/", trade, name="trade"),
]
