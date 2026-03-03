import datetime
import logging
import json

from django.core.cache import cache
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from django.db import transaction as db_transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from user_accounts.decorators import business_admin_required
from user_accounts.utils import hash_token, verify_token_hash
from .forms import LoginForm, SignUpForm, AddTeamMemberForm, ForgotPasswordForm, ResetPasswordForm, InviteUserForm

from constants import COUNTRIES
from utils import decode_jwt, encode_jwt, get_client_ip

from user_accounts.models import Business, BusinessTeamMember, UserProfile, PasswordResetLog, InviteUserLog
from user_accounts.tasks import send_existing_invitation_email, send_password_reset_email

logger = logging.getLogger(__name__)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard_overview")

    form = LoginForm(request.POST or None)
    try:
        if request.method == 'POST':
            if form.is_valid():
                user = form.cleaned_data['user']
                login(request, user)
                if next_url := request.GET.get('next'):
                    return redirect(next_url)
                return redirect("dashboard_overview")
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        form.add_error(None, "An error occurred during login. Please try again.")

    return render(request, 'auth/login.html', {"form": form})


def signup_view(request):
    form = SignUpForm(request.POST or None)
    try:
        if request.user.is_authenticated:
            return redirect("dashboard_overview")
        if request.method == 'POST':
            if form.is_valid():
                form.save()
                user = authenticate(username=form.cleaned_data['email'], password=form.cleaned_data['password'])
                if user is not None:
                    login(request, user)
                    return redirect("dashboard_overview")
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        form.add_error(None, "An error occurred during signup. Please try again.")

    return render(request, "auth/signup.html", {"form": form, "countries": COUNTRIES})


def logout_view(request):
    try:
        from django.contrib.auth import logout
        logout(request)
        return redirect("login")

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return redirect("login")


def verify_email_view(request, token):
    try:
        token_data = decode_jwt(token, audience_id="email_verification")
        if token_data.get("reference") != "email_verification":
            raise Exception("Invalid token reference.")

        user_id = token_data.get("accountID")
        user_profile = UserProfile.objects.filter(user_id=user_id).first()
        if not user_profile:
            raise Exception("User profile not found.")

        if user_profile.email_verified:
            return render(request, 'auth/verify_email.html', {"message": "Email already verified."})

        user_profile.email_verified = True
        user_profile.verification_token = None
        user_profile.save(update_fields=['email_verified', 'verification_token'])

        user_profile.user.is_active = True
        user_profile.user.save(update_fields=['is_active'])

        # Log successful verification
        logger.info(f"Email verified for user {user_id}")

        # If user is already authenticated, redirect to dashboard
        if request.user.is_authenticated:
            return redirect("dashboard_overview")

        # Otherwise show success page
        return render(request, 'auth/verify_email.html', {"success": True})

    except Exception as e:
        logger.error(f"Email verification failed: {str(e)}")
        return render(request, 'auth/verify_email.html', {"error": "Invalid or expired token."})


def forgot_password_view(request):
    form = ForgotPasswordForm(request.POST or None)
    client_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    try:
        if request.user.is_authenticated:
            return redirect("dashboard_overview")
        if request.method == 'POST':
            if form.is_valid():
                email = form.cleaned_data['email']
                user = User.objects.get(email=email)

                # Create password reset token
                token_data = {
                    "accountID": user.id,
                    "reference": "password_reset",
                    "expires_in": (datetime.datetime.utcnow() + datetime.timedelta(hours=24)).timestamp()
                }
                reset_token = encode_jwt(token_data, account_id=user.id,reference="password_reset", expiry=24*3600)

                # Atomic: Update UserProfile and create PasswordResetLog
                with db_transaction.atomic():
                    # Hash and save token to user profile
                    user_profile = UserProfile.objects.get(user=user)
                    user_profile.password_reset_token_hash = hash_token(reset_token)
                    user_profile.password_reset_requested_at = timezone.now()
                    user_profile.password_reset_ip = client_ip
                    user_profile.password_reset_used = False
                    user_profile.save(update_fields=[
                        'password_reset_token_hash',
                        'password_reset_requested_at',
                        'password_reset_ip',
                        'password_reset_used'
                    ])

                    # Log the password reset request
                    PasswordResetLog.objects.create(
                        user=user,
                        status='requested',
                        ip_address=client_ip,
                        user_agent=user_agent
                    )

                logger.info(f"Password reset requested for user {user.id} from IP {client_ip}")

                # Send reset email (outside atomic to avoid blocking on email)
                reset_link = f"{settings.FRONTEND_URL}/reset-password/{reset_token}"
                send_password_reset_email.apply_async(args=[user.email, user.first_name, reset_link])

                return redirect('forgot_password_done')
    except User.DoesNotExist:
        logger.warning(f"Password reset requested for non-existent email from IP {client_ip}")
        return redirect("forgot_password_done")
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        form.add_error(None, "An error occurred. Please try again.")

    return render(request, 'auth/forgot_password.html', {"form": form})


