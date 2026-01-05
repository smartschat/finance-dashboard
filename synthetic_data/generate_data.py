#!/usr/bin/env python3
"""Generate synthetic DKB bank export data for testing."""

import random
from datetime import datetime, timedelta
from pathlib import Path

# Seed for reproducibility
random.seed(42)

# Date range: 2023-01-01 to 2025-12-31
START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2025, 12, 31)


# German number format
def format_german_number(amount):
    """Format number as German currency (1.234,56 €)."""
    sign = "-" if amount < 0 else ""
    abs_amount = abs(amount)
    int_part = int(abs_amount)
    dec_part = int(round((abs_amount - int_part) * 100))
    int_str = f"{int_part:,}".replace(",", ".")
    return f"{sign}{int_str},{dec_part:02d} €"


def format_german_date(dt):
    """Format date as DD.MM.YYYY."""
    return dt.strftime("%d.%m.%Y")


def random_date_in_month(year, month):
    """Get a random date in a given month."""
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    start = datetime(year, month, 1)
    delta = (next_month - start).days
    return start + timedelta(days=random.randint(0, delta - 1))


# Transaction templates
SALARY = {
    "empfaenger": "ARBEITGEBER GMBH",
    "zweck": "GEHALT {month}/{year}",
    "typ": "Eingang",
    "amount_range": (3500, 4500),
}

RENT = {
    "empfaenger": "Hausverwaltung Müller",
    "zweck": "Miete {month}/{year} Whg. 3.OG",
    "typ": "Dauerauftrag",
    "iban": "DE89370400440532013000",
    "amount_range": (-1200, -1200),
}

UTILITIES = [
    {"empfaenger": "Stadtwerke Berlin", "zweck": "Strom Abschlag", "amount": -85},
    {"empfaenger": "GASAG", "zweck": "Gas Abschlag", "amount": -65},
    {"empfaenger": "Berliner Wasserbetriebe", "zweck": "Wasser/Abwasser", "amount": -45},
]

INSURANCE = [
    {"empfaenger": "Allianz Versicherung", "zweck": "Haftpflicht", "amount": -15, "freq": 1},
    {"empfaenger": "TK Krankenkasse", "zweck": "Zusatzversicherung", "amount": -25, "freq": 1},
    {"empfaenger": "HUK Coburg", "zweck": "KFZ Versicherung", "amount": -45, "freq": 1},
]

SUBSCRIPTIONS_GIRO = [
    {"empfaenger": "Spotify AB", "zweck": "Premium Family", "amount": -17.99},
    {"empfaenger": "Netflix Intl", "zweck": "Streaming Abo", "amount": -15.99},
    {"empfaenger": "Fitnessstudio McFit", "zweck": "Mitgliedsbeitrag", "amount": -24.99},
    {"empfaenger": "Deutsche Bahn", "zweck": "BahnCard 50", "amount": -25.90, "freq": 12},
]

GROCERIES_STORES = [
    "REWE",
    "EDEKA",
    "LIDL",
    "ALDI",
    "Kaufland",
    "Penny",
    "Netto",
    "dm Drogerie",
    "Rossmann",
    "Bio Company",
]

RESTAURANTS = [
    "Restaurant Olive",
    "Pizza Napoli",
    "Sushi Garden",
    "Cafe Einstein",
    "Burger King",
    "McDonalds",
    "Vapiano",
    "Block House",
    "L'Osteria",
]

TRANSPORT = [
    {"empfaenger": "BVG", "zweck": "Monatskarte AB", "amount": -86},
]

SHOPPING_STORES = ["Amazon EU", "Zalando", "MediaMarkt", "Saturn", "IKEA", "H&M", "Decathlon"]

INVESTMENTS = [
    {"empfaenger": "Trade Republic", "zweck": "Sparplan ETF", "amount": -500},
    {"empfaenger": "Scalable Capital", "zweck": "Depot Einzahlung", "amount": -200},
]

# Visa transactions
VISA_SUBSCRIPTIONS = [
    {"desc": "OPENAI *CHATGPT SUBSCR", "amount": -20.00},
    {"desc": "GITHUB, INC.", "amount": -4.00},
    {"desc": "APPLE.COM/BILL", "amount": -2.99},
    {"desc": "GOOGLE *CLOUD", "amount": -10.50},
    {"desc": "AMAZON PRIME*", "amount": -8.99},
    {"desc": "DISNEY PLUS", "amount": -8.99},
]

