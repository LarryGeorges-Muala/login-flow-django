import ast
import pyotp
import qrcode
import datetime
from django.conf import settings
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views import View, generic
from django.urls import reverse
from django.views.decorators import csrf, http
from django.contrib.auth import decorators, authenticate, login, logout
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from . import models
from common import _common_modules, _otel_modules

from io import BytesIO
from cryptography.fernet import Fernet
from prometheus_client import generate_latest


'''
    Decorators
'''
decorator_secured_gets = [
    http.require_http_methods(['GET']),
    csrf.csrf_protect,
]
decorator_protected_secured_gets = [
    http.require_http_methods(['GET']),
    csrf.csrf_protect,
    decorators.login_required,
]
decorator_secured_posts = [
    http.require_http_methods(['POST']),
    csrf.csrf_protect,
]
decorator_protected_secured_posts = [
    http.require_http_methods(['POST']),
    csrf.csrf_protect,
    decorators.login_required,
]
decorator_relaxed_posts = [
    http.require_http_methods(['POST']),
    csrf.csrf_exempt,
    csrf.ensure_csrf_cookie,
]
decorator_secured_endpoints = [
    http.require_http_methods(['GET', 'POST']),
    csrf.csrf_protect,
]


'''
    Endpoints
'''
@method_decorator(
    decorator_secured_gets, 
    name='dispatch'
)
class Health(View):
    def get(self, request):
        _otel_modules.request_counter_health_endpoint.add(
            1,
            {
                'http.method': request.method,
                'http.route': request.path
            }
        )
        return JsonResponse(
            {
                'status': 'up',
                'current_time': datetime.datetime.now()
            }
        )


@method_decorator(
    decorator_secured_gets, 
    name='dispatch'
)
class PrometheusMetrics(View):
    ''' Expose Prometheus metrics, including log counters. '''
    metrics = generate_latest()  # Generate all Prometheus metrics
    def get(self, request, *args, **kwargs):
        return HttpResponse(
            self.metrics,
            content_type='text/plain'
        )


@method_decorator(
    decorator_secured_endpoints, 
    name='dispatch'
)
class Index(generic.TemplateView):
    template_name = 'flow/index.html'

    def dispatch(self, request, *args, **kwargs):
        # Authed Flow
        if request.user.is_authenticated:
            return redirect('/profile')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # Registration Flow
        context = super().get_context_data(**kwargs)
        context['welcome_message'] = 'Hello and welcome!'
        context['user'] = self.request.user
        status_message = self.request.session.get('status_message', '')
        if status_message:
            del self.request.session['status_message']
        context['status_message'] = status_message
        return context

    def post(self, request, *args, **kwargs):
        # Extract Post Data - First Name
        first_name = request.POST.get('first_name', '')
        if not first_name:
            request.session['status_message'] = 'Missing first name...'
            return HttpResponseRedirect(reverse('flow:index'))
        # Extract Post Data - Last Name
        last_name = request.POST.get('last_name', '')
        if not last_name:
            request.session['status_message'] = 'Missing last name...'
            return HttpResponseRedirect(reverse('flow:index'))
        # Extract Post Data - Email
        email = request.POST.get('email', '')
        if not email:
            request.session['status_message'] = 'Missing email...'
            return HttpResponseRedirect(reverse('flow:index'))
        # Extract Post Data - Password
        password = request.POST.get('password', '')
        if not password:
            request.session['status_message'] = 'Missing password...'
            return HttpResponseRedirect(reverse('flow:index'))
        # Check Existing User
        try:
            User.objects.get(
                username=email
            )
            request.session['status_message'] = 'Existing account, please login...'
            return HttpResponseRedirect(reverse('flow:index'))
        except User.DoesNotExist:
            # Create New User
            User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            # Confirm New User
            user = authenticate(
                request,
                username=email,
                password=password
            )
            # Login New User
            if user is not None:
                login(request, user)
                # Create TOTP Profile
                try:
                    token = pyotp.random_base32()
                    qr_code_url = pyotp.totp.TOTP(
                        token
                    ).provisioning_uri(
                        name=email,
                        issuer_name='Django Login Flow App'
                    )
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=5,
                        border=2,
                    )
                    qr.add_data(
                        qr_code_url
                    )
                    qr.make(
                        fit=True
                    )
                    qr_code_img = qr.make_image(
                        fill_color="black",
                        back_color="white"
                    )
                    # qr_code_img.save("qr_code_img.png")
                    buffer = BytesIO()
                    qr_code_img.save(
                        buffer,
                        format="PNG"
                    )
                    qr_code_img_buffer = ContentFile(
                        buffer.getvalue()
                    )
                    try:
                        # Encrypt Token
                        cipher_suite_default = Fernet(
                            settings.CRYPTOGRAPHY_KEY
                        )
                        client = models.Client.objects.create(
                            user=self.request.user,
                            enabled=True,
                            active=False,
                            token=cipher_suite_default.encrypt(
                                str(token).encode('utf-8')
                            ),
                            qr_code_url=cipher_suite_default.encrypt(
                                str(qr_code_url).encode('utf-8')
                            ),
                        )
                        client.qr_code.save(
                            '{}.png'.format(self.request.user.id),
                            qr_code_img_buffer,
                            save=True
                        )
                    except Exception as e:
                        _common_modules.logger_error(e)
                except Exception as e:
                    _common_modules.logger_error(e)
                return HttpResponseRedirect(reverse('flow:profile'))
        except Exception as e:
            _common_modules.logger_error(e)
        return HttpResponseRedirect(reverse('flow:index'))


