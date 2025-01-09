from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from models import db, User, Group, UserGroup, Expense, ExpenseShare, Settlement, Friends, FriendRequest
from werkzeug.security import generate_password_hash, check_password_hash
from calculate_balance import calculate_balance
from decimal import Decimal, ROUND_HALF_UP
from charts import get_user_charts_data, get_group_charts_data
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError


app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)

load_dotenv()

sender_email = os.getenv('SENDER_EMAIL')
password = os.getenv('PASSWORD')

if not sender_email or not password:
    raise ValueError("Email or password is not set in .env file")


# Endpoint rejestracji
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash('This email address is already taken', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('This username is already taken!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        new_user = User(username=username, email=email, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration completed successfully! You can log in now.', 'success')
            return redirect(url_for('login'))
        except:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')


# Endpoint logowania
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id  # Zapisz użytkownika w sesji
            return redirect(url_for('user_dashboard'))  # Przekieruj na stronę użytkownika
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


# Endpoint głównej strony użytkownika po zalogowaniu
@app.route('/dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])  # Pobranie danych użytkownika

    return render_template('dashboard.html', user=user)


# Endpoint dodawania znajomego z wysyłaniem maila
@app.route('/add_friend', methods=['GET', 'POST'])
def add_friend():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        friend_email = request.form.get('friend_email')
        friend = User.query.filter_by(email=friend_email).first()

        # Sprawdzanie, czy użytkownik o podanym e-mailu istnieje
        if not friend:
            flash('User not found.', 'error')
            return redirect(url_for('add_friend'))

        # Sprawdzanie, czy użytkownik nie próbuje dodać samego siebie
        if friend.id == user.id:
            flash('You cannot add yourself as a friend.', 'error')
            return redirect(url_for('add_friend'))

        # Sprawdzenie istniejącej relacji w tabeli `friends`
        existing_friendship = db.session.query(Friends).filter(
            ((Friends.user_id == user.id) & (Friends.friend_id == friend.id)) |
            ((Friends.user_id == friend.id) & (Friends.friend_id == user.id))
        ).first()

        if existing_friendship:
            flash('You are already friends with this user.', 'info')
            return redirect(url_for('add_friend'))

        # Sprawdzenie, czy zaproszenie nie zostało już wysłane
        existing_request = FriendRequest.query.filter_by(sender_id=user.id, recipient_id=friend.id,
                                                         status='pending').first()
        if existing_request:
            flash('Friend request already sent.', 'error')
            return redirect(url_for('add_friend'))

        # Tworzenie nowego zaproszenia w bazie danych
        friend_request = FriendRequest(sender_id=user.id, recipient_id=friend.id)
        db.session.add(friend_request)

        try:
            db.session.commit()

            # Generowanie wiadomości e-mail
            subject = "Friend Request Confirmation"
            confirmation_url = url_for('confirm_friend_request', token=friend_request.token, _external=True)
            body = (
                f"Hi {friend.username},\n\n"
                f"{user.username} wants to be your friend!\n"
                f"Click the link below to confirm the friendship:\n\n"
                f"{confirmation_url}\n\n"
                "If you did not expect this email, please ignore it.\n\n"
                "Best regards,\nSmart Split"
            )

            # Tworzenie wiadomości e-mail
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = friend.email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            # Wysyłanie wiadomości e-mail
            try:
                # Połączenie z serwerem SMTP WP.PL
                with smtplib.SMTP_SSL("smtp.wp.pl", 465) as server:
                    server.login(sender_email, password)
                    server.sendmail(sender_email, friend.email, msg.as_string())
                    print(f"Email sent to {friend.email} from {sender_email}")

                flash('Friend request sent successfully!', 'success')
            except Exception as e:
                print(f"Error sending email: {e}")
                flash('Failed to send friend request email.', 'error')

        except IntegrityError:
            db.session.rollback()
            flash('Error while adding friend request. Please try again later.', 'error')

        return redirect(url_for('add_friend'))

    return render_template('add_friend.html')


@app.route('/confirm_friend_request/<token>', methods=['GET'])
def confirm_friend_request(token):
    friend_request = FriendRequest.query.filter_by(token=token, status='pending').first()

    if not friend_request:
        flash('Invalid or expired friend request.', 'error')
        return redirect(url_for('user_dashboard'))

    # Dodawanie znajomości między użytkownikami
    sender = User.query.get(friend_request.sender_id)
    recipient = User.query.get(friend_request.recipient_id)

    sender.friends.append(recipient)
    recipient.friends.append(sender)

    # Aktualizacja statusu zaproszenia
    friend_request.status = 'accepted'
    db.session.commit()

    flash('Friend request confirmed successfully!', 'success')
    return redirect(url_for('user_dashboard'))


@app.route('/remove_friend/<int:friend_id>', methods=['POST'])
def remove_friend(friend_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Usuń wszystkie rekordy reprezentujące tę znajomość
    friendships = Friends.query.filter(
        ((Friends.user_id == user_id) & (Friends.friend_id == friend_id)) |
        ((Friends.user_id == friend_id) & (Friends.friend_id == user_id))
    ).all()

    if friendships:
        for friendship in friendships:
            db.session.delete(friendship)
        db.session.commit()
        flash('Friend removed successfully.', 'success')
    else:
        flash('No friendship found to remove.', 'error')

    return redirect(url_for('view_friends'))


# Endpoint wyświetlania znajomych
@app.route('/friends')
def view_friends():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    friends = user.friends

    return render_template('friends.html', user=user, friends=friends)


# Endpoint tworzenia grupy
@app.route('/create_group', methods=['GET', 'POST'])
def create_group():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        group_name = request.form.get('group_name')
        selected_friends = request.form.getlist('friends')

        # Sprawdzenie, czy grupa ma nazwę
        if not group_name:
            flash('Group name is required!', 'error')
            return redirect(url_for('create_group'))

        # Utworzenie nowej grupy
        new_group = Group(name=group_name, created_by=user.id)
        db.session.add(new_group)

        try:
            db.session.commit()
            print(f"New group created with ID {new_group.id}")

            # Dodanie właściciela grupy
            user_group_owner = UserGroup(user_id=user.id, group_id=new_group.id)
            db.session.add(user_group_owner)

            # Dodanie znajomych do grupy
            for friend_id in selected_friends:
                # Sprawdzanie, czy znajomy istnieje
                friend = User.query.get(friend_id)
                if friend:
                    user_group = UserGroup(user_id=friend.id, group_id=new_group.id)
                    db.session.add(user_group)
                    print(f"Adding friend with ID {friend.id} to group with ID {new_group.id}")
                else:
                    print(f"Friend with ID {friend_id} not found. Skipping.")

            db.session.commit()  # Zatwierdzenie wszystkich zmian
            return redirect(url_for('user_dashboard'))
        except Exception as e:
            db.session.rollback()  # Wycofanie zmian w przypadku błędu
            print(f"An error occurred: {e}")
            flash('An error occurred while creating the group. Please try again.', 'error')
            return redirect(url_for('create_group'))

    friends = user.friends
    return render_template('create_group.html', user=user, friends=friends)


# Endpoint wyświetlania grup
@app.route('/groups')
def view_groups():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    groups = db.session.query(Group).join(UserGroup).filter(UserGroup.user_id == user.id).all()

    return render_template('groups.html', user=user, groups=groups)


# Endpoint wyświetlania szczegółów grupy i jej członków
@app.route('/group/<int:group_id>')
def view_group(group_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    group = Group.query.get_or_404(group_id)
    user = User.query.get(session['user_id'])

    # Sprawdzamy, czy użytkownik jest członkiem grupy
    if user not in group.members:
        flash('You are not a member of this group!', 'error')
        return redirect(url_for('view_groups'))

    members = {member.id: member for member in group.members}

    print("Members in group:", members)

    expenses = []
    balance_sheet = {}

    for expense in group.expenses:
        payer_shares = ExpenseShare.query.filter_by(expense_id=expense.id).all()

        paid_by_users = set()
        for payer_share in payer_shares:
            payer_user = User.query.get(payer_share.paid_by)
            if payer_user:
                paid_by_users.add(payer_user.username)

        if not paid_by_users:
            paid_by_users.add("Unknown")

        expenses.append({
            'id': expense.id,
            'description': expense.description,
            'amount': expense.amount,
            'currency': expense.currency,
            'category': expense.category,
            'date': expense.created_at.strftime('%Y-%m-%d'),
            'paid_by': ', '.join(paid_by_users)
        })

        if group.expenses:
            balance_sheet = calculate_balance(group)

    return render_template('group_detail.html', group=group, members=members, expenses=expenses,
                           balance_sheet=balance_sheet)


# Endpoint wysyłania powiadomienia
@app.route('/send_reminder/<int:receiver_id>', methods=['POST'])
def send_reminder(receiver_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # Użytkownik zalogowany (odbiorca płatności)
    receiver = User.query.get(session['user_id'])
    # Płatnik (osoba, której przypominamy o płatności)
    payer = User.query.get(receiver_id)

    if not payer:
        return jsonify({'error': 'User not found'}), 404

    data = request.json
    group_name = data.get('groupName', 'Unknown Group')

    # Sprawdzenie, czy zalogowany użytkownik ma prawo wysłać przypomnienie
    if receiver.username != data.get('receiverName'):
        return jsonify({'error': 'Permission denied'}), 403

    # Tworzenie wiadomości e-mail
    subject = "Payment Reminder"
    body = (
        f"Hi {payer.username},\n\n"
        f"{receiver.username} reminds you to settle your payment.\n"
        f"The payment is related to the group: {group_name}.\n\n"
        "Best regards,\nYour Group Manager"
    )

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = payer.email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Połączenie z serwerem SMTP WP.PL
        with smtplib.SMTP_SSL("smtp.wp.pl", 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, payer.email, msg.as_string())
            print(f"Email sent to {payer.email} from {sender_email}")

        return jsonify({'message': 'E-mail sent successfully!'}), 200
    except Exception as e:
        print(f"Error sending email: {e}")
        return jsonify({'error': 'Failed to send e-mail'}), 500


# Endpoint wyswietlania wykresow
@app.route('/charts/<int:group_id>')
def view_charts(group_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    group = Group.query.get_or_404(group_id)
    user = User.query.get(session['user_id'])

    if user not in group.members:
        flash('You are not a member of this group!', 'error')
        return redirect(url_for('view_groups'))

    if not group:
        return "Group not found", 404

    return render_template('charts.html', group=group)


# Endpoint generowania wykresow
@app.route('/charts_data/<int:group_id>', methods=['GET'])
def get_charts_data(group_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    group = Group.query.get_or_404(group_id)
    user = User.query.get(session['user_id'])

    if user not in group.members:
        flash('You are not a member of this group!', 'error')
        return redirect(url_for('view_groups'))

    if not group:
        return jsonify({"error": "Group not found"}), 404

    group_data = get_group_charts_data(group)
    user_data = get_user_charts_data(group, user.id)

    return jsonify({
        'groupData': group_data,
        'userData': user_data,
    })


# Endpoint dodawania wydatku
@app.route('/group/<int:group_id>/add_expense', methods=['GET', 'POST'])
def add_expense(group_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    group = Group.query.get_or_404(group_id)
    user = User.query.get(session['user_id'])

    if user not in group.members:
        flash('You are not a member of this group!', 'error')
        return redirect(url_for('view_groups'))

    if request.method == 'POST':
        description = request.form.get('description')
        amount = request.form.get('amount')
        currency = request.form.get('currency')  # Pobierz walutę
        category = request.form.get('category')
        split_type = request.form.get('split_type')
        selected_members = request.form.getlist('members')
        created_by = session['user_id']
        paid_by = request.form.get('paid_by')

        if not description or not amount:
            flash('Description and amount are needed!', 'error')
            return redirect(url_for('add_expense', group_id=group_id))

        try:
            amount = Decimal(amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash('Amount must be positive!', 'error')
            return redirect(url_for('add_expense', group_id=group_id))

        # Walidacja i podział wydatku
        shares = {}
        if split_type == 'equal':
            share_amount = round(amount / len(selected_members), 2)
            shares = {member_id: share_amount for member_id in selected_members}
            custom_split = False
        elif split_type == 'custom':
            total_custom_share = 0
            for member_id in selected_members:
                try:
                    member_share = Decimal(request.form.get(f'custom_share_{member_id}', 0)).\
                        quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    shares[member_id] = member_share
                    total_custom_share += member_share
                except ValueError:
                    flash('Custom shares must be numbers.', 'error')
                    return redirect(url_for('add_expense', group_id=group_id))

            if round(total_custom_share, 2) != round(amount, 2):
                flash('Custom shares do not add up to the total amount.', 'error')
                return redirect(url_for('add_expense', group_id=group_id))
            custom_split = True

        # Tworzenie nowego wydatku
        new_expense = Expense(
            description=description,
            amount=amount,  # Bez konwersji waluty
            currency=currency,  # Zapisywanie podanej waluty
            category=category,
            created_by=created_by,
            group_id=group.id,
            custom_split=custom_split
        )

        try:
            db.session.add(new_expense)
            db.session.flush()

            # Dodawanie udziałów
            for member_id, member_share in shares.items():
                expense_share = ExpenseShare(
                    expense_id=new_expense.id,
                    user_id=member_id,
                    share=member_share,
                    paid_by=paid_by
                )
                db.session.add(expense_share)

            db.session.commit()

            flash('Expense has been added with split!', 'success')
            return redirect(url_for('view_group', group_id=group_id))
        except Exception as e:
            db.session.rollback()
            flash('Error while adding an expense.', 'error')
            print(e)

    return render_template('add_expense.html', group=group)


@app.route('/expense/<int:expense_id>/edit', methods=['GET', 'POST'])
def edit_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    expense = Expense.query.get(expense_id)
    if not expense:
        flash("Expense not found.")
        return redirect(url_for('view_group', group_id=expense.group_id))

    group = expense.group
    user = User.query.get(session['user_id'])
    if user not in group.members:
        flash("You are not a member of this group!", 'error')
        return redirect(url_for('view_groups'))

    if expense.created_by != user.id:
        flash("You are not allowed to edit this expense.", 'error')
        return redirect(url_for('view_group', group_id=group.id))

    all_members = group.members
    members_dict = {member.id: member for member in all_members}

    if request.method == 'POST':
        description = request.form.get('description')
        amount = request.form.get('amount')
        currency = request.form.get('currency')  # Pobranie waluty z formularza
        category = request.form.get('category')
        split_type = request.form.get('split_type')
        paid_by = request.form.get('paid_by')

        selected_members = request.form.getlist('members')
        shares = {}

        # Walidacja danych wejściowych
        if not description or not amount:
            flash('Description and amount are needed!', 'error')
            return redirect(url_for('edit_expense', expense_id=expense.id))

        try:
            amount = Decimal(amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash('Amount must be a positive number!', 'error')
            return redirect(url_for('edit_expense', expense_id=expense.id))

        # Obsługa podziału
        if split_type == 'equal':
            share_amount = round(amount / len(selected_members), 2)
            shares = {int(member_id): share_amount for member_id in selected_members}
            expense.custom_split = False
        elif split_type == 'custom':
            total_custom_share = 0
            for member_id in selected_members:
                try:
                    member_share = Decimal(request.form.get(f'custom_share_{member_id}', 0)).\
                        quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    shares[int(member_id)] = member_share
                    total_custom_share += member_share
                except ValueError:
                    flash('Custom shares must be numbers.', 'error')
                    return redirect(url_for('edit_expense', expense_id=expense.id))

            if round(total_custom_share, 2) != round(amount, 2):
                flash('Custom shares do not add up to the total amount.', 'error')
                return redirect(url_for('edit_expense', expense_id=expense.id))

            expense.custom_split = True

        # Aktualizacja wydatku
        expense.description = description
        expense.amount = amount
        expense.currency = currency
        expense.category = category

        # Aktualizacja ExpenseShare
        ExpenseShare.query.filter_by(expense_id=expense.id).delete()
        for member_id, share in shares.items():
            new_share = ExpenseShare(expense_id=expense.id, user_id=member_id, share=share, paid_by=paid_by)
            db.session.add(new_share)

        db.session.commit()
        flash("Expense updated successfully.", "success")
        return redirect(url_for('view_group', group_id=group.id))

    return render_template('edit_expense.html', expense=expense, all_members=all_members,
                           members_dict=members_dict, shared_user_ids=[s.user_id for s in expense.shares])


# Endpoint usuwania wydatku
@app.route('/expense/<int:expense_id>/delete', methods=['GET', 'POST'])
def delete_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    expense = Expense.query.get(expense_id)
    if not expense:
        flash("Expense not found.")
        return redirect(url_for('view_group', group_id=expense.group_id))

    group = expense.group
    user = User.query.get(session['user_id'])
    if user not in group.members:
        flash("You are not a member of this group!", 'error')
        return redirect(url_for('view_groups'))

    if expense.created_by != user.id:  # Upewniamy się, że użytkownik jest twórcą wydatku
        flash("You are not allowed to delete this expense.", 'error')
        return redirect(url_for('view_group', group_id=group.id))

    group_id = expense.group_id

    db.session.delete(expense)
    db.session.commit()

    flash("Expense deleted successfully!")
    return redirect(url_for('view_group', group_id=group_id))


# Endpoint dodawania spłaty
@app.route('/group/<int:group_id>/settle', methods=['GET', 'POST'])
def settle_expense(group_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    group = Group.query.get_or_404(group_id)
    user = User.query.get(session['user_id'])

    if user not in group.members:
        flash('You are not a member of this group!', 'error')
        return redirect(url_for('view_groups'))

    if request.method == 'POST':
        payer_id = request.form.get('payer_id')
        receiver_id = user.id
        amount = Decimal(request.form.get('amount'))
        currency = request.form.get('currency')  # Waluta wybrana przez użytkownika

        payer = User.query.get(payer_id)
        receiver = user.id

        if payer_id == receiver_id:
            flash('Payer and receiver must be different users.', 'error')
            return redirect(url_for('view_group', group_id=group.id))

        if not payer or not receiver:
            return "Invalid payer or receiver", 400

        # Tworzymy nową spłatę
        settlement = Settlement(group_id=group.id, payer_id=payer.id, receiver_id=receiver, amount=amount,
                                currency=currency)
        db.session.add(settlement)

        db.session.commit()

        flash('Settlement added successfully!', 'success')
        return redirect(url_for('view_group', group_id=group.id))

    members = group.members
    return render_template('settlement_expense.html', group=group, members=members, user=user, default_currency="PLN")


# Endpoint edycji spłaty
@app.route('/group/<int:group_id>/settlement/edit/<int:settlement_id>', methods=['GET', 'POST'])
def edit_settlement(group_id, settlement_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    group = Group.query.get_or_404(group_id)
    settlement = Settlement.query.get_or_404(settlement_id)
    user = User.query.get(session['user_id'])

    if settlement.payer_id != session['user_id'] and settlement.receiver_id != session['user_id']:
        flash('You are not authorized to edit this settlement.', 'error')
        return redirect(url_for('view_group', group_id=group.id))

    if request.method == 'POST':
        payer_id = request.form.get('payer_id')
        receiver_id = user.id
        amount = Decimal(request.form.get('amount'))
        currency = request.form.get('currency')

        payer = User.query.get(payer_id)
        receiver = user.id

        if payer_id == receiver_id:
            flash('Payer and receiver must be different users.', 'error')
            return redirect(url_for('edit_settlement', group_id=group_id, settlement_id=settlement_id))

        if not payer or not receiver:
            flash('Invalid payer or receiver.', 'error')
            return redirect(url_for('edit_settlement', group_id=group_id, settlement_id=settlement_id))

        if amount <= 0:
            flash('Amount must be greater than zero.', 'error')
            return redirect(url_for('edit_settlement', group_id=group_id, settlement_id=settlement_id))

        # Aktualizacja spłaty
        settlement.payer_id = payer.id
        settlement.receiver_id = user.id
        settlement.amount = amount
        settlement.currency = currency  # Zaktualizowana waluta

        db.session.commit()

        flash('Settlement updated successfully!', 'success')
        return redirect(url_for('view_group', group_id=group.id))

    members = group.members
    return render_template('edit_settlement.html', group=group, settlement=settlement, user=user, members=members)


# Endpoin usuwania splaty
@app.route('/group/<int:group_id>/settlement/delete/<int:settlement_id>', methods=['POST'])
def delete_settlement(group_id, settlement_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    group = Group.query.get_or_404(group_id)
    settlement = Settlement.query.get_or_404(settlement_id)

    # Sprawdzanie, czy użytkownik jest zaangażowany w tę spłatę (payer lub receiver)
    if settlement.payer_id != session['user_id'] and settlement.receiver_id != session['user_id']:
        flash('You are not authorized to delete this settlement.', 'error')
        return redirect(url_for('view_group', group_id=group.id))

    try:
        db.session.delete(settlement)
        db.session.commit()
        flash('Settlement deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting settlement: {str(e)}', 'error')

    return redirect(url_for('view_group', group_id=group.id))


# Endpoint wylogowania
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


# Bazowy endpoint
@app.route('/')
def index():
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