VISA_SHOPPING = [
    "AMAZON.DE",
    "PAYPAL *EBAY",
    "BOOKING.COM",
    "AIRBNB",
    "UBER *TRIP",
    "LIEFERANDO",
    "GORILLAS",
    "FLINK SE",
]

VISA_TRAVEL = [
    "LUFTHANSA",
    "RYANAIR",
    "HOTEL MARRIOTT",
    "SIXT RENT A CAR",
    "SHELL TANKSTELLE",
    "ARAL TANKSTELLE",
    "OMV TANKSTELLE",
]


def generate_girokonto_transactions():
    """Generate Girokonto (checking account) transactions."""
    transactions = []

    current = START_DATE
    while current <= END_DATE:
        year = current.year
        month = current.month

        # Monthly salary (around 25th of previous month or 1st)
        salary_date = random_date_in_month(year, month)
        salary_date = salary_date.replace(day=min(28, random.randint(25, 28)))
        amount = random.uniform(*SALARY["amount_range"])
        transactions.append(
            {
                "date": salary_date,
                "empfaenger": SALARY["empfaenger"],
                "zweck": SALARY["zweck"].format(month=month, year=year),
                "typ": SALARY["typ"],
                "iban": "DE12500105170648489890",
                "amount": amount,
            }
        )

        # Rent (1st-5th of month)
        rent_date = random_date_in_month(year, month).replace(day=random.randint(1, 5))
        transactions.append(
            {
                "date": rent_date,
                "empfaenger": RENT["empfaenger"],
                "zweck": RENT["zweck"].format(month=month, year=year),
                "typ": RENT["typ"],
                "iban": RENT["iban"],
                "amount": RENT["amount_range"][0],
            }
        )

        # Utilities
        for util in UTILITIES:
            util_date = random_date_in_month(year, month).replace(day=random.randint(10, 20))
            transactions.append(
                {
                    "date": util_date,
                    "empfaenger": util["empfaenger"],
                    "zweck": util["zweck"],
                    "typ": "Lastschrift",
                    "iban": f"DE{random.randint(10, 99)}{''.join(str(random.randint(0, 9)) for _ in range(18))}",
                    "amount": util["amount"] + random.uniform(-10, 10),
                }
            )

        # Insurance (monthly)
        for ins in INSURANCE:
            if ins.get("freq", 1) == 1 or month % ins.get("freq", 1) == 0:
                ins_date = random_date_in_month(year, month).replace(day=random.randint(1, 10))
                transactions.append(
                    {
                        "date": ins_date,
                        "empfaenger": ins["empfaenger"],
                        "zweck": ins["zweck"],
                        "typ": "Lastschrift",
                        "iban": f"DE{random.randint(10, 99)}{''.join(str(random.randint(0, 9)) for _ in range(18))}",
                        "amount": ins["amount"],
                    }
                )

        # Subscriptions
        for sub in SUBSCRIPTIONS_GIRO:
            freq = sub.get("freq", 1)
            if freq == 1 or month % freq == 0:
                sub_date = random_date_in_month(year, month).replace(day=random.randint(1, 28))
                transactions.append(
                    {
                        "date": sub_date,
                        "empfaenger": sub["empfaenger"],
                        "zweck": sub["zweck"],
                        "typ": "Lastschrift",
                        "iban": "",
                        "amount": sub["amount"],
                    }
                )

        # Transport
        for tr in TRANSPORT:
            tr_date = random_date_in_month(year, month).replace(day=random.randint(1, 5))
            transactions.append(
                {
                    "date": tr_date,
                    "empfaenger": tr["empfaenger"],
                    "zweck": tr["zweck"],
                    "typ": "Lastschrift",
                    "iban": "",
                    "amount": tr["amount"],
                }
            )

        # Groceries (4-8 times per month)
        for _ in range(random.randint(4, 8)):
            store = random.choice(GROCERIES_STORES)
            groc_date = random_date_in_month(year, month)
            amount = -random.uniform(15, 120)
            transactions.append(
                {
                    "date": groc_date,
                    "empfaenger": store,
                    "zweck": f"EC {store} //Berlin",
                    "typ": "Kartenzahlung",
                    "iban": "",
                    "amount": amount,
                }
            )

        # Restaurants (2-5 times per month)
        for _ in range(random.randint(2, 5)):
            rest = random.choice(RESTAURANTS)
            rest_date = random_date_in_month(year, month)
            amount = -random.uniform(15, 80)
            transactions.append(
                {
                    "date": rest_date,
                    "empfaenger": rest,
                    "zweck": f"EC {rest} //Berlin",
                    "typ": "Kartenzahlung",
                    "iban": "",
                    "amount": amount,
                }
            )

        # Shopping (1-3 times per month)
        for _ in range(random.randint(1, 3)):
            shop = random.choice(SHOPPING_STORES)
            shop_date = random_date_in_month(year, month)
            amount = -random.uniform(20, 200)
            transactions.append(
                {
                    "date": shop_date,
                    "empfaenger": shop,
                    "zweck": f"SEPA {shop}",
                    "typ": "Lastschrift",
                    "iban": "",
                    "amount": amount,
                }
            )

        # Investments
        for inv in INVESTMENTS:
            inv_date = random_date_in_month(year, month).replace(day=random.randint(1, 5))
            transactions.append(
                {
                    "date": inv_date,
                    "empfaenger": inv["empfaenger"],
                    "zweck": inv["zweck"],
                    "typ": "Überweisung",
                    "iban": f"DE{random.randint(10, 99)}{''.join(str(random.randint(0, 9)) for _ in range(18))}",
                    "amount": inv["amount"],
                }
            )

        # ATM withdrawals (1-2 per month)
        for _ in range(random.randint(1, 2)):
            atm_date = random_date_in_month(year, month)
            amount = -random.choice([50, 100, 150, 200])
            transactions.append(
                {
                    "date": atm_date,
                    "empfaenger": "Geldautomat",
                    "zweck": "Bargeldauszahlung",
                    "typ": "Auszahlung",
                    "iban": "",
                    "amount": amount,
                }
            )

        # Credit card settlement (from Visa)
        cc_date = random_date_in_month(year, month).replace(day=random.randint(5, 10))
        transactions.append(
            {
                "date": cc_date,
                "empfaenger": "DKB VISA Kartenabrechnung",
                "zweck": f"Kartenabrechnung {month:02d}/{year}",
                "typ": "Lastschrift",
                "iban": "",
                "amount": -random.uniform(200, 600),
            }
        )

        # Occasional transfers to savings
        if random.random() > 0.5:
            save_date = random_date_in_month(year, month)
            transactions.append(
                {
                    "date": save_date,
                    "empfaenger": "Eigenes Sparkonto",
                    "zweck": "Umbuchung Sparkonto",
                    "typ": "Überweisung",
                    "iban": "DE45120300001234567890",
                    "amount": -random.choice([100, 200, 300, 500]),
                }
            )

        # Move to next month
        if month == 12:
            current = datetime(year + 1, 1, 1)
        else:
            current = datetime(year, month + 1, 1)

    return transactions


