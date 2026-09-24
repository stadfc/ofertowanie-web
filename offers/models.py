from decimal import Decimal

from django.conf import settings
from django.db import models


class Product(models.Model):
    kod = models.CharField(max_length=64, db_index=True)
    nazwa = models.CharField(max_length=800)
    combi = models.CharField(max_length=900, db_index=True)
    cena_det = models.DecimalField(max_digits=12, decimal_places=2)
    cena_baz = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    waluta = models.CharField(max_length=8, default="PLN", db_index=True)
    zdjecie = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["combi"]

    def __str__(self) -> str:
        return self.combi

    @property
    def photo_url(self) -> str:
        if not self.zdjecie:
            return ""
        from django.urls import reverse
        return reverse("product_photo", args=[self.zdjecie])


class Client(models.Model):
    nazwa = models.CharField(max_length=250, db_index=True)
    adres = models.CharField(max_length=400, blank=True)
    nip = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["nazwa"]

    def __str__(self) -> str:
        return self.nazwa


class Offer(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="offers"
    )
    nazwa = models.CharField(max_length=200, blank=True, default="Propozycja")
    platnik = models.ForeignKey(
        Client, null=True, blank=True, on_delete=models.SET_NULL, related_name="offers_platnik"
    )
    platnik_nazwa = models.CharField(max_length=250, blank=True)
    platnik_adres = models.CharField(max_length=400, blank=True)
    platnik_nip = models.CharField(max_length=20, blank=True)
    odbiorca = models.ForeignKey(
        Client, null=True, blank=True, on_delete=models.SET_NULL, related_name="offers_odbiorca"
    )
    odbiorca_nazwa = models.CharField(max_length=250, blank=True)
    odbiorca_adres = models.CharField(max_length=400, blank=True)
    created_on = models.DateField()
    valid_days = models.PositiveIntegerField(default=14)
    with_photos = models.BooleanField(default=True)
    show_codes = models.BooleanField(default=True)
    koszt_transportu = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("20.00"))

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.nazwa} ({self.created_on})"


class SalespersonProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    telefon = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    stanowisko = models.CharField(max_length=120, blank=True)
    kontakt = models.CharField(max_length=400, blank=True)
    komunikat_otwarcia = models.TextField(blank=True)
    komunikat_zamkniecia = models.TextField(blank=True)
    zdjecie = models.ImageField(upload_to="handlowcy/", blank=True)

    def __str__(self) -> str:
        return self.user.get_full_name() or self.user.username


class FxRate(models.Model):
    waluta = models.CharField(max_length=8, unique=True)
    kurs_pln = models.DecimalField(max_digits=12, decimal_places=4)
    nazwa = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["waluta"]

    def __str__(self) -> str:
        return f"{self.waluta}/PLN {self.kurs_pln}"


class OfferLine(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="lines")
    position = models.PositiveIntegerField()
    combi = models.CharField(max_length=900, blank=True)
    rabat = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0"))
    ilosc = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["position"]

    @property
    def product(self):
        if not self.combi:
            return None
        kod = self.combi.split(" ", 1)[0]
        return Product.objects.filter(kod=kod).first() or Product.objects.filter(combi=self.combi).first()
