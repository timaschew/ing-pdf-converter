# ing-pdf-converter
A python script to convert ING bank accounut statements from PDF to CSV and JSON

Can be used for [firefly-iii-fints-importer](https://github.com/bnw/firefly-iii-fints-importer)

## Motivation

CSV files from ING online portal doesn't contain "Referenz".
Sometimes statements (rows in CSV) have no "Verwendungszweck" which makes it impossible to process CSV files automatically.

## Status
Tested for german ING bank girp accounuts.

Supported transaction types:

- Gutschrift
- Ueberweisung
- Lastschrift
- Bezuege
- Gehalt/Rente
- Dauerauftrag/Terminueberw.
- Entgelt
- Retoure
- Abbuchung

## Output structure 

CSV headers

- Buchung
- Valuta
- Auftraggeber/Empfänger
- Buchungstext
- Verwendungszweck
- Referenz
- Mandat
- Saldo
- Währung
- Betrag
- Währung

JSON structure:

```json
{
    "meta": {
        "datum": "31.12.2020",
        "saldo_alt": "0,00",
        "saldo_neu": "500,00"
    },
    "transactions": [
        {
            "buchung": "21.12.2020",
            "typ": "Gutschrift",
            "betrag": "500,00",
            "konto": "MAX MUSTERMANN",
            "zweck": [
                "Umbuchung"
            ],
            "valuta": "20.12.2020",
            "referenz": "ZV0000123456789110000000"
        }
    ]
}
```

## Setup

- install [python](https://www.python.org/downloads/) (with pip)
- run `pip install PyPDF2` (I recommend using [virtualenv](https://virtualenv.pypa.io/))
- run `python diba-pdf.py folder-with-pdf-documents`
