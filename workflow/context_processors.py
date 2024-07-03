from django.conf import settings  # import the settings file


def workflow(request):
    # return the value you want as a dictionnary. you may add multiple values in there.

    if request.realm_code:
        url_prefix = '/' + request.realm_code + '/' + request.space_code
    else:
        url_prefix = '/' + request.space_code

    return {'FLOWER_URL': settings.FLOWER_URL,
            'SPACE_CODE': request.space_code,
            'REALM_CODE': request.realm_code,
            'DOCUMENTATION_LINK': url_prefix + '/workflow/static/documentation/index.html',
            'API_DOCUMENTATION_LINK': url_prefix + '/workflow/docs/api/',
            'LOG_LINK': url_prefix + '/workflow/api/log',
            'DOMAIN_NAME': settings.DOMAIN_NAME,
            }
