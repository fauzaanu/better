import debug_toolbar
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    path('admin/', admin.site.urls),
]

urlpatterns += [
    path("__debug__/", include(debug_toolbar.urls)),
    path("__reload__/", include("django_browser_reload.urls")),
    path('cms/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),
    path('pages/', include(wagtail_urls)),
    path('accounts/', include('allauth.urls')),

    # apps : YOUR APP URLS go here
    # Note that wagtail urls dont need including if using default aproach of wagtail

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
