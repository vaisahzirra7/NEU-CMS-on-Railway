# accounts/context_processors.py
#
# Add this to TEMPLATES[0]['OPTIONS']['context_processors'] in settings.py:
#
#   'accounts.context_processors.user_permissions',
#
# Then in ANY template across the entire project you can use:
#
#   {% if perms_map.patients.can_view %}   ... {% endif %}
#   {% if perms_map.patients.can_create %} ... {% endif %}
#   {% if perms_map.patients.can_edit %}   ... {% endif %}
#   {% if perms_map.patients.can_delete %} ... {% endif %}
#   {% if perms_map.patients.can_export %} ... {% endif %}
#
# Works for any module slug:
#   perms_map.consultations.can_view
#   perms_map.inventory.can_create
#   perms_map.laboratory.can_edit
#   etc.
#
# Superusers automatically get True for everything.


def user_permissions(request):
    """
    Injects `perms_map` into every template context.
    perms_map is a dict of { module_slug: { can_view, can_create, ... } }
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {'perms_map': {}}

    user = request.user

    # Superusers get full access to everything without hitting the DB
    if user.is_superuser:
        class FullAccess:
            can_view   = True
            can_create = True
            can_edit   = True
            can_delete = True
            can_export = True
            def __getitem__(self, key):
                return True
            def get(self, key, default=None):
                return True

        class SuperPermsMap:
            def __getattr__(self, slug):
                return FullAccess()
            def __getitem__(self, slug):
                return FullAccess()
            def get(self, slug, default=None):
                return FullAccess()

        return {'perms_map': SuperPermsMap()}

    # For regular users, build the map from their role + overrides
    # We load all at once to avoid N+1 queries
    perms_map = {}

    # Load role permissions
    if user.role:
        role_perms = user.role.permissions.select_related('module').filter(
            module__is_active=True
        )
        for rp in role_perms:
            perms_map[rp.module.slug] = {
                'can_view':   rp.can_view,
                'can_create': rp.can_create,
                'can_edit':   rp.can_edit,
                'can_delete': rp.can_delete,
                'can_export': rp.can_export,
            }

    # Apply individual overrides (None = inherit from role, so skip those)
    overrides = user.permission_overrides.select_related('module').filter(
        module__is_active=True
    )
    for ov in overrides:
        slug = ov.module.slug
        if slug not in perms_map:
            perms_map[slug] = {
                'can_view': False, 'can_create': False,
                'can_edit': False, 'can_delete': False, 'can_export': False,
            }
        if ov.can_view   is not None: perms_map[slug]['can_view']   = ov.can_view
        if ov.can_create is not None: perms_map[slug]['can_create'] = ov.can_create
        if ov.can_edit   is not None: perms_map[slug]['can_edit']   = ov.can_edit
        if ov.can_delete is not None: perms_map[slug]['can_delete'] = ov.can_delete
        if ov.can_export is not None: perms_map[slug]['can_export'] = ov.can_export

    # Wrap in a dict-like object that returns all-False for unknown slugs
    # so templates never crash with KeyError
    class PermsMap:
        def __init__(self, data):
            self._data = data

        def __getattr__(self, slug):
            return self._get(slug)

        def __getitem__(self, slug):
            return self._get(slug)

        def get(self, slug, default=None):
            return self._get(slug)

        def _get(self, slug):
            d = self._data.get(slug, {})
            class P:
                can_view   = d.get('can_view',   False)
                can_create = d.get('can_create', False)
                can_edit   = d.get('can_edit',   False)
                can_delete = d.get('can_delete', False)
                can_export = d.get('can_export', False)
            return P()

    return {'perms_map': PermsMap(perms_map)}