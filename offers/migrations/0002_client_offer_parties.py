import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("offers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Client",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nazwa", models.CharField(db_index=True, max_length=250)),
                ("adres", models.CharField(blank=True, max_length=400)),
                ("nip", models.CharField(blank=True, max_length=20)),
            ],
            options={"ordering": ["nazwa"]},
        ),
        migrations.RenameField(
            model_name="offer",
            old_name="klient",
            new_name="nazwa",
        ),
        migrations.AddField(
            model_name="offer",
            name="platnik",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="offers_platnik",
                to="offers.client",
            ),
        ),
        migrations.AddField(
            model_name="offer",
            name="platnik_nazwa",
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AddField(
            model_name="offer",
            name="platnik_adres",
            field=models.CharField(blank=True, max_length=400),
        ),
        migrations.AddField(
            model_name="offer",
            name="platnik_nip",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="offer",
            name="odbiorca",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="offers_odbiorca",
                to="offers.client",
            ),
        ),
        migrations.AddField(
            model_name="offer",
            name="odbiorca_nazwa",
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AddField(
            model_name="offer",
            name="odbiorca_adres",
            field=models.CharField(blank=True, max_length=400),
        ),
    ]