def generate_visa_transactions():
    """Generate Visa credit card transactions."""
    transactions = []

    current = START_DATE
    while current <= END_DATE:
        year = current.year
        month = current.month

        # Monthly subscriptions
        for sub in VISA_SUBSCRIPTIONS:
            sub_date = random_date_in_month(year, month).replace(day=random.randint(1, 28))
            transactions.append(
                {
                    "date": sub_date,
                    "desc": sub["desc"],
                    "typ": "Lastschrift",
                    "amount": sub["amount"],
                    "currency": "",
                }
            )

        # Online shopping (3-6 times per month)
        for _ in range(random.randint(3, 6)):
            shop = random.choice(VISA_SHOPPING)
            shop_date = random_date_in_month(year, month)
            amount = -random.uniform(10, 150)
            transactions.append(
                {
                    "date": shop_date,
                    "desc": f"{shop} {random.randint(1000, 9999)}",
                    "typ": "Zahlung",
                    "amount": amount,
                    "currency": "",
                }
            )

        # Travel/Gas (1-3 times per month)
        for _ in range(random.randint(1, 3)):
            travel = random.choice(VISA_TRAVEL)
            travel_date = random_date_in_month(year, month)
            amount = -random.uniform(30, 200)
            transactions.append(
                {
                    "date": travel_date,
                    "desc": f"{travel}",
                    "typ": "Zahlung",
                    "amount": amount,
                    "currency": "",
                }
            )

        # Occasional foreign currency transactions
        if random.random() > 0.7:
            fx_date = random_date_in_month(year, month)
            amount = -random.uniform(20, 100)
            transactions.append(
                {
                    "date": fx_date,
                    "desc": "PAYMENT INTL STORE",
                    "typ": "Zahlung",
                    "amount": amount,
                    "currency": f"{abs(amount) * 1.1:.2f} USD",
                }
            )

        # Move to next month
        if month == 12:
            current = datetime(year + 1, 1, 1)
        else:
            current = datetime(year, month + 1, 1)

    return transactions


