from vincab_app.api_views.common_imports import *

# index page
def index(request):
    return HttpResponse("Hello world!")