def forgot_password_done_view(request):
    return render(request, 'auth/forgot_password_done.html')


def reset_password_view(request, token):
    form = ResetPasswordForm(request.POST or None)
    client_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    try:
        # Validate token
        token_data = decode_jwt(token, audience_id="password_reset")
        if token_data.get("reference") != "password_reset":
            logger.warning(f"Invalid token reference from IP {client_ip}")
            raise Exception("Invalid token provided.")
        
        user_id = token_data.get("accountID")
        user = User.objects.get(id=user_id)
        user_profile = UserProfile.objects.get(user=user)
        
        # Check if token has already been used
        if user_profile.password_reset_used:
            logger.warning(f"Attempt to reuse password reset token for user {user_id} from IP {client_ip}")
            PasswordResetLog.objects.create(
                user=user,
                status='token_already_used',
                ip_address=client_ip,
                user_agent=user_agent,
                error_message="Token has already been used"
            )
            raise Exception("This password reset token has already been used.")
        
        # Verify token hash matches stored hash using constant-time comparison
        if not verify_token_hash(token, user_profile.password_reset_token_hash):
            logger.warning(f"Invalid token hash for user {user_id} from IP {client_ip}")
            PasswordResetLog.objects.create(
                user=user,
                status='invalid_token',
                ip_address=client_ip,
                user_agent=user_agent,
                error_message="Token hash mismatch"
            )
            raise Exception("Token does not match.")
        
        # Verify token is not older than 24 hours
        if user_profile.password_reset_requested_at:
            token_age = timezone.now() - user_profile.password_reset_requested_at
            if token_age > datetime.timedelta(hours=24):
                logger.warning(f"Expired password reset token for user {user_id} from IP {client_ip}")
                PasswordResetLog.objects.create(
                    user=user,
                    status='token_expired',
                    ip_address=client_ip,
                    user_agent=user_agent,
                    error_message="Token expired"
                )
                raise Exception("Password reset token has expired.")
        
        if request.method == 'POST':
            if form.is_valid():
                # Atomic: Update User, UserProfile, and create PasswordResetLog
                with db_transaction.atomic():
                    # Update password
                    user.set_password(form.cleaned_data['new_password1'])
                    user.save()
                    
                    # Mark token as used
                    user_profile.password_reset_token_hash = None
                    user_profile.password_reset_used = True
                    user_profile.password_reset_requested_at = None
                    user_profile.save(update_fields=[
                        'password_reset_token_hash',
                        'password_reset_used',
                        'password_reset_requested_at'
                    ])
                    
                    # Log successful password reset
                    PasswordResetLog.objects.create(
                        user=user,
                        status='reset_successful',
                        ip_address=client_ip,
                        user_agent=user_agent
                    )
                
                logger.info(f"Password successfully reset for user {user_id} from IP {client_ip}")
                return redirect('reset_password_done')
    
    except Exception as e:
        logger.error(f"Password reset failed: {str(e)} from IP {client_ip}")
        return render(request, 'auth/reset_password.html', {"error": "Invalid or expired reset link.", "token": token})

    return render(request, 'auth/reset_password.html', {"form": form, "token": token})


def reset_password_done_view(request):
    return render(request, 'auth/reset_password_done.html')