@method_decorator(
    decorator_secured_endpoints, 
    name='dispatch'
)
class Profile(generic.TemplateView):
    template_name = 'flow/profile.html'

    def get_context_data(self, **kwargs):
        # Check MFA
        mfa = None
        try:
            mfa_component = models.Client.objects.filter(user=self.request.user).first()
            if mfa_component:
                if mfa_component.enabled:
                    if not mfa_component.active:
                        mfa = mfa_component
                    else:
                        if mfa_component.reset_mfa():
                            mfa_component.active = False
                            mfa_component.save()
                            mfa = mfa_component
        except Exception as e:
            _common_modules.logger_error(e)
        # Login Flow
        context = super().get_context_data(**kwargs)
        context['welcome_message'] = 'Profile!'
        context['user'] = self.request.user
        context['mfa'] = mfa
        status_message = self.request.session.get('status_message', '')
        if status_message:
            del self.request.session['status_message']
        context['status_message'] = status_message
        return context

    def post(self, request, *args, **kwargs):
        # MFA
        code = request.POST.get('code', '')
        if code:
            mfa = models.Client.objects.filter(
                user=self.request.user
            ).first()
            if mfa:
                if mfa.enabled:
                    try:
                        # Decrypt Token
                        cipher_suite = Fernet(
                            settings.CRYPTOGRAPHY_KEY
                        )
                        totp = pyotp.TOTP(
                            (
                                cipher_suite.decrypt(
                                    ast.literal_eval(mfa.token)
                                )
                            ).decode('utf-8')
                        )
                        # Check Token Session
                        session_valid = totp.verify(code)
                        if session_valid:
                            mfa.active = True
                            mfa.save()
                            return HttpResponseRedirect(reverse('flow:profile'))
                        if not session_valid:
                            request.session['status_message'] = 'Invalid code... Please try again...'
                            return HttpResponseRedirect(reverse('flow:profile'))
                    except Exception as e:
                        _common_modules.logger_error(e)
        if not code:
            # Clear session
            logout(request)
        # Extract Post Data - Email
        email = request.POST.get('email', '')
        if not email:
            request.session['status_message'] = 'Missing email...'
            return HttpResponseRedirect(reverse('flow:profile'))
        # Extract Post Data - Password
        password = request.POST.get('password', '')
        if not password:
            request.session['status_message'] = 'Missing password...'
            return HttpResponseRedirect(reverse('flow:profile'))
        # Check Existing User
        try:
            user = User.objects.get(
                username=email
            )
            # Check Password
            if not user.check_password(password):
                request.session['status_message'] = 'Invalid password... Please try again...'
                return HttpResponseRedirect(reverse('flow:profile'))
            # Login New User
            auth_user = authenticate(
                request,
                username=user.email,
                password=password
            )
            if auth_user is None:
                request.session['status_message'] = 'Invalid login details... Please try again...'
                return HttpResponseRedirect(reverse('flow:profile'))
            if auth_user is not None:
                login(request, auth_user)
                return HttpResponseRedirect(reverse('flow:profile'))
        except User.DoesNotExist:
            # Switch to Registration
            request.session['status_message'] = 'Account not found... Please register...'
            return HttpResponseRedirect(reverse('flow:index'))
        except Exception as e:
            _common_modules.logger_error(e)
        return HttpResponseRedirect(reverse('flow:index'))


