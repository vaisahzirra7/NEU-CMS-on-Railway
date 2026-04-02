from pathlib import Path
from decouple import config
import dj_database_url
import os

# =============================================================================
# VanaraUniCare — NEU HMS
# North-Eastern University Health Management System
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

# Render provides the DOMAIN via environment variable, but we should fallback to '*' if missing to avoid 400 Bad Request during the initial deployment when the exact URL might not be set.
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')


# =============================================================================
# APPLICATIONS
# =============================================================================
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

LOCAL_APPS = [
    'accounts',
    'patients',
    'appointments',
    'inventory',
    'prescriptions',
    'wards',
    'laboratory',
    'documents',
    'consultations',
    'clearance',
    'reports',
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS



# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',        # ← Whitenoise for static files MUST be right after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'


# =============================================================================
# TEMPLATES
# =============================================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],   # Global templates folder
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.user_permissions',  # Custom context processor for permissions
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# =============================================================================
# DATABASE — MySQL
# =============================================================================
# DATABASES = {
#     'default': {
#         'ENGINE':   'django.db.backends.mysql',
#         'NAME':     config('DB_NAME'),
#         'USER':     config('DB_USER'),
#         'PASSWORD': config('DB_PASSWORD'),
#         'HOST':     config('DB_HOST', default='localhost'),
#         'PORT':     config('DB_PORT', default='3306'),
#         'OPTIONS': {
#             'charset': 'utf8mb4',
#             'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#         },
#     }
# }


# Database fallback to mySQL locally if no DATABASE_URL is defined.
# This prevents dj_database_url from crashing when DATABASE_URL is None or an empty string.
DATABASE_URL = os.environ.get('DATABASE_URL') or config('DATABASE_URL', default=None)

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    # Local dev — use MySQL
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.mysql',
            'NAME':     config('DB_NAME'),
            'USER':     config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST':     config('DB_HOST', default='localhost'),
            'PORT':     config('DB_PORT', default='3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
    
# =============================================================================
# CUSTOM AUTH — We use our own User model in accounts app
# =============================================================================
AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL          = '/auth/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/auth/login/'


# =============================================================================
# PASSWORD VALIDATION
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# =============================================================================
# INTERNATIONALIZATION
# =============================================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Africa/Lagos'
USE_I18N      = True
USE_TZ        = True


# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================
STATIC_URL  = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Whitenoise static file compression wrapper
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'            # Uploaded files (photos, documents etc.)


# =============================================================================
# DEFAULT PRIMARY KEY
# =============================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =============================================================================
# SESSION
# =============================================================================
SESSION_COOKIE_AGE      = 1800          # 30 minutes — matches system setting
SESSION_SAVE_EVERY_REQUEST = True       # Reset timer on every request
SESSION_EXPIRE_AT_BROWSER_CLOSE = True


# =============================================================================
# MESSAGES — for flash notifications (success, error etc.)
# =============================================================================
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG:   'debug',
    messages.INFO:    'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR:   'danger',
}


# =============================================================================
# EMAIL (configure properly when ready to send emails)
# =============================================================================
#Comment whiever one you may not want to use.

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend' # Use SMTP backend for production
#EMAIL_BACKEND       = 'django.core.mail.backends.console.EmailBackend'  # Prints to console in dev

EMAIL_HOST          = config('SMTP_HOST',     default='')
EMAIL_PORT          = config('SMTP_PORT',     default=587,   cast=int)
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = config('SMTP_USER',     default='')
EMAIL_HOST_PASSWORD = config('SMTP_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = config('FROM_EMAIL',    default='noreply@neu.edu.ng')


# =============================================================================
# SECURITY — enforced in production (when DEBUG is False)
# =============================================================================
if not DEBUG:
    SECURE_PROXY_SSL_HEADER     = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT         = True
    SESSION_COOKIE_SECURE       = True
    CSRF_COOKIE_SECURE          = True
    SECURE_BROWSER_XSS_FILTER   = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# =============================================================================
# NEU HMS — Application-specific settings
# =============================================================================
NEU_HMS = {
    'CLINIC_NAME':              'North-Eastern University Clinic',
    'UNIVERSITY_NAME':          'North-Eastern University',
    'SYSTEM_NAME':              'VanaraUniCare',
    'VERSION':                  '1.0.0',
    'PRESCRIPTION_VALID_DAYS':  30,
    'MAX_LOGIN_ATTEMPTS':       5,
    'PATIENT_UID_PREFIX':       'NEU',
    'PRESCRIPTION_UID_PREFIX':  'NEU-RX',
    'APPOINTMENT_UID_PREFIX':   'APT',
    'ADMISSION_UID_PREFIX':     'ADM',
    'LAB_UID_PREFIX':           'LAB',
    'DOC_UID_PREFIX':           'DOC',
    'EXPIRY_ALERT_DAYS':        [90, 60, 30],
}