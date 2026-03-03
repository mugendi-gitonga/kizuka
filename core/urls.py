"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from user_accounts.views import (users_list_view, users_add_edit_view, users_delete_view, users_toggle_status_view,)

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("user_accounts.urls")),

    path("dashboard/",
        include([
                
            path("", include("dashboard.urls")),

            # User management URLs
            path("users/",
                include(
                    [
                        path("", users_list_view, name="users_list"),
                        path("add-edit/", users_add_edit_view, name="users_add_edit"),
                        path("delete/", users_delete_view, name="users_delete"),
                        path("toggle-status/",users_toggle_status_view,name="users_toggle_status",),
                    ]
                ),
            ),

        ]),
    ),
    path("api/v1/", include([

    ])),
]
