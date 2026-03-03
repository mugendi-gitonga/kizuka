import datetime

from django import forms
from django.forms import ModelForm
from django.contrib.auth.models import User
from django.db import transaction as db_transaction
from django.conf import settings
from django.contrib.auth import authenticate, login


from user_accounts.tasks import send_existing_invitation_email, send_invitation_email, send_verification_email
from utils import check_phone_number, encode_jwt
from .utils import hash_token
from .models import Business, BusinessTeamMember, UserProfile

class LoginForm(forms.Form):
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'you@example.com',
            'class': 'input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'class': 'input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none'
        }),
        required=True
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("Invalid email or password.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if user is None:
                raise forms.ValidationError("Invalid email or password.")
            cleaned_data['user'] = user
        return cleaned_data


class SignUpForm(forms.Form):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'John',
            'class': 'input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Doe',
            'class': 'input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none'
        })
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'you@example.com',
            'class': 'input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Create a strong password',
            'class': 'input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none'
        }),
        required=True
    )
    country = forms.CharField(
        max_length=3,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-900 text-sm focus:outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600'
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '+1 (555) 123-4567',
            'class': 'input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm your password',
            'class': 'input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none'
        }),
        required=True
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_password(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")

        return password

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and not phone_number.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")

        phone_number = check_phone_number(phone_number, country=self.cleaned_data.get('country'))
        return phone_number

    def save(self):
        with db_transaction.atomic():
            user = User.objects.create_user(
                username=self.cleaned_data['email'],
                email=self.cleaned_data['email'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                password=self.cleaned_data['password']
            )

            business = Business.objects.create(
                owner=user,
                name=f"{user.first_name}'s Business"
            )
            business.team_members.create(
                user=user,
                role='admin',
                is_active=True
            )

            token_data = {
                "accountID": user.id,
                "reference": "email_verification",
                "expires_in": (datetime.datetime.utcnow() + datetime.timedelta(hours=24)).timestamp()
            }

            from utils import encode_jwt
            verification_token = encode_jwt(token_data, account_id=user.id, reference="email_verification", expiry=24*3600)

            profile = UserProfile.objects.create(
                user=user,
                phone_number=self.cleaned_data.get('phone_number'),
                verification_token=verification_token
            )
            verification_link = f"{settings.FRONTEND_URL}/verify-email/{verification_token}"
            send_verification_email.apply_async(args=[user.email, user.first_name, verification_link])

            return user


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(
            attrs={
                "placeholder": "you@example.com",
                "class": "input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none",
            }
        ),
    )


class ResetPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter your new password",
                "class": "input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none",
            }
        ),
        min_length=8,
        required=True,
    )
    new_password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Re-enter your new password",
                "class": "input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none",
            }
        ),
        min_length=8,
        required=True,
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data


class InviteUserForm(forms.Form):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'John',
            'class': 'input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Doe',
            'class': 'input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Create a strong password',
            'class': 'input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none'
        }),
        required=True,
        min_length=8
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm your password',
            'class': 'input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none'
        }),
        required=True,
        min_length=8
    )
    country = forms.CharField(
        max_length=3,
        required=False,
        widget=forms.Select(
            attrs={
                "class": "w-full px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-900 text-sm focus:outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600"
            }
        ),
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '+1 (555) 123-4567',
            'class': 'input input-bordered w-full bg-white border-slate-300 focus:border-blue-600 focus:outline-none'
        })
    )

    def clean_password(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match.")

        return password

    def clean_phone_number(self):
        cleaned_data = super().clean()
        phone_number = cleaned_data.get('phone_number')
        country = cleaned_data.get("country")
        if phone_number and not phone_number.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")

        phone_number = check_phone_number(phone_number, country=country)
        return phone_number


class AddTeamMemberForm(forms.Form):
    email = forms.EmailField(max_length=254, required=True)
    role = forms.ChoiceField(choices=BusinessTeamMember.ROLES_CHOICES, required=True)

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role not in dict(BusinessTeamMember.ROLES_CHOICES):
            raise forms.ValidationError("Invalid role selected.")
        return role

    def save(self, business, inviter=None):
        with db_transaction.atomic():
            email = self.cleaned_data.get("email")
            user, created = User.objects.get_or_create(username=email, email=email)
            user_profile, profile_created = UserProfile.objects.get_or_create(user=user)

            user_team = BusinessTeamMember.objects.create(
                business=business,
                user=user,
                role=self.cleaned_data['role']
            )

            # token_data = {
            #     "accountID": user.id,
            #     "businessID": business.alias_id,
            #     "reference": "invite_user",
            #     "expires_in": (
            #         datetime.datetime.now() + datetime.timedelta(days=7)
            #     ).timestamp(),
            # }
            # invite_token = encode_jwt(token_data, account_id=user.id, reference="invite_user", expiry=7*24*3600)
            # user_profile.invite_token_hash = hash_token(invite_token)
            # user_profile.invite_requested_at = datetime.datetime.now()
            # user_profile.save(update_fields=['invite_token_hash', 'invite_requested_at'])

            invite_token = self.generate_invite_token(user_profile, business)
            
            if profile_created:
                db_transaction.on_commit(lambda: send_invitation_email.apply_async(args=[user.email, user.first_name, business.name]))
                return user_profile

            # For existing users, generate invite token and links
            accept_link = f"{settings.FRONTEND_URL}/invite/{invite_token}/"
            decline_link = f"{settings.FRONTEND_URL}/invite/{invite_token}/decline/"
            inviter_name = inviter.get_full_name() if inviter else "An admin"

            db_transaction.on_commit(lambda: send_existing_invitation_email.apply_async(args=[
                user.email, 
                user.first_name, 
                inviter_name, 
                business.name, 
                accept_link, 
                decline_link,
                business.contact_email or '',
                business.description or ''
            ]))

        return user_profile

    def generate_invite_token(user_profile, business):
        user = user_profile.user
        token_data = {
            "accountID": user.id,
            "businessID": business.alias_id,
            "reference": "invite_user",
            "expires_in": (datetime.datetime.now() + datetime.timedelta(days=7)).timestamp()
        }
        invite_token = encode_jwt(token_data, account_id=user.id, reference="invite_user", expiry=7*24*3600)
        user_profile.invite_token_hash = hash_token(invite_token)
        user_profile.invite_requested_at = datetime.datetime.now()
        user_profile.save(update_fields=['invite_token_hash', 'invite_requested_at'])
        return invite_token