def invite_user_view(request, token):
    form = InviteUserForm(request.POST or None)
    client_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    try:
        # Validate invite token
        token_data = decode_jwt(token, audience_id="invite_user")
        if token_data.get("reference") != "invite_user":
            logger.warning(f"Invalid invite token reference from IP {client_ip}")
            raise Exception("Invalid token provided.")

        user_id = token_data.get("accountID")
        business_id = token_data.get("businessID")
        user = User.objects.get(id=user_id)
        user_profile = UserProfile.objects.get(user=user)
        business = Business.objects.get(alias_id=business_id)

        # Check if invite has already been used
        if user_profile.invite_used:
            logger.warning(f"Attempt to reuse invite token for user {user_id} from IP {client_ip}")
            InviteUserLog.objects.create(
                user=user,
                business=business,
                status='token_already_used',
                ip_address=client_ip,
                user_agent=user_agent,
                error_message="Invite token has already been used"
            )
            raise Exception("This invite has already been used.")

        # Verify token hash matches stored hash using constant-time comparison
        if not verify_token_hash(token, user_profile.invite_token_hash):
            logger.warning(f"Invalid invite token hash for user {user_id} from IP {client_ip}")
            InviteUserLog.objects.create(
                user=user,
                business=business,
                status='invalid_token',
                ip_address=client_ip,
                user_agent=user_agent,
                error_message="Invite token hash mismatch"
            )
            raise Exception("Invalid invite token.")

        # Verify token is not older than 7 days (more lenient than password reset)
        if user_profile.invite_requested_at:
            token_age = timezone.now() - user_profile.invite_requested_at
            if token_age > datetime.timedelta(days=7):
                logger.warning(f"Expired invite token for user {user_id} from IP {client_ip}")
                InviteUserLog.objects.create(
                    user=user,
                    business=business,
                    status='token_expired',
                    ip_address=client_ip,
                    user_agent=user_agent,
                    error_message="Invite token expired"
                )
                raise Exception("Your invitation has expired.")

        if request.method == 'POST':
            if form.is_valid():
                # Atomic: Update User, UserProfile, and create InviteUserLog
                with db_transaction.atomic():
                    # Update user with name and password
                    user.first_name = form.cleaned_data['first_name']
                    user.last_name = form.cleaned_data['last_name']
                    user.set_password(form.cleaned_data['password'])
                    user.is_active = True
                    user.save()

                    # Mark invite as used and save phone number
                    user_profile.phone_number = form.cleaned_data.get('phone_number')
                    user_profile.invite_token_hash = None
                    user_profile.invite_used = True
                    user_profile.invite_requested_at = None
                    user_profile.email_verified = True  # Mark email as verified since they received the invite
                    user_profile.save(update_fields=[
                        'phone_number',
                        'invite_token_hash',
                        'invite_used',
                        'invite_requested_at',
                        'email_verified',
                    ])

                    business.team_members.filter(user=user).update(is_active=True)

                    # Log successful invite completion
                    InviteUserLog.objects.create(
                        user=user,
                        business=business,
                        status='activation_successful',
                        ip_address=client_ip,
                        user_agent=user_agent
                    )

                logger.info(f"User {user_id} successfully activated invite for {business.name} from IP {client_ip}")
                return redirect('invite_user_done')

    except Exception as e:
        logger.error(f"Invite activation failed: {str(e)} from IP {client_ip}")
        return render(request, 'auth/invite_user.html', {"error": "Invalid or expired invite link.", "token": token})

    return render(
        request,
        "auth/invite_user.html",
        {"form": form, "token": token, "countries": COUNTRIES},
    )


def invite_user_done_view(request):
    return render(request, 'auth/invite_user_done.html')


