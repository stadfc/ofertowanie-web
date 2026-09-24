import json
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client as HttpClient, TestCase
from django.urls import reverse

from .models import Offer, OfferLine, Product


class OfferPasteTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("handlowiec", password="test-pass")
        self.client = HttpClient()
        self.client.login(username="handlowiec", password="test-pass")
        self.p1 = Product.objects.create(
            kod="ABC-1",
            nazwa="Produkt jeden",
            combi="ABC-1 Produkt jeden",
            cena_det=Decimal("100.00"),
            cena_baz=Decimal("50.00"),
        )
        self.p2 = Product.objects.create(
            kod="XYZ-2",
            nazwa="Produkt dwa",
            combi="XYZ-2 Produkt dwa",
            cena_det=Decimal("40.00"),
            cena_baz=Decimal("20.00"),
        )
        self.offer = Offer.objects.create(
            created_by=self.user,
            created_on=date.today(),
            nazwa="Test",
        )
        for i in range(1, 4):
            OfferLine.objects.create(offer=self.offer, position=i)

    def _paste(self, text, **opts):
        payload = {
            "text": text,
            "has_header": opts.get("has_header", False),
            "format": opts.get("format", "kod_ilosc"),
        }
        return self.client.post(
            reverse("offer_paste", args=[self.offer.pk]),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_paste_kod_ilosc_smooth(self):
        text = "ABC-1\t2\nXYZ-2\t3"
        res = self._paste(text)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["smooth"])
        self.assertEqual(data["accepted_count"], 2)
        self.assertEqual(data["dropped_count"], 0)
        lines = list(self.offer.lines.order_by("position"))
        filled = [l for l in lines if l.combi]
        self.assertEqual(len(filled), 2)
        self.assertEqual(filled[0].combi, self.p1.combi)
        self.assertEqual(filled[0].ilosc, Decimal("2.00"))
        self.assertEqual(filled[1].combi, self.p2.combi)
        self.assertEqual(filled[1].ilosc, Decimal("3.00"))

    def test_paste_skips_unknown_and_continues(self):
        text = "ABC-1\t1\nMISSING\t5\nXYZ-2\t2"
        res = self._paste(text)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertFalse(data["smooth"])
        self.assertEqual(data["accepted_count"], 2)
        self.assertEqual(data["dropped_count"], 1)
        self.assertEqual(data["dropped"][0]["kod"], "MISSING")
        filled = [l for l in self.offer.lines.order_by("position") if l.combi]
        self.assertEqual([l.combi for l in filled], [self.p1.combi, self.p2.combi])

    def test_paste_with_header_and_price(self):
        text = "kod\tilosc\tcena\nABC-1\t4\t80"
        res = self._paste(text, has_header=True, format="kod_ilosc_cena")
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["smooth"])
        line = self.offer.lines.filter(combi=self.p1.combi).first()
        self.assertIsNotNone(line)
        self.assertEqual(line.ilosc, Decimal("4.00"))
        # cena 80 vs katalog 100 → rabat 20%
        self.assertEqual(line.rabat, Decimal("0.2000"))

    def test_paste_kod_cena_ilosc(self):
        text = "XYZ-2\t30\t7"
        res = self._paste(text, format="kod_cena_ilosc")
        data = res.json()
        self.assertTrue(data["ok"])
        line = self.offer.lines.filter(combi=self.p2.combi).first()
        self.assertEqual(line.ilosc, Decimal("7.00"))
        # cena 30 vs 40 → rabat 25%
        self.assertEqual(line.rabat, Decimal("0.2500"))
