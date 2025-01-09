import requests
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from models import Currency, db
import os
from dotenv import load_dotenv

load_dotenv()

FIXER_API_URL = "http://data.fixer.io/api/latest"
FIXER_API_KEY = os.getenv('FIXER_API_KEY')


def update_currency_rates():
    """
    Pobiera najnowsze kursy walut z API Fixer.io względem EUR i aktualizuje je w bazie danych jako kursy względem PLN.
    """
    try:
        response = requests.get(FIXER_API_URL, params={"access_key": FIXER_API_KEY, "base": "EUR"})
        data = response.json()

        if not data.get("success", False):
            print(f"Failed to fetch currency data: {data.get('error', 'Unknown error')}")
            return

        rates = data.get("rates", {})
        now = datetime.utcnow()

        eur_to_pln = rates.get('PLN')

        if not eur_to_pln:
            print("Error: EUR/PLN rate not found in the API response.")
            return

        for currency_code, rate in rates.items():

            rate_in_pln = Decimal(eur_to_pln) / Decimal(rate)

            currency = Currency.query.filter_by(currency_code=currency_code).first()
            if currency:
                currency.exchange_rate = rate_in_pln
                currency.last_updated = now
            else:
                db.session.add(Currency(
                    currency_code=currency_code,
                    exchange_rate=rate_in_pln,
                    last_updated=now
                ))

        db.session.commit()
        print("Currency rates updated successfully.")
    except Exception as e:
        print(f"Error while updating currency rates: {e}")


def get_exchange_rate(currency_code):
    """
    Pobiera kurs wymiany dla danej waluty. Jeśli kurs jest starszy niż 8 godzin, aktualizuje kursy.
    """
    currency = Currency.query.filter_by(currency_code=currency_code).first()
    now = datetime.utcnow()

    if not currency or (now - currency.last_updated > timedelta(hours=8)):
        update_currency_rates()
        currency = Currency.query.filter_by(currency_code=currency_code).first()

    if not currency:
        raise ValueError(f"Currency {currency_code} not found in the database.")

    return currency.exchange_rate


def convert_to_pln(amount, currency_code):
    """
    Przelicza podaną kwotę na PLN na podstawie kursu wymiany.
    """
    if currency_code == "PLN":
        return amount

    exchange_rate = get_exchange_rate(currency_code)

    amount_in_pln = Decimal(amount) * exchange_rate
    return amount_in_pln.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