def decline_invite_view(request, token):
    """Handle invitation decline for existing users"""
    client_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    try:
        # Validate invite token
        token_data = decode_jwt(token, audience_id="invite_user")
        if token_data.get("reference") != "invite_user":
            logger.warning(f"Invalid decline token reference from IP {client_ip}")
            raise Exception("Invalid token provided.")

        user_id = token_data.get("accountID")
        business_id = token_data.get("businessID")
        user = User.objects.get(id=user_id)
        user_profile = UserProfile.objects.get(user=user)
        business = Business.objects.get(alias_id=business_id)

        # Check if invite has already been used
        if user_profile.invite_used:
            logger.warning(f"Attempt to decline already-used invite token for user {user_id} from IP {client_ip}")
            InviteUserLog.objects.create(
                user=user,
                business=business,
                status='token_already_used',
                ip_address=client_ip,
                user_agent=user_agent,
                error_message="Invite token has already been used"
            )
            raise Exception("This invite has already been used.")

        # Verify token hash matches stored hash using constant-time comparison
        if not verify_token_hash(token, user_profile.invite_token_hash):
            logger.warning(f"Invalid token hash for decline from user {user_id} from IP {client_ip}")
            InviteUserLog.objects.create(
                user=user,
                business=business,
                status='invalid_token',
                ip_address=client_ip,
                user_agent=user_agent,
                error_message="Invite token hash mismatch"
            )
            raise Exception("Invalid invite token.")

        # Verify token is not older than 7 days
        if user_profile.invite_requested_at:
            token_age = timezone.now() - user_profile.invite_requested_at
            if token_age > datetime.timedelta(days=7):
                logger.warning(f"Expired decline token for user {user_id} from IP {client_ip}")
                InviteUserLog.objects.create(
                    user=user,
                    business=business,
                    status='token_expired',
                    ip_address=client_ip,
                    user_agent=user_agent,
                    error_message="Invite token expired"
                )
                raise Exception("Your invitation has expired.")

        # Mark invite as declined in atomic transaction
        with db_transaction.atomic():
            # Clear the invite token and mark as declined
            user_profile.invite_token_hash = None
            user_profile.invite_requested_at = None
            user_profile.save(update_fields=['invite_token_hash', 'invite_requested_at'])

            # Remove the team member association
            BusinessTeamMember.objects.filter(business=business, user=user).delete()

            # Log the decline
            InviteUserLog.objects.create(
                user=user,
                business=business,
                status='invitation_declined',
                ip_address=client_ip,
                user_agent=user_agent
            )

        logger.info(f"User {user_id} declined invitation for {business.name} from IP {client_ip}")
        return render(request, 'auth/invite_declined.html', {"business_name": business.name})

    except Exception as e:
        logger.error(f"Invite decline failed: {str(e)} from IP {client_ip}")
        return render(request, 'auth/invite_declined.html', {"error": "Invalid or expired decline request."})


@login_required
@business_admin_required
def change_account_view(request):
    try:
        if request.method == "POST":
            business_id = request.POST.get("business_id")
            if business_id:
                if business_id == "new-business":
                    if request.business.can_transact:
                        return redirect("sub_business_create")
                team_record = request.user.team.get(business_id=business_id)
                if team_record:
                    KEY = f"BIZ_{request.user.id}"
                    cache.set(KEY, team_record.business)
        return redirect("dashboard_overview")
    except Exception as ex:
        logger.error(ex, exc_info=True)
        return redirect("dashboard_overview")


@login_required
@business_admin_required
def users_list_view(request):
    """List all team members for the current business"""
    try:
        # Get current business from middleware
        business = request.business
        if not business:
            return redirect("dashboard_overview")

        # Get all team members
        team_members = (
            BusinessTeamMember.objects.filter(business=business)
            .select_related("user")
            .order_by(
                "-is_active",
                "-created_at",
            )
        )

        # Pagination
        paginator = Paginator(team_members, 20)
        page_num = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_num)

        # Format for template
        users_data = [
            {
                'alias_id': member.alias,
                'first_name': member.user.first_name,
                'last_name': member.user.last_name,
                'email': member.user.email,
                'phone': member.user.profile.phone_number or 'N/A',
                'role': member.role,
                'is_active': member.is_active,
                'archived': member.archived,
                'joined_at': member.joined_at.strftime('%Y-%m-%d'),
            }
            for member in page_obj
        ]

        context = {
            'business': business,
            'users': users_data,
            'page_obj': page_obj,
            'total_users': paginator.count,
        }

        return render(request, 'dashboard/users.html', context)

    except Exception as e:
        logger.error(f"Error loading users list: {str(e)}")
        return redirect('users_list')


