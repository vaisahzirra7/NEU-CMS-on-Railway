from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def permission_required(module_slug, action='view'):
    """
    Decorator that checks whether the logged-in user has the given
    action permission on the given module.

    @permission_required('patients', 'view')
    @permission_required('prescriptions', 'create')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user

            # Not logged in — send to login
            if not user.is_authenticated:
                return redirect('login')

            # Superusers bypass all checks
            if user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Use the model's built-in helper
            perm = user.get_module_permission(module_slug)
            key  = f'can_{action}'

            if perm.get(key):
                return view_func(request, *args, **kwargs)

            # No permission — show error and redirect to dashboard
            action_labels = {
                'view':   'view',
                'create': 'create records in',
                'edit':   'edit records in',
                'delete': 'delete records in',
                'export': 'export data from',
            }
            label = action_labels.get(action, action)
            messages.error(
                request,
                f'⛔ You do not have permission to {label} '
                f'<strong>{module_slug.replace("-", " ").title()}</strong>. '
                f'Contact your administrator if you need access.'
            )
            return redirect('dashboard')

        return wrapper
    return decorator