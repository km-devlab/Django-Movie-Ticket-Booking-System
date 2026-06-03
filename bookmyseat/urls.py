#original code
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from movies.views import admin_demo_reset, admin_email_test

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('', include('users.urls')),
    path('movies/', include('movies.urls')),
    
    # Secret DB Reset Route
    path('secret-db-reset/', admin_demo_reset, name='db_reset'),
    path('admin-email-test/', admin_email_test, name='admin_email_test'),
]

# Serve media files during development or if DEBUG is True
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# attempt 1
# from django.contrib import admin
# from django.urls import path, include

# from django.conf import settings
# from django.conf.urls.static import static

# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', include('movies.urls')),
# ]

# urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

#attempt 2
# from django.contrib import admin
# from django.urls import path, include
# from django.conf import settings
# from django.conf.urls.static import static

# urlpatterns = [
#     path('admin/', admin.site.urls),

#     path('', include('movies.urls')),
#     path('', include('users.urls')),
# ]

# urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
