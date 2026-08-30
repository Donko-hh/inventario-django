from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='login')
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_role = str(user.role).lower()
            allowed = [r.lower() for r in allowed_roles]

            if user_role in allowed:
                return view_func(request, *args, **kwargs)

            messages.error(
                request,
                f'Acceso denegado: Tu perfil ({user.get_role_display()}) no tiene permisos para realizar esta accion.'
            )
            return redirect('dashboard')
        return _wrapped_view
    return decorator


def admin_required(view_func):
    return role_required(['admin'])(view_func)


def bodeguero_or_admin_required(view_func):
    return role_required(['admin', 'bodeguero'])(view_func)