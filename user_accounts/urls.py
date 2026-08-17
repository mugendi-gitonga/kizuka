from django.urls import path, include
from user_accounts.views import (
    login_view,
    verify_login_otp_view,
    resend_login_otp_view,
    cancel_login_otp_view,
    force_password_change_view,
    logout_view,
    signup_view,
    admin_create_business_view,
    forgot_password_view,
    forgot_password_done_view,
    reset_password_view,
    reset_password_done_view,
    invite_user_view,
    invite_user_done_view,
    decline_invite_view,
    verify_email_view,
    change_account_view,
    resend_invite_view,
    business_api_key_view,
    regenerate_api_key_view,
)

urlpatterns = [
    path("login/", login_view, name="login"),
    path("login/verify/", verify_login_otp_view, name="verify_login_otp"),
    path("login/verify/resend/", resend_login_otp_view, name="resend_login_otp"),
    path("login/verify/cancel/", cancel_login_otp_view, name="cancel_login_otp"),
    path("force-password-change/", force_password_change_view, name="force_password_change"),
    path("logout/", logout_view, name="logout"),
    path("signup/", signup_view, name="signup"),
    path("staff/create-business/", admin_create_business_view, name="admin_create_business"),
    path("forgot-password/",
        include(
            [
                path("done/", forgot_password_done_view, name="forgot_password_done"),
                path("", forgot_password_view, name="forgot_password"),
            ]
        ),
    ),
    path("reset-password/",
        include(
            [
                path("done/", reset_password_done_view, name="reset_password_done"),
                path("<str:token>/", reset_password_view, name="reset_password"),
            ]
        ),
    ),
    path("invite/",
        include(
            [
                path("resend/", resend_invite_view, name="resend_invite"),
                path("done/", invite_user_done_view, name="invite_user_done"),
                path("<str:token>/", invite_user_view, name="invite_user"),
                path("<str:token>/decline/", decline_invite_view, name="decline_invite"),
            ]
        ),
    ),
    path("verify-email/<str:token>/", verify_email_view, name="verify_email"),
    path("change-account/", change_account_view, name="change_account"),
]