def write_girokonto_csv(transactions, filepath):
    """Write Girokonto transactions to CSV."""
    # DKB header format (4 lines of metadata, then data)
    header_lines = [
        '"Kontoauszug";"DE12345678901234567890"',
        '"Kontostand";"10.234,56 EUR"',
        "",
        "",
    ]

    columns = "Buchungsdatum;Wertstellung;Status;Zahlungspflichtiger;Zahlungsempfaenger;Verwendungszweck;Umsatztyp;IBAN;Betrag;Glaeubiger-ID;Mandatsreferenz;Kundenreferenz"

    # Sort by date descending (newest first)
    transactions = sorted(transactions, key=lambda x: x["date"], reverse=True)

    with open(filepath, "w", encoding="utf-8-sig") as f:
        for line in header_lines:
            f.write(line + "\n")
        f.write(columns + "\n")

        for tx in transactions:
            date_str = format_german_date(tx["date"])
            amount_str = format_german_number(tx["amount"])
            row = [
                date_str,  # Buchungsdatum
                date_str,  # Wertstellung
                "Gebucht",  # Status
                "",  # Zahlungspflichtiger
                tx["empfaenger"],  # Zahlungsempfaenger
                tx["zweck"],  # Verwendungszweck
                tx["typ"],  # Umsatztyp
                tx.get("iban", ""),  # IBAN
                amount_str,  # Betrag
                "",  # Glaeubiger-ID
                "",  # Mandatsreferenz
                "",  # Kundenreferenz
            ]
            f.write(";".join(f'"{x}"' if ";" in str(x) else str(x) for x in row) + "\n")


def write_visa_csv(transactions, filepath):
    """Write Visa transactions to CSV."""
    # DKB Visa header format
    header_lines = [
        '"Kreditkarte";"1234********5678"',
        '"Kreditrahmen";"5.000,00 EUR"',
        "",
        "",
    ]

    columns = "Belegdatum;Wertstellung;Status;Beschreibung;Umsatztyp;Betrag;Fremdwährungsbetrag"

    # Sort by date descending (newest first)
    transactions = sorted(transactions, key=lambda x: x["date"], reverse=True)

    with open(filepath, "w", encoding="utf-8-sig") as f:
        for line in header_lines:
            f.write(line + "\n")
        f.write(columns + "\n")

        for tx in transactions:
            date_str = format_german_date(tx["date"])
            amount_str = format_german_number(tx["amount"])
            row = [
                date_str,  # Belegdatum
                date_str,  # Wertstellung
                "Gebucht",  # Status
                tx["desc"],  # Beschreibung
                tx["typ"],  # Umsatztyp
                amount_str,  # Betrag
                tx.get("currency", ""),  # Fremdwährungsbetrag
            ]
            f.write(";".join(f'"{x}"' if ";" in str(x) else str(x) for x in row) + "\n")


def main():
    """Generate all synthetic data files."""
    output_dir = Path(__file__).parent

    print("Generating Girokonto transactions...")
    giro_tx = generate_girokonto_transactions()
    giro_path = output_dir / "1234567890_Girokonto_DE12345678901234567890.csv"
    write_girokonto_csv(giro_tx, giro_path)
    print(f"  Written {len(giro_tx)} transactions to {giro_path.name}")

    print("Generating Visa transactions...")
    visa_tx = generate_visa_transactions()
    visa_path = output_dir / "1234567890_Visa_1234.csv"
    write_visa_csv(visa_tx, visa_path)
    print(f"  Written {len(visa_tx)} transactions to {visa_path.name}")

    print("\nDone! Files created in:", output_dir)


if __name__ == "__main__":
    main()
