from flask import Flask, render_template, request, redirect, flash, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import os
from babel.numbers import format_currency

app = Flask(__name__)

# Use environment variable in production, fallback to hardcoded for local dev
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------------------
# Models
# ---------------------------

class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    contact_number = db.Column(db.String(20))

class Booking(db.Model):
    __tablename__ = "booking"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    contact_number = db.Column(db.String(20), nullable=False)
    event = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)
    from_time = db.Column(db.Time, nullable=False)
    to_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="Pending")


class Complaint(db.Model):
    __tablename__ = "complaint"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Cart(db.Model):
    __tablename__ = "cart"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    event = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)
    from_time = db.Column(db.Time, nullable=False)
    to_time = db.Column(db.Time, nullable=False)


    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event": self.event,
            "price": self.price,
            "from_date": self.from_date.strftime("%Y-%m-%d") if self.from_date else None,
            "to_date": self.to_date.strftime("%Y-%m-%d") if self.to_date else None,
            "time": f"{self.from_time.strftime('%I:%M %p')} to {self.to_time.strftime('%I:%M %p')}"
        }



# Initialize DB
with app.app_context():
    db.create_all()

# ---------------------------
# Routes
# ---------------------------

def format_inr(amount):
    # Format with Indian commas and ₹ symbol
    return format_currency(amount, 'INR', locale='en_IN')


@app.route('/catalogue')
def catalogue():
    events = [
        {"name": "Wedding Photography", "price": 2000},
        {"name": "Engagement Shoot", "price": 1500},
        {"name": "Birthday Event", "price": 1200},
        {"name": "Corporate Event", "price": 2500},
        {"name": "Pre-Wedding Shoot", "price": 1800},
        {"name": "Anniversary Celebration", "price": 2000},
        {"name": "Music Concert", "price": 3000},
        {"name": "Fashion Show", "price": 3500},
        {"name": "Product Launch", "price": 2800},
        {"name": "School/College Event", "price": 1500},
    ]
    return render_template("catalogue.html", events=events)


@app.route('/catalogue_booking', methods=['GET', 'POST'])
def catalogue_booking():
    event = request.args.get("event")
    price = request.args.get("price")

    if 'user_id' not in session:
        return render_template("catalogue_booking.html", event=event, price=price, user=None)

    user = db.session.get(User, session['user_id'])

    if request.method == 'POST':
        event_name = request.form.get('event')
        price_str = request.form.get('price')

        if not price_str:
            flash("Price not received from form.", "danger")
            return redirect(url_for('catalogue'))

        price_per_hour = int(price_str)

        from_date_str = request.form.get('from_date')
        to_date_str = request.form.get('to_date')
        from_time_str = request.form.get('from_time')
        to_time_str = request.form.get('to_time')

        # Parse dates/times
        from_date_obj = datetime.strptime(from_date_str, "%Y-%m-%d").date()
        to_date_obj = datetime.strptime(to_date_str, "%Y-%m-%d").date()
        from_time_obj = datetime.strptime(from_time_str, "%H:%M").time()
        to_time_obj = datetime.strptime(to_time_str, "%H:%M").time()

        # Calculate hours and price
        start_dt = datetime.combine(from_date_obj, from_time_obj)
        end_dt = datetime.combine(to_date_obj, to_time_obj)
        hours_total = (end_dt - start_dt).total_seconds() / 3600
        total_price = int(price_per_hour * hours_total)

        action = request.form.get("action")

        if action == 'cart':
            new_cart_item = Cart(
                user_id=session['user_id'],
                event=event_name,
                price=total_price,
                from_date=from_date_obj,
                to_date=to_date_obj,
                from_time=from_time_obj,
                to_time=to_time_obj
            )
            db.session.add(new_cart_item)
            db.session.commit()
            session['cart_count'] = Cart.query.filter_by(user_id=session['user_id']).count()
            flash(f"🛒 Added to cart! Total ₹{total_price}", "info")
            return redirect(url_for('cart'))

        elif action == 'pay':
            new_booking = Booking(
                name=user.name,
                email=user.email,
                contact_number=user.contact_number,
                event=event_name,
                price=total_price,
                from_date=from_date_obj,
                to_date=to_date_obj,
                from_time=from_time_obj,
                to_time=to_time_obj,
                status="Pending"
            )
            db.session.add(new_booking)
            db.session.commit()
            flash(f"✅ Booking confirmed for {event_name}", "success")
            return redirect(url_for('account', popup="true"))

    return render_template("catalogue_booking.html", event=event, price=price, user=user)