@method_decorator(
    decorator_protected_secured_posts, 
    name='dispatch'
)
class UpdateUser(View):
    def post(self, request, *args, **kwargs):
        # Extract Post Data - First Name
        first_name = request.POST.get('first_name', '')
        if not first_name:
            request.session['status_message'] = 'Missing first name...'
            return HttpResponseRedirect(reverse('flow:profile'))
        # Extract Post Data - Last Name
        last_name = request.POST.get('last_name', '')
        if not last_name:
            request.session['status_message'] = 'Missing last name...'
            return HttpResponseRedirect(reverse('flow:profile'))
        # Extract Post Data - Email
        email = request.POST.get('email', '')
        if not email:
            request.session['status_message'] = 'Missing email...'
            return HttpResponseRedirect(reverse('flow:profile'))
        # Extract Post Data - Password
        password = request.POST.get('password', '')
        if not password:
            request.session['status_message'] = 'Missing password...'
            return HttpResponseRedirect(reverse('flow:profile'))
        # Check Existing User
        try:
            user = User.objects.get(
                username=email
            )
            # Check Password
            if not user.check_password(password):
                request.session['status_message'] = 'Invalid password... Please try again...'
                return HttpResponseRedirect(reverse('flow:profile'))
            # Update Names
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            # Check New Email
            new_email = request.POST.get('profile', '')
            if new_email:
                user.email = new_email
                user.save()
            # Check New Password
            auth_password = password
            new_password = request.POST.get('new_password', '')
            if new_password:
                user.set_password(new_password)
                user.save()
                auth_password = new_password
            # Auth User
            auth_user = authenticate(
                request,
                username=user.email,
                password=auth_password
            )
            if auth_user is None:
                request.session['status_message'] = 'Invalid details... Please try again...'
                return HttpResponseRedirect(reverse('flow:profile'))
            if auth_user is not None:
                login(request, auth_user)
                request.session['status_message'] = 'Profile updated!'
                return HttpResponseRedirect(reverse('flow:profile'))
        except User.DoesNotExist:
            # Switch to Registration
            request.session['status_message'] = 'Account not found... Please register...'
            return HttpResponseRedirect(reverse('flow:index'))
        except Exception as e:
            _common_modules.logger_error(e)
        return HttpResponseRedirect(reverse('flow:profile'))


@method_decorator(
    decorator_protected_secured_posts, 
    name='dispatch'
)
class Logout(View):
    def post(self, request, *args, **kwargs):
        try:
            mfa = models.Client.objects.filter(user=self.request.user).first()
            if mfa:
                mfa.active = False
                mfa.save()
        except Exception as e:
            _common_modules.logger_error(e)
        # Clear session
        logout(request)
        return HttpResponseRedirect(reverse('flow:profile'))
