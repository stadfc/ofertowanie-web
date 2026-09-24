from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from offers.models import Client, Offer, OfferLine, Product, SalespersonProfile

CLIENTS = [
    {
        "nazwa": "Restauracja Demo Sp. z o.o.",
        "adres": "ul. Kuchenna 12, 00-001 Warszawa",
        "nip": "5251234567",
    },
    {
        "nazwa": "Hotel Zielony Park",
        "adres": "al. Lipowa 8, 31-002 Kraków",
        "nip": "6779876543",
    },
    {
        "nazwa": "Catering Morze",
        "adres": "ul. Portowa 3, 80-001 Gdańsk",
        "nip": "5831112223",
    },
    {
        "nazwa": "Stołówka Fabryczna",
        "adres": "ul. Przemysłowa 44, 40-001 Katowice",
        "nip": "6345556667",
    },
]


class Command(BaseCommand):
    help = "Konto demo i baza klientów. Katalog: python manage.py sync_google"

    def handle(self, *args, **options):
        User = get_user_model()
        user, _created = User.objects.get_or_create(
            username="handlowiec",
            defaults={"first_name": "Mateusz", "last_name": "Jaskulski", "is_staff": True},
        )
        user.set_password("oferta123")
        user.save()
        SalespersonProfile.objects.update_or_create(
            user=user,
            defaults={
                "telefon": "+48 600 000 001",
                "email": "mateusz.jaskulski@kjgastro.com.pl",
                "stanowisko": "Handlowiec",
                "kontakt": "KJ Gastro",
                "komunikat_otwarcia": "Dzień dobry,\nponiżej propozycja produktowa KJ Gastro dopasowana do Państwa potrzeb.",
                "komunikat_zamkniecia": "W razie pytań pozostaję do dyspozycji.\nPozdrawiam serdecznie.",
            },
        )
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={"first_name": "Adam", "is_staff": True, "is_superuser": True},
        )
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password("oferta123")
        admin.save()

        Client.objects.all().delete()
        clients = [Client.objects.create(**row) for row in CLIENTS]
        platnik = clients[0]
        odbiorca = clients[1]
        Product.objects.update_or_create(
            kod="TRANSPORT",
            defaults={
                "nazwa": "Koszt transportu",
                "combi": "TRANSPORT Koszt transportu",
                "cena_det": Decimal("20.00"),
                "cena_baz": Decimal("20.00"),
                "waluta": "PLN",
                "zdjecie": "",
            },
        )

        if not Offer.objects.filter(created_by=user).exists():
            offer = Offer.objects.create(
                created_by=user,
                nazwa="Wyposażenie kuchni — Q4",
                created_on=date.today(),
                platnik=platnik,
                platnik_nazwa=platnik.nazwa,
                platnik_adres=platnik.adres,
                platnik_nip=platnik.nip,
                odbiorca=odbiorca,
                odbiorca_nazwa=odbiorca.nazwa,
                odbiorca_adres=odbiorca.adres,
            )
            for i in range(1, 6):
                OfferLine.objects.create(offer=offer, position=i)
        else:
            offer = Offer.objects.filter(created_by=user).order_by("id").first()
            offer.platnik = platnik
            offer.platnik_nazwa = platnik.nazwa
            offer.platnik_adres = platnik.adres
            offer.platnik_nip = platnik.nip
            offer.odbiorca = odbiorca
            offer.odbiorca_nazwa = odbiorca.nazwa
            offer.odbiorca_adres = odbiorca.adres
            if not offer.nazwa or offer.nazwa in ("Propozycja", "Restauracja Demo"):
                offer.nazwa = "Wyposażenie kuchni — Q4"
            offer.save()

        self.stdout.write(self.style.SUCCESS("Konto: handlowiec / oferta123  ·  admin / oferta123"))
        self.stdout.write("Klienci: 4 rekordy. Katalog: python manage.py sync_google")
