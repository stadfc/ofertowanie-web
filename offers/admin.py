from django.contrib import admin

from .models import Client, FxRate, Offer, OfferLine, Product, SalespersonProfile


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("kod", "nazwa", "cena_det", "cena_baz", "waluta", "zdjecie")
    search_fields = ("kod", "nazwa", "combi")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("nazwa", "nip", "adres")
    search_fields = ("nazwa", "nip")


class OfferLineInline(admin.TabularInline):
    model = OfferLine
    extra = 0


@admin.register(SalespersonProfile)
class SalespersonProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "telefon", "email", "stanowisko")


@admin.register(FxRate)
class FxRateAdmin(admin.ModelAdmin):
    list_display = ("waluta", "kurs_pln", "nazwa")


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("nazwa", "odbiorca_nazwa", "platnik_nazwa", "created_on", "created_by")
    inlines = [OfferLineInline]
