from django.conf import settings  # import the settings file


def workflow(request):
    # return the value you want as a dictionnary. you may add multiple values in there.

    if request.realm_code:
        doc_link = '/' + request.realm_code + '/' + request.space_code + '/workflow/static/documentation/index.html'
        log_link = '/' + request.realm_code + '/' + request.space_code + '/workflow/api/log'
    else:
        doc_link = '/' + request.space_code + '/workflow/static/documentation/index.html'
        log_link = '/' + request.space_code + '/workflow/api/log'

    return {'FLOWER_URL': settings.FLOWER_URL,
            'BASE_API_URL': settings.BASE_API_URL,
            'DOCUMENTATION_LINK': doc_link,
            'LOG_LINK': log_link}
