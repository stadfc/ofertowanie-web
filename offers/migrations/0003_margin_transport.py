from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("offers", "0002_client_offer_parties"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="cena_baz",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=12),
        ),
        migrations.AddField(
            model_name="offer",
            name="koszt_transportu",
            field=models.DecimalField(decimal_places=2, default=Decimal("20.00"), max_digits=12),
        ),
    ]