@app.context_processor
def inject_user():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return dict(current_user=user)
    return dict(current_user=None)


@app.template_filter('datetimeformat')
def datetimeformat(value, format="%d %B %Y"):
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime(format)
    except Exception:
        return value


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = generate_password_hash(request.form.get('password'))
        contact_number = request.form.get('contact_number')  # ✅ still here

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash("Email already registered! Please login.", "danger")
            return redirect(url_for('login'))

        # ✅ Include contact_number when creating the new user
        new_user = User(
            name=name,
            email=email,
            password=password,
            contact_number=contact_number
        )

        db.session.add(new_user)
        db.session.commit()
        # send_email("admin@example.com", "New User Signup",
        #    f"New user {new_user.name} has registered with email {new_user.email}.")
        flash("Signup successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')

        admins = {
            'ansh': 'ansh@123',
            'vansh': 'vansh@123'
        }

        if name in admins and password == admins[name]:
            session['admin_name'] = name
            flash(f"Welcome, Admin {name.capitalize()}!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid admin credentials!", "danger")
            return redirect(url_for('admin_login'))

    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin_name'):
        flash("Please login as admin.", "warning")
        return redirect(url_for('admin_login'))

    users = User.query.all()
    bookings = Booking.query.all()
    complaints = Complaint.query.all()

    return render_template('admin_dashboard.html', users=users, bookings=bookings, complaints=complaints)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@example.com'
app.config['MAIL_PASSWORD'] = 'your_app_password'

mail = Mail(app)

def send_email(to, subject, body):
    msg = Message(subject, recipients=[to], body=body, sender="your_email@example.com")
    mail.send(msg)

@app.route('/approve_booking/<int:id>', methods=['POST'])
def approve_booking(id):
    booking = Booking.query.get_or_404(id)
    booking.status = "Approved"
    db.session.commit()
    flash("Booking approved successfully.", "success")
    return redirect(url_for('admin_bookings'))

@app.route('/reject_booking/<int:id>', methods=['POST'])
def reject_booking(id):
    booking = Booking.query.get_or_404(id)
    booking.status = "Rejected"
    db.session.commit()
    flash("Booking rejected successfully.", "danger")
    return redirect(url_for('admin_bookings'))

@app.route('/edit_user/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    user.name = request.form['name']
    user.email = request.form['email']
    user.contact_number = request.form['contact_number']
    db.session.commit()
    flash("User updated successfully.", "success")
    return redirect(url_for('admin_users'))


@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully.", "danger")
    return redirect(url_for('admin_users'))

@app.route('/exit_admin_mode')
def exit_admin_mode():
    session.pop('admin_name', None)
    flash("Exited admin mode.", "info")
    return redirect(url_for('home'))

@app.route('/change_admin')
def change_admin():
    session.pop('admin_name', None)
    flash("Switch admin account.", "info")
    return redirect(url_for('admin_login'))

@app.route('/admin/bookings')
def admin_bookings():
    users = User.query.all()
    bookings = Booking.query.all()
    complaints = Complaint.query.all()
    return render_template('admin_dashboard.html', active_tab='bookings', users=users, bookings=bookings, complaints=complaints)

@app.route('/admin/users')
def admin_users():
    users = User.query.all()
    bookings = Booking.query.all()
    complaints = Complaint.query.all()
    return render_template('admin_dashboard.html', active_tab='users', users=users, bookings=bookings, complaints=complaints)

@app.route('/admin/complaints')
def admin_complaints():
    users = User.query.all()
    bookings = Booking.query.all()
    complaints = Complaint.query.all()
    return render_template('admin_dashboard.html', active_tab='complaints', users=users, bookings=bookings, complaints=complaints)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Admin login
        if email == 'admin' and password == 'admin123':
            session['is_admin'] = True
            flash("Welcome Admin!", "success")
            return redirect(url_for('admin_login'))

        # Normal user login
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("No account found with that email.", "no_account")
            return render_template('login.html')

        if user and check_password_hash(user.password, password):
            # ✅ set user session
            session['user_id'] = user.id
            session['username'] = user.name
            session['user_email'] = user.email

            # ✅ load this user's cart from DB or start empty
            # ✅ Only store cart count, not items
            user_cart = Cart.query.filter_by(user_id=user.id).all()
            session['cart_count'] = len(user_cart)


            flash(f"Welcome back, {user.name}!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid password!", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    bookings = Booking.query.filter_by(email=user.email).all()

    # Update booking statuses
    for booking in bookings:
        try:
            booking_end = datetime.combine(booking.to_date, booking.to_time)
            if booking_end < datetime.now():
                booking.status = "Completed"
            else:
                booking.status = "Pending"
        except Exception as e:
            print("Parse error:", e)
            booking.status = "Unknown"

    db.session.commit()

    return render_template('account.html', user=user, bookings=bookings)


@app.route('/edit_user', methods=['POST'])
def update_user():   # renamed function
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    user.name = request.form.get('name')
    user.email = request.form.get('email')
    user.contact_number = request.form.get('contact_number')

    try:
        db.session.commit()
        flash("✅ User details updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating user: {e}", "danger")

    return redirect(url_for('account'))


@app.route('/feedback', methods=['POST'])
def feedback():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    feedback_text = request.form.get('feedback')
    # Save feedback to DB or handle as needed
    flash("✅ Thank you for your feedback!", "success")
    return redirect(url_for('account'))


@app.route('/complaint', methods=['POST'])
def complaint():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    complaint_text = request.form.get('complaint')
    # Save complaint to DB or handle as needed
    flash("⚠️ Your complaint has been submitted.", "warning")
    return redirect(url_for('account'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('cart', None)   # ✅ clear cart on signout
    flash("You have been signed out.", "info")
    return redirect(url_for('home'))

@app.route('/')
def home():
    hero_images = [
        "/static/images/wedding_bg1.jpg",
        "/static/images/wedding_bg2.jpg",
        "/static/images/wedding_bg3.jpg",
        "/static/images/wedding_bg4.jpg"
    ]
    event_images = [
        "/static/images/wedding_photography.jpg",
        "/static/images/engagement_shoot.jpg",
        "/static/images/birthday_event.jpg",
        "/static/images/corporate_event.jpg",
        "/static/images/prewedding_shoot.jpg",
        "/static/images/anniversary_celebration.jpg",
        "/static/images/music_concert.jpg",
        "/static/images/fashion_show.jpg",
        "/static/images/product_launch.jpg",
        "/static/images/school_event.jpg"
    ]
    return render_template('home.html', hero_images=hero_images, event_images=event_images)


@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        flash("Please login to delete your account.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    if user:
        db.session.delete(user)
        db.session.commit()
        session.clear()  # ✅ log out after deletion
        flash("Your account has been deleted successfully.", "success")
        return redirect(url_for('signup'))
    else:
        flash("User not found.", "danger")
        return redirect(url_for('account'))

def inr_format(value):
    # Convert to int for grouping
    s = str(int(value))
    # First group (last 3 digits)
    last3 = s[-3:]
    # Remaining digits
    rest = s[:-3]
    if rest != '':
        # Insert commas every 2 digits in the rest
        rest = ','.join([rest[max(i-2,0):i] for i in range(len(rest),0,-2)][::-1])
        return rest + ',' + last3
    else:
        return last3

# Register filter with Jinja
app.jinja_env.filters['inr'] = inr_format


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash("Please login to view your cart.", "warning")
        return redirect(url_for('login'))

    # Fetch raw Cart objects
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    session['cart_count'] = len(cart_items)

    # Format times into strings for display
    formatted_items = []
    for c in cart_items:
        # Calculate hours between start and end
        hours_total = None
        if c.from_date and c.to_date and c.from_time and c.to_time:
            start_dt = datetime.combine(c.from_date, c.from_time)
            end_dt   = datetime.combine(c.to_date, c.to_time)
            hours_total = (end_dt - start_dt).total_seconds() / 3600

        per_hour_price = c.price / hours_total if hours_total else c.price

        formatted_items.append({
            "id": c.id,
            "event": c.event,
            "price": c.price,  # keep raw number
            "from_date": c.from_date.strftime("%Y-%m-%d") if c.from_date else None,
            "to_date": c.to_date.strftime("%Y-%m-%d") if c.to_date else None,
            "from_time": c.from_time.strftime("%I:%M %p") if c.from_time else None,
            "to_time": c.to_time.strftime("%I:%M %p") if c.to_time else None,
            "per_hour": int(per_hour_price)  # ✅ cast to int to remove .0
        })

    print("🛒 Cart items fetched:", len(formatted_items))
    return render_template('cart.html', cart_items=formatted_items)

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    events = [
        {"name": "Wedding Photography", "price": 2000},
        {"name": "Engagement Shoot", "price": 1500},
        {"name": "Birthday Event", "price": 1200},
        {"name": "Corporate Event", "price": 2500},
        {"name": "Pre-Wedding Shoot", "price": 1800},
        {"name": "Anniversary Celebration", "price": 2000},
        {"name": "Music Concert", "price": 3000},
        {"name": "Fashion Show", "price": 3500},
        {"name": "Product Launch", "price": 2800},
        {"name": "School/College Event", "price": 1500},
    ]
    popup = False
    selected_event = None

    if request.method == 'POST':
        print("🧾 Full form data:", request.form)
        event_name = request.args.get("event")
        event_price = request.args.get("price")
        popup = request.args.get("popup") == "true"

        selected_event = None
        if event_name and event_price:
            selected_event = {"name": event_name, "price": event_price}

        # Require login
        if 'user_id' not in session:
            flash("Please login or signup to request a booking.", "warning")
            return redirect(url_for('login'))

        # Get user details
        user = db.session.get(User, session['user_id'])
        name = user.name
        email = user.email
        contact_number = request.form.get('contact_number')
        event_name = request.form.get('event')
        price_per_hour = int(str(request.form.get('price')).replace("₹", "").strip())

        # Handle single date booking
        single_date = request.form.get("date")
        from_date_str = request.form.get('from_date')
        to_date_str = request.form.get('to_date')

        if single_date:
            from_date_str = single_date
            to_date_str = single_date

        from_time_str = request.form.get('from_time')
        to_time_str = request.form.get('to_time')

        if not from_date_str or not to_date_str or not from_time_str or not to_time_str:
            flash("Please select all dates and times before submitting.", "warning")
            return redirect(url_for('booking'))

        # Parse dates
        try:
            from_date_obj = datetime.strptime(from_date_str, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date_str, "%Y-%m-%d").date()
        except ValueError as e:
            flash(f"Date format error: {e}", "danger")
            return redirect(url_for('booking'))

        # Parse times
        try:
            from_time_obj = datetime.strptime(from_time_str.strip(), "%I:%M %p").time()
            to_time_obj = datetime.strptime(to_time_str.strip(), "%I:%M %p").time()
        except ValueError:
            try:
                from_time_obj = datetime.strptime(from_time_str.strip(), "%H:%M").time()
                to_time_obj = datetime.strptime(to_time_str.strip(), "%H:%M").time()
            except ValueError as e:
                flash(f"Time format error: {e}", "danger")
                return redirect(url_for('booking'))

        # ✅ Continuous hours calculation across multiple days
        start_dt = datetime.combine(from_date_obj, from_time_obj)
        end_dt   = datetime.combine(to_date_obj, to_time_obj)

        if end_dt <= start_dt:
            flash("End date/time must be after start date/time.", "danger")
            return redirect(url_for('booking'))

        hours_total = (end_dt - start_dt).total_seconds() / 3600
        total_price = price_per_hour * hours_total

        print("DEBUG:", start_dt, "to", end_dt, "=", hours_total, "hours → ₹", total_price)


        print("DEBUG:", start_dt, "to", end_dt, "=", hours_total, "hours → ₹", total_price)

        # Decide which date string to display
        date_display = single_date if single_date else f"{from_date_str} to {to_date_str}"
        time_display = f"{from_time_str} to {to_time_str}"

        action = request.form.get("action")

        if action == 'cart':
            user_id = int(session.get('user_id'))
            new_cart_item = Cart(
                user_id=user_id,
                event=event_name,
                price=int(total_price),
                from_date=from_date_obj,
                to_date=to_date_obj,
                from_time=from_time_obj,
                to_time=to_time_obj
            )
            try:
                db.session.add(new_cart_item)
                db.session.commit()
                print("✅ Cart item added:", new_cart_item.id)
            except Exception as e:
                db.session.rollback()
                flash(f"Database error: {e}", "danger")
                return redirect(url_for('booking'))

            updated_cart = Cart.query.filter_by(user_id=session['user_id']).all()
            session['cart_count'] = len(updated_cart)

            flash(f"🛒 Added to cart! Total ₹{int(total_price)}", "info")
            return redirect(url_for('booking'))

        elif action == 'pay':
            user = db.session.get(User, session['user_id'])

            new_booking = Booking(
        name=user.name,
        email=user.email,
        contact_number=user.contact_number,
        event=event_name,
        price=int(total_price),
        from_date=from_date_obj,
        to_date=to_date_obj,
        from_time=from_time_obj,
        to_time=to_time_obj,
        status="Pending"
    )
            db.session.add(new_booking)
            db.session.commit()
            print("✅ Booking confirmed for user:", session['user_id'])

            return redirect(url_for('account', popup="true"))



    template = "booking_form.html" if popup else "booking.html"
    return render_template(template, events=events, booked_dates=[], selected_event=selected_event)


@app.route('/remove_from_cart/<int:index>', methods=['POST'])
def remove_from_cart(index):
    if 'user_id' not in session:
        flash("Please login to modify your cart.", "warning")
        return redirect(url_for('login'))

    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    if 0 <= index < len(cart_items):
        db.session.delete(cart_items[index])
        db.session.commit()
        flash("❌ Item removed from cart.", "danger")

    updated_cart = Cart.query.filter_by(user_id=session['user_id']).all()
    session['cart_count'] = len(updated_cart)

    return redirect(url_for('cart'))

@app.route('/pay_now/<int:index>', methods=['POST'])
def pay_now(index):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    if 0 <= index < len(cart_items):
        item = cart_items[index]

        # ✅ Get user details from DB
        user = db.session.get(User, session['user_id'])

        new_booking = Booking(
            name=user.name,
            email=user.email,
            contact_number=user.contact_number,
            event=item.event,
            price=item.price,
            from_date=item.from_date,
            to_date=item.to_date,
            from_time=item.from_time,
            to_time=item.to_time,
            status="Pending"
        )
        db.session.add(new_booking)
        db.session.commit()

        db.session.delete(item)
        db.session.commit()

    updated_cart = Cart.query.filter_by(user_id=session['user_id']).all()
    session['cart_count'] = len(updated_cart)

    session['show_popup'] = True
    return redirect(url_for('account'))



@app.route('/contact')
def contact():
    return render_template('contact.html')

# @app.route('/complaint', methods=['GET', 'POST'])
# def complaint():
#     if request.method == 'POST':
#         name = request.form['name']
#         email = request.form['email']
#         message = request.form['message']
#         new_complaint = Complaint(name=name, email=email, message=message)
#         db.session.add(new_complaint)
#         db.session.commit()
#         # send_email(
#         #     "admin@example.com",
#         #     "New Complaint Submitted",
#         #     f"User {name} submitted a complaint: {message}"
#         # )
#         flash("📩 Complaint submitted!", "info")
#         return redirect('/complaint')
#     return render_template('complaint.html')

# ---------------------------
# Run App
# ---------------------------

if __name__ == "__main__":
    app.run(debug=True)
