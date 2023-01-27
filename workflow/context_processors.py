from django.conf import settings # import the settings file

def workflow(request):
    # return the value you want as a dictionnary. you may add multiple values in there.
    return {'FLOWER_URL': settings.FLOWER_URL}