@login_required
@business_admin_required
@require_http_methods(["POST"])
def users_add_edit_view(request):
    """Add a team member using AddTeamMemberForm (AJAX endpoint)"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        role = data.get('role', 'staff')
        mode = data.get('mode', 'add')  # 'add' or 'edit'

        # Get current business from middleware
        business = request.business
        if not business:
            return JsonResponse({
                'success': False,
                'error': 'No business selected'
            }, status=400)

        # Validate inputs
        if not email or not role:
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)

        # Use AddTeamMemberForm to handle user creation and invitations
        form_data = {
            'email': email,
            'role': role,
        }

        if mode == 'add':
            form = AddTeamMemberForm(form_data)

            if not form.is_valid():
                errors = form.errors.as_json()
                return JsonResponse({
                    'success': False,
                    'error': 'Form validation failed',
                    'errors': json.loads(errors)
                }, status=400)

            # Save using the form (handles user creation, profile, invitations, emails, tokens)
            user_profile = form.save(business=business, inviter=request.user)
            member = BusinessTeamMember.objects.filter(business=business, user=user_profile.user).first()

            return JsonResponse({
                'success': True,
                'message': 'Team member added successfully',
                'user': {
                    'alias_id': member.alias if member else '',
                    'first_name': user_profile.user.first_name,
                    'last_name': user_profile.user.last_name,
                    'email': user_profile.user.email,
                    'phone': user_profile.phone_number or 'N/A',
                    'role': form.cleaned_data['role'],
                    'is_active': member.is_active if member else False,
                    'joined_at': member.joined_at.strftime('%Y-%m-%d') if member else '',
                }
            })
        elif mode == "edit":
            if request.user == business.owner:
                return JsonResponse({
                    'success': False,
                    'error': 'Business owner role cannot be changed'
                }, status=400)
            try:
                member = BusinessTeamMember.objects.get(
                    user__email=email, business=business
                )
                member.role = role
                member.save(update_fields=['role'])
                return JsonResponse({
                    'success': True,
                    'message': 'Team member role updated successfully',
                })
            except BusinessTeamMember.DoesNotExist:
                return JsonResponse(
                    {"success": False, "error": "Team member not found"}, status=404
                )

    except Business.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Business not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error in users_add_edit_view: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred'
        }, status=500)


@login_required
@business_admin_required
@require_http_methods(["POST"])
def users_delete_view(request):
    """Delete a team member (AJAX endpoint)"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')

        if not user_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)

        # Get current business from middleware
        business = request.business
        if not business:
            return JsonResponse({
                'success': False,
                'error': 'No business selected'
            }, status=400)

        # Delete team member
        with db_transaction.atomic():
            member = BusinessTeamMember.objects.get(alias_id=user_id, business=business)

            # Prevent owner from being removed
            if business.owner == member.user:
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot remove the business owner'
                }, status=400)

            member.archived = not member.archived  # Toggle archived status
            member.is_active = False if member.archived else True  # Toggle active status instead of deleting
            member.save()

        return JsonResponse({
            'success': True,
            'message': 'User status updated successfully',
            'is_active': member.is_active,
            'archived': member.archived
        })

    except BusinessTeamMember.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Team member not found'
        }, status=404)
    except Business.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Business not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error in users_delete_view: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred'
        }, status=500)


@login_required
@business_admin_required
def resend_invite_view(request):
    """Resend invite email to a team member (AJAX endpoint)"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        if not user_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)

        # Get current business from middleware
        business = request.business
        if not business:
            return JsonResponse({
                'success': False,
                'error': 'No business selected'
            }, status=400)

        member = BusinessTeamMember.objects.get(alias_id=user_id, business=business)
        if member.is_active:
            return JsonResponse({
                'success': False,
                'error': 'Member is already active'
            }, status=400)

        # Resend the invite email using the existing token
        invite_token = AddTeamMemberForm.generate_invite_token(member.user.profile, business)
        accept_link = f"{settings.FRONTEND_URL}/invite/{invite_token}/"
        decline_link = f"{settings.FRONTEND_URL}/invite/{invite_token}/decline/"
        inviter_name = request.user.first_name

        send_existing_invitation_email.apply_async(args=[
            member.user.email, 
            member.user.first_name, 
            inviter_name, 
            business.name, 
            accept_link, 
            decline_link,
            business.contact_email or '',
            business.description or ''
        ])

        return JsonResponse({
            'success': True,
            'message': 'Invite email resent successfully'
        })

    except BusinessTeamMember.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Team member not found'
        }, status=404)
    except Business.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Business not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error in resend_invite_view: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred'
        }, status=500)


@login_required
@business_admin_required
@require_http_methods(["POST"])
def users_toggle_status_view(request):
    """Toggle team member active/inactive status (AJAX endpoint)"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        
        if not user_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)
        
        # Get current business from middleware
        business = request.business
        if not business:
            return JsonResponse({
                'success': False,
                'error': 'No business selected'
            }, status=400)
        
        
        # Toggle team member status
        with db_transaction.atomic():
            member = BusinessTeamMember.objects.get(alias_id=user_id, business=business)
            
            # Prevent deactivating the owner
            if business.owner == member.user:
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot deactivate the business owner'
                }, status=400)
            
            member.is_active = not member.is_active
            member.save(update_fields=['is_active'])
        
        status_text = 'activated' if member.is_active else 'deactivated'
        return JsonResponse({
            'success': True,
            'message': f'User {status_text} successfully',
            'is_active': member.is_active
        })
    
    except BusinessTeamMember.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Team member not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error in users_toggle_status_view: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred'
        }, status=500)


def manage_users_view(request):
    return users_list_view(request)
