from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


def seed_fx(apps, schema_editor):
    FxRate = apps.get_model("offers", "FxRate")
    defaults = [
        ("EUR", Decimal("4.3000"), "Euro"),
        ("USD", Decimal("3.9000"), "Dolar amerykański"),
        ("GBP", Decimal("5.1000"), "Funt szterling"),
        ("CZK", Decimal("0.1700"), "Korona czeska"),
        ("CNY", Decimal("0.5500"), "Juan"),
        ("SEK", Decimal("0.3800"), "Korona szwedzka"),
    ]
    for code, rate, name in defaults:
        FxRate.objects.update_or_create(
            waluta=code, defaults={"kurs_pln": rate, "nazwa": name}
        )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency("auth.user"),
        ("offers", "0003_margin_transport"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="waluta",
            field=models.CharField(db_index=True, default="PLN", max_length=8),
        ),
        migrations.CreateModel(
            name="SalespersonProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("telefon", models.CharField(blank=True, max_length=40)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("stanowisko", models.CharField(blank=True, max_length=120)),
                ("kontakt", models.CharField(blank=True, max_length=400)),
                ("komunikat_otwarcia", models.TextField(blank=True)),
                ("komunikat_zamkniecia", models.TextField(blank=True)),
                ("zdjecie", models.ImageField(blank=True, upload_to="handlowcy/")),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to="auth.user",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="FxRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("waluta", models.CharField(max_length=8, unique=True)),
                ("kurs_pln", models.DecimalField(decimal_places=4, max_digits=12)),
                ("nazwa", models.CharField(blank=True, max_length=80)),
            ],
            options={"ordering": ["waluta"]},
        ),
        migrations.RunPython(seed_fx, migrations.RunPython.noop),
    ]
