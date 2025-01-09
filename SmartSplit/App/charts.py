from datetime import datetime
from models import Expense, ExpenseShare, db
from sqlalchemy import func


def get_group_charts_data(group):
    monthly_expenses_group = (
        db.session.query(
            func.to_char(Expense.created_at, 'YYYY-MM').label('month'),
            func.sum(Expense.amount).label('total')
        )
        .filter(
            Expense.group_id == group.id,
            Expense.currency == 'PLN'
        )
        .group_by(func.to_char(Expense.created_at, 'YYYY-MM'))
        .order_by(func.to_char(Expense.created_at, 'YYYY-MM'))
        .all()
    )

    monthly_data_group = {
        "labels": [row[0] for row in monthly_expenses_group],
        "values": [row[1] for row in monthly_expenses_group],
    }

    start_of_this_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    category_expenses_group = (
        db.session.query(
            Expense.category,
            func.sum(Expense.amount).label('total')
        )
        .filter(
            Expense.group_id == group.id,
            Expense.currency == 'PLN',
            Expense.created_at >= start_of_this_month,
        )
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )

    category_data_group = {
        "labels": [row[0] for row in category_expenses_group],
        "values": [row[1] for row in category_expenses_group],
    }

    return {
        "monthly": monthly_data_group,
        "categories": category_data_group,
    }


def get_user_charts_data(group, user_id):
    monthly_expenses = (
        db.session.query(
            func.to_char(Expense.created_at, 'YYYY-MM').label('month'),
            func.sum(ExpenseShare.share).label('total')
        )
        .join(Expense, Expense.id == ExpenseShare.expense_id)
        .filter(
            Expense.group_id == group.id,
            Expense.currency == 'PLN',
            ExpenseShare.user_id == user_id
        )
        .group_by(func.to_char(Expense.created_at, 'YYYY-MM'))
        .order_by(func.to_char(Expense.created_at, 'YYYY-MM'))
        .all()
    )

    monthly_data = {
        "labels": [row[0] for row in monthly_expenses],
        "values": [row[1] for row in monthly_expenses],
    }

    category_expenses = (
        db.session.query(
            Expense.category,
            func.sum(ExpenseShare.share).label('total')
        )
        .join(Expense, Expense.id == ExpenseShare.expense_id)
        .filter(
            Expense.group_id == group.id,
            Expense.currency == 'PLN',
            ExpenseShare.user_id == user_id,
            func.date_trunc('month', Expense.created_at) == func.date_trunc('month', func.now())
        )
        .group_by(Expense.category)
        .order_by(func.sum(ExpenseShare.share).desc())
        .all()
    )

    category_data = {
        "labels": [row[0] for row in category_expenses],
        "values": [row[1] for row in category_expenses],
    }

    return {
        "monthly": monthly_data,
        "categories": category_data,
    }
