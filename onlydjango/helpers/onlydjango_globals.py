from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

def global_settings(request):
    """
    Context processor to inject global variables for templates.
    Raises ImproperlyConfigured if any required SITE_/OG_/TWITTER_ setting is missing.
    """
    # map of required setting names → context key names
    required = {
        'SITE_NAME': 'site_name',
        'SITE_AUTHOR': 'author',
        'SITE_KEYWORDS': 'keywords',
        'SITE_DESCRIPTION': 'description',
        'OG_TYPE': 'og_type',
        'OG_TITLE': 'og_title',
        'OG_DESCRIPTION': 'og_description',
        'OG_IMAGE': 'og_image',
        'TWITTER_CARD': 'twitter_card',
        'TWITTER_TITLE': 'twitter_title',
        'TWITTER_DESCRIPTION': 'twitter_description',
        'TWITTER_IMAGE': 'twitter_image',
    }

    context = {}
    for setting_name, key in required.items():
        if not hasattr(settings, setting_name):
            raise ImproperlyConfigured(
                f"Missing setting `{setting_name}` required by global_settings. "
                f"Add, for example, in settings.py:\n"
                f"    {setting_name} = 'Your value here'"
            )
        context[key] = getattr(settings, setting_name)

    # OG URL comes from the request itself
    context['og_url'] = request.build_absolute_uri()

    return context
