from flask_sqlalchemy import SQLAlchemy
import uuid

db = SQLAlchemy()


class Friends(db.Model):
    __tablename__ = 'friends'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
        return f"<Friendship {self.user_id} -> {self.friend_id}, status={self.status}>"


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    friends = db.relationship(
        'User',
        secondary='friends',
        primaryjoin=(id == Friends.user_id),
        secondaryjoin=(id == Friends.friend_id),
        backref=db.backref('friend_of', lazy='dynamic'),
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<User {self.username}>'


class UserGroup(db.Model):
    __tablename__ = 'usergroups'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), primary_key=True)
    joined_at = db.Column(db.DateTime, default=db.func.now())


class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    expenses = db.relationship('Expense', back_populates='group', cascade="all, delete-orphan")

    members = db.relationship(
        'User',
        secondary='usergroups',
        primaryjoin="Group.id == UserGroup.group_id",
        secondaryjoin="User.id == UserGroup.user_id",
        backref='groups'
    )

    def __repr__(self):
        return f'<Group {self.name}>'


class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))
    description = db.Column(db.String(255))
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=db.func.now())
    category = db.Column(db.String(50), nullable=True)
    custom_split = db.Column(db.Boolean, default=False)

    shares = db.relationship('ExpenseShare', back_populates='expense', cascade="all, delete-orphan")
    group = db.relationship('Group', back_populates='expenses')


class ExpenseShare(db.Model):
    __tablename__ = 'expenseshares'

    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    share = db.Column(db.Numeric(10, 2), nullable=False)
    paid_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    expense = db.relationship('Expense', back_populates='shares')\



class Settlement(db.Model):
    __tablename__ = 'settlement'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    payer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.DateTime, default=db.func.now())
    currency = db.Column(db.String(10), nullable=False, default='PLN')

    payer = db.relationship('User', foreign_keys=[payer_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])
    group = db.relationship('Group', backref=db.backref('settlements', lazy=True))


class Currency(db.Model):
    __tablename__ = 'currencies'

    currency_code = db.Column(db.String(3), primary_key=True)
    exchange_rate = db.Column(db.Numeric(10, 6), nullable=False)
    last_updated = db.Column(db.DateTime, nullable=False, default=db.func.now())

    def __repr__(self):
        return f"<Currency {self.currency_code}: {self.exchange_rate} (updated {self.last_updated})>"


class FriendRequest(db.Model):
    __tablename__ = 'friendrequest'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)

    sender = db.relationship('User', foreign_keys=[sender_id])
    recipient = db.relationship('User', foreign_keys=[recipient_id])
