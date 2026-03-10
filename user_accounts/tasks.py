from core import settings
from core.celery import app
from django.template.loader import render_to_string
from django.template import Context, Template
from django.core.mail import EmailMultiAlternatives
import logging

from zoho import send_zoho_message_api

logger = logging.getLogger(__name__)

@app.task(name="send_verification_email_task", queue="email_tasks", max_retries=3, default_retry_delay=60)
def send_verification_email(email, first_name, verification_link):
    try:
        context_dict = {
            'first_name': first_name,
            'verification_link': verification_link
        }
        context = Context(context_dict)
        txt_template = Template('/user_accounts/templates/emails/text/verification_email.txt').render(context)
        html_template = Template('/user_accounts/templates/emails/html/verification_email.html').render(context)
        html_content = render_to_string('emails/html/verification_email.html', context_dict)
        subject = "Please Verify Your Email Address"
        # email = EmailMultiAlternatives(subject, txt_template, to=[email])
        # email.attach_alternative(html_template, "text/html")
        # email.send()
        send_zoho_message_api(email, subject, html_content)
        print(verification_link)
        logger.info(f"Verification email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {str(e)}")
        raise send_verification_email.retry(exc=e)


@app.task(name="send_invitation_email_task", queue="email_tasks", max_retries=3, default_retry_delay=60)
def send_invitation_email(email, first_name, business_name):
    try:
        context_dict = {
            'first_name': first_name,
            'business_name': business_name,
            'invite_link': f"{settings.FRONTEND_URL}/invite/"
        }
        context = Context(context_dict)
        txt_template = Template('/user_accounts/templates/emails/text/invite_user.txt').render(context)
        html_template = Template('/user_accounts/templates/emails/html/invite_user.html').render(context)
        html_content = render_to_string('emails/html/invite_user.html', context_dict)
        subject = f"Invitation to Join {business_name}"
        # email = EmailMultiAlternatives(subject, txt_template, to=[email])
        # email.attach_alternative(html_template, "text/html")
        # email.send()
        send_zoho_message_api(email, subject, html_content)
        logger.info(f"Invitation email sent to {email} for joining {business_name}")
    except Exception as e:
        logger.error(f"Failed to send invitation email to {email}: {str(e)}")
        raise send_invitation_email.retry(exc=e)


@app.task(name="send_existing_invitation_email_task", queue="email_tasks", max_retries=3, default_retry_delay=60)
def send_existing_invitation_email(email, first_name, inviter_name, business_name, accept_link, decline_link, business_email=None, business_description=None):
    try:
        context_dict = {
            'first_name': first_name,
            'inviter_name': inviter_name,
            'business_name': business_name,
            'accept_link': accept_link,
            'decline_link': decline_link,
            'business_email': business_email,
            'business_description': business_description,
        }
        context = Context(context_dict)
        txt_template = Template('/user_accounts/templates/emails/text/existing_invite_user.txt').render(context)
        html_template = Template('/user_accounts/templates/emails/html/existing_invite_user.html').render(context)
        html_content = render_to_string('emails/html/existing_invite_user.html', context_dict)
        subject = f"You're Invited to Join {business_name}"
        # email_msg = EmailMultiAlternatives(subject, txt_template, to=[email])
        # email_msg.attach_alternative(html_template, "text/html")
        # email_msg.send()
        send_zoho_message_api(email, subject, html_content)   
        print(accept_link)
        logger.info(f"Existing user invitation email sent to {email} for {business_name}")
    except Exception as e:
        logger.error(f"Failed to send existing invitation email to {email}: {str(e)}")
        raise send_existing_invitation_email.retry(exc=e)


@app.task(name="send_password_reset_email_task", queue="email_tasks", max_retries=3, default_retry_delay=60)
def send_password_reset_email(email, first_name, reset_link):
    try:
        context_dict = {
            'first_name': first_name,
            'reset_link': reset_link
        }
        context = Context(context_dict)
        txt_template = Template('/user_accounts/templates/emails/text/password_reset_email.txt').render(context)
        html_template = Template('/user_accounts/templates/emails/html/password_reset_email.html').render(context)
        html_content = render_to_string('emails/html/password_reset_email.html', context_dict)
        subject = "Reset Your Password"
        # email_msg = EmailMultiAlternatives(subject, txt_template, to=[email])
        # email_msg.attach_alternative(html_template, "text/html")
        # email_msg.send()
        send_zoho_message_api(email, subject, html_content)
        print(reset_link)
        logger.info(f"Password reset email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {str(e)}")
        raise send_password_reset_email.retry(exc=e)
