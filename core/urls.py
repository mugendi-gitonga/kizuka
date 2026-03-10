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

from payins.callbacks import mpesa_c2b_callback_url, mpesa_stk_callback_url

from payouts.callbacks import mpesa_payout_callback_url
from user_accounts.views import (callback_log_detail_view, callback_logs_view, callbacks_add_edit_view, callbacks_delete_view, callbacks_list_view, integrations_view, regenerate_api_key_view, users_list_view, users_add_edit_view, users_delete_view, users_toggle_status_view, whitelist_add_view, whitelist_delete_view, whitelist_ips_view,)

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("user_accounts.urls")),

    path("dashboard/",
        include([
                
            path("", include("dashboard.urls")),
            path("", include("payins.urls")),
            path("", include("payouts.urls")),

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

            # Integrations URLs
            path("integrations/",
                include(
                    [
                        path("", integrations_view, name="integrations"),
                        path("callbacks/", callbacks_list_view, name="callbacks_list"),
                        path("callbacks/add/", callbacks_add_edit_view, name="callbacks_add"),
                        path("callbacks/<int:callback_id>/", callbacks_add_edit_view, name="callbacks_edit"),
                        path("callbacks/<int:callback_id>/delete/", callbacks_delete_view, name="callbacks_delete"),
                        # path("callbacks/<int:callback_id>/test/", callbacks_test_view, name="callbacks_test"),
                        path("callbacks/<int:callback_id>/logs/", callback_logs_view, name="callback_logs"),
                        path("callbacks/logs/<int:log_id>/", callback_log_detail_view, name="callback_log_detail"),
                        path("api-key/regenerate/", regenerate_api_key_view, name="regenerate_api_key"),
                        path("whitelist/", whitelist_ips_view, name="whitelist_ips"),
                        path("whitelist/add/", whitelist_add_view, name="whitelist_add"),
                        path("whitelist/<str:whitelist_id>/delete/", whitelist_delete_view, name="whitelist_delete"),
                    ]
                ),
            ),

        ]),
    ),

    path("api/v1/", include([
        path("callback/", include(
            [
                # PAYIN CALLBACKS
                path("mpesa/stk/", mpesa_stk_callback_url, name="mpesa_stk_callback"),
                path("mpesa/c2b/", mpesa_c2b_callback_url, name="mpesa_c2b_callback"), # offline handler

                # PAYOUT CALLBACKS
                path("mpesa/b2c/", mpesa_payout_callback_url, name="mpesa_b2c_callback"), # online handler
            ]
        )),
        path("", include("payins.api_urls")),
        path("", include("payouts.api_urls")),
    ])),
]
