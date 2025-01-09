from models import Settlement
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict


def calculate_balance(group):
    members = {member.id: member for member in group.members}
    balance_sheet = defaultdict(lambda: defaultdict(lambda: defaultdict(Decimal)))

    # Przetwarzanie wydatków
    for expense in group.expenses:
        payer_share = next((share for share in expense.shares if share.paid_by == share.user_id), None)
        if not payer_share:
            continue

        payer_user_id = int(payer_share.user_id)
        currency = expense.currency

        if payer_user_id not in members:
            print(f"Użytkownik o id {payer_user_id} nie istnieje w grupie")
            continue

        for share in expense.shares:
            member_user_id = int(share.user_id)
            member_share_amount = Decimal(share.share).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            if member_user_id not in members:
                print(f"Użytkownik o id {member_user_id} nie istnieje w grupie")
                continue

            if member_user_id != payer_user_id:
                balance_sheet[member_user_id][payer_user_id][currency] += member_share_amount
                balance_sheet[payer_user_id][member_user_id][currency] -= member_share_amount

    # Przetwarzanie rozliczeń
    for settlement in Settlement.query.filter_by(group_id=group.id).all():
        payer_id = settlement.payer_id
        receiver_id = settlement.receiver_id
        settlement_amount = Decimal(settlement.amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        currency = settlement.currency

        balance_sheet[payer_id][receiver_id][currency] -= settlement_amount
        balance_sheet[receiver_id][payer_id][currency] += settlement_amount

    # Zaokrąglanie końcowych wyników
    for user_id, balances in balance_sheet.items():
        for other_user_id, currencies in balances.items():
            for currency, amount in currencies.items():
                balance_sheet[user_id][other_user_id][currency] = amount.quantize(Decimal('0.01'),
                                                                                  rounding=ROUND_HALF_UP)

    return balance_sheet


