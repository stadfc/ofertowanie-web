# Ofertowanie web — prototyp

Arkusz oferty w przeglądarce, zbliżony do Excela (Oferta V3).

## Uruchomienie

```
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed
python manage.py sync_google
python manage.py runserver
```

Otwórz http://127.0.0.1:8000/

- login: `handlowiec`
- hasło: `oferta123`

## Jak pracować (jak w Excelu)

- **Nazwa oferty**, **Płatnik** (nazwa, adres, NIP), **Odbiorca** (nazwa, adres) z bazy klientów
- dwuklik w **Opis** — wyszukiwarka produktu
- **Rabat** (np. `0.1` = 10%) i **Ilość**
- **Oferta ze zdjęciami** (zdjęcia z kjgastro.com.pl po sync Google)
- **Pokaż kody**, **Dodaj wiersze**, **Wyczyść tabelę**
- **PDF** / **EXCEL**
- **Archiwum** — lista po nazwie oferty i odbiorcy

```
python manage.py sync_google
```

pobiera z opublikowanego arkusza Google **BAZA** do 250 produktów **ze zdjęciem** (`https://www.kjgastro.com.pl/pictures/…`).

Archiwum: nazwa oferty + odbiorca + płatnik. Płatnik: nazwa, adres, NIP. Odbiorca: nazwa i adres.

Ten katalog jest osobny od pliku XLSM z makrami. Dalszy rozwój aplikacji — nowy czat w tym folderze.
