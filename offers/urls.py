from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="offers/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.offer_list, name="offer_list"),
    path("archiwum/", views.offer_list, name="archive"),
    path("oferta/nowa/", views.offer_create, name="offer_create"),
    path("oferta/<int:pk>/", views.offer_edit, name="offer_edit"),
    path("oferta/<int:pk>/zapis/", views.offer_save, name="offer_save"),
    path("oferta/<int:pk>/pdf/", views.offer_print, name="offer_print"),
    path("oferta/<int:pk>/excel/", views.offer_excel, name="offer_excel"),
    path("ustawienia/", views.settings_view, name="settings"),
    path("szukaj/", views.product_search, name="product_search"),
    path("klienci/", views.client_search, name="client_search"),
    path("zdjecie/<path:filename>", views.product_photo, name="product_photo"),
]
