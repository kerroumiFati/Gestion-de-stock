from django.shortcuts import render, redirect
from django.templatetags.static import static


def app_download_page(request):
    apk_url = request.build_absolute_uri(static('app/app.apk'))
    context = {'apk_url': apk_url}
    return render(request, 'frontoffice/app_download.html', context)


def app_download_redirect(request):
    return redirect(static('app/app.apk'))
