from django.conf import settings # import the settings file

def workflow(request):
    # return the value you want as a dictionnary. you may add multiple values in there.

    doc_link = '/' + settings.BASE_API_URL + '/workflow/static/documentation/index.html'

    return {'FLOWER_URL': settings.FLOWER_URL, 'BASE_API_URL': settings.BASE_API_URL, 'DOCUMENTATION_LINK': doc_link}