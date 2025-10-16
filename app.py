from flask import Flask, render_template, request, redirect, url_for, flash, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import random
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import time, datetime
from sqlalchemy import desc


app = Flask(__name__, template_folder="pages")

#SQL Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/project_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

#Tables

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    ticker = db.Column(db.String(5), nullable=False, unique=True)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    transactions = db.relationship('Transactions', backref='stock')
    portfolio_entries = db.relationship('Portfolio', backref='stock')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    fname = db.Column(db.String(100), nullable=False)
    lname = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Float, nullable=False)
    transactions = db.relationship('Transactions', backref='user')
    portfolio_entries = db.relationship('Portfolio', backref='user')
    role = db.Column(db.String(100), nullable=False)

class Transactions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(100), nullable=False)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)

class TradingHours(db.Model):
    day_of_week = db.Column(db.String(10), primary_key=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

class Holidays(db.Model):
    name = db.Column(db.String(100), primary_key=True)
    holiday_date = db.Column(db.Date, nullable=False)

# Flask-Login setup
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Randomize stock prices
def stock_randomize():
    with app.app_context():
        stocks = Stock.query.all()
        for stock in stocks:
            new_price = round(random.uniform(15,70), 2)
            stock.price = new_price
        db.session.commit()
    print('randomized!')

scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(stock_randomize, 'interval', seconds=30)
scheduler.start()

#getting current date + time
def check_time():
    current_datetime = datetime.now()
    formatted_time = current_datetime.strftime("%I:%M %p")
    return formatted_time

#check if market is open based on local time
def is_market_open():
    now = datetime.now()
    current_day = now.strftime("%A")
    current_time = now.time()

    holiday_today = Holidays.query.filter_by(holiday_date=now.date()).first()
    if holiday_today:
        return False
    
    trading_hours = TradingHours.query.filter_by(day_of_week=current_day).first()
    if not trading_hours:
        return False
    
    if trading_hours.start_time <= current_time <= trading_hours.end_time:
        return True
    return False

# Create tables
with app.app_context():
    #db.drop_all()
    db.create_all()

#Routes
@app.route("/")
def home():
    if not current_user.is_authenticated:
        return render_template("home.html")
    
    elif current_user.role == "admin":
        if not is_market_open() == True: 
            status = "Closed"
        else:
            status = "Open"
        current_time = check_time()
        user_portfolio = db.session.query(Portfolio).join(Stock).filter(Portfolio.user_id == current_user.id, Portfolio.quantity > 0).order_by(Stock.ticker.asc()).all()
        return render_template("dash_admin.html", current_time=current_time, status=status, user_portfolio=user_portfolio)
    
    else:
        if not is_market_open() == True: 
            status = "Closed"
        else:
            status = "Open"
        current_time = check_time()
        user_portfolio = db.session.query(Portfolio).join(Stock).filter(Portfolio.user_id == current_user.id, Portfolio.quantity > 0).order_by(Stock.ticker.asc()).all()
        transaction_summary = db.session.query(Transactions).join(Stock).filter(Transactions.user_id == current_user.id).order_by(desc(Transactions.date)).limit(15).all()
        portfolio_value = 0.00
        for e in user_portfolio:
            portfolio_value += (e.stock.price * int(e.quantity))
        portfolio_value = round(portfolio_value, 2)
        return render_template("dash_user.html", current_time=current_time, status=status, user_portfolio=user_portfolio, portfolio_value=portfolio_value, transaction_summary = transaction_summary)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/stocks")
def stocks():
    stocks = Stock.query.order_by(Stock.name.asc()).all()
    return render_template('stocks.html', stocks=stocks)

@app.route("/login_page")
def login_page():
    return render_template('login_page.html')

@app.route("/buy")
def buy():
    if is_market_open() == False:
        flash("Market is closed!", "danger")
        return redirect(url_for('stocks'))
    stocks = Stock.query.order_by(Stock.name.asc()).all()
    return render_template("buy.html", stocks=stocks)

@app.route("/sell")
def sell():
    if is_market_open() == False:
        flash("Market is closed!", "danger")
        return redirect(url_for('stocks'))
    stocks = Stock.query.order_by(Stock.name.asc()).all()
    return render_template('sell.html', stocks=stocks)

@app.route("/trading_hours")
def trading_hours():
    if current_user.role == "admin":
        days = TradingHours.query.all()
        return render_template("trading_hours.html", days=days)
    else:
        return redirect(url_for('home'))
    
@app.route('/get_market_hours', methods=['GET'])
def get_market_hours():
    if not current_user.role == "admin":
        return jsonify({'error': 'Unauthorized'}), 403

    day = request.args.get('day')
    if not day:
        return jsonify({'error': 'No day provided'}), 400

    record = TradingHours.query.filter_by(day_of_week=day).first()
    if record:
        return jsonify({
            'start_time': record.start_time.strftime("%H:%M"),
            'end_time': record.end_time.strftime("%H:%M")
        })
    else:
        return jsonify({'start_time': '', 'end_time': ''})

#Routes to ADD database tables

#Add Stock Route
@app.route('/add_stock/<string:name>/<float:price>/<int:quantity>')
def add_stock(name, price, quantity):
    if not name or not price or not quantity:
        flash('Fill all fields!', 'error')
        return redirect(url_for('home'))
    new_stock = Stock(name=name, price=price, quantity=quantity)

    try:
        db.session.add(new_stock)
        db.session.commit()
        flash(f'Stock {name} added!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding stock: {str(e)}', 'error')

    return redirect(url_for('stocks'))

#Add User Route
@app.route('/add_user/<string:email>/<string:password>/<string:fname>/<string:lname>')
def add_user(email, password, fname, lname):
    if not email or not password or not fname or not lname:
        flash('Fill all fields!', 'error')
        return redirect(url_for('home'))

    new_user = User(email=email, password=password, fname=fname, lname=lname, balance=0.00)
    try:
        db.session.add(new_user)
        db.session.commit()
        flash(f'User {new_user.email} added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding user: {str(e)}', 'error')

    return redirect(url_for('stocks'))


#Add Admin Route
@app.route('/add_admin/<string:email>/<string:password>/<string:fname>/<string:lname>')
def add_admin(email, password, fname, lname):
    if not email or not password or not fname or not lname:
        flash('Fill all fields!', 'error')
        return redirect(url_for('home'))

    new_admin = Admin(email=email, password=password, fname=fname, lname=lname)

    try:
        db.session.add(new_admin)
        db.session.commit()
        flash(f'User {new_admin.email} added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding admin: {str(e)}', 'error')

    return redirect(url_for('stocks'))


#Add Order Route
@app.route('/add_order/<int:quantity>/<string:date>/<float:total_price>/<string:transaction_type>/<int:user_id>/<int:stock_id>')
def add_order(quantity, date, total_price, transaction_type, user_id, stock_id):
    if not quantity or not date or not total_price or not transaction_type:
        flash('Fill all fields!', 'error')
        return redirect(url_for('home'))

    new_order = Transactions(quantity=quantity, date=date, total_price=total_price, transaction_type=transaction_type, user_id=user_id, stock_id=stock_id)

    try:
        db.session.add(new_order)
        db.session.commit()
        flash(f'Order {new_order.id} added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding admin: {str(e)}', 'error')

    return redirect(url_for('stocks'))

#FULL BUY STOCK PROCESS
@app.route('/buy_stock', methods=["POST"])
def buy_stock():
    stock_id = request.form['stock_id']
    stock = Stock.query.get_or_404(stock_id)
    stock_price = stock.price
    quantity = request.form['quantity']
    total_price = stock_price * float(quantity)
    user = current_user

    if user.balance < total_price:
        flash("Insufficient funds", "danger")
        return redirect(url_for("stocks"))
    
    try:
        user.balance -= total_price
        db.session.commit()
        flash(f"Successfully bought {quantity} * {stock.name} for ${total_price:.2f}.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error completing purchase: {str(e)}", "danger")
        return redirect(url_for("stocks"))
    
    #ADD TO PORTFOLIO, IF X USER HAS X STOCK ALREADY, ADD TO IT, OTHERWISE MAKE NEW ENTRY
    portfolio_entry = Portfolio.query.filter_by(user_id=user.id, stock_id=stock.id).first()
    if portfolio_entry:
        portfolio_entry.quantity += int(quantity)
    else:
        portfolio_entry = Portfolio(user_id=user.id, stock_id=stock.id, quantity=quantity)
        db.session.add(portfolio_entry)

    #add entry to Transactions table
    new_transaction = Transactions(
        user_id=user.id, 
        stock_id=stock.id, 
        quantity=quantity,
        date = datetime.now(),
        total_price = total_price,
        transaction_type = 'buy'
    )
    db.session.add(new_transaction)
    #end
    db.session.commit()
    return redirect(url_for("stocks"))


#FULL SELL STOCK PROCESS
@app.route('/sell_stock', methods=["POST"])
def sell_stock():
    stock_id = request.form['stock_id']
    stock = Stock.query.get_or_404(stock_id)
    stock_price = stock.price
    quantity = request.form['quantity']
    total_price = stock_price * float(quantity)
    user = current_user

    #CHECK IF PORTFOLIO HAS ENOUGH STOCK TO PULL FROM; ELSE RETURN TO PAGE
    portfolio_entry = Portfolio.query.filter_by(user_id=user.id, stock_id=stock.id).first()
    if not portfolio_entry:
        flash(f"You do not own at least {quantity} shares of {stock.name}", "danger")
        return redirect(url_for("stocks"))
    
    elif portfolio_entry.quantity < int(quantity):
        flash(f"You do not own at least {quantity} shares of {stock.name}", "danger")
        return redirect(url_for("stocks"))
    else:
        portfolio_entry.quantity -= int(quantity)
    try:
         user.balance += total_price
         db.session.commit()
         flash(f"Successfully sold {quantity} {stock.name} stock for ${total_price:.2f}.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error completing sale: {str(e)}", "danger")
        return redirect(url_for("stocks"))
    
    #add entry to Transactions table
    new_transaction = Transactions(
        user_id=user.id, 
        stock_id=stock.id, 
        quantity=quantity,
        date = datetime.now(),
        total_price = total_price,
        transaction_type = 'sell'
    )
    db.session.add(new_transaction)
        
    #end
    db.session.commit()
    return redirect(url_for("stocks"))



#Add Portfolio Route
@app.route('/add_portfolio/<int:quantity>/<int:user_id>/<int:stock_id>')
def add_portfolio(quantity, user_id, stock_id):
    if not quantity:
        flash('Fill all fields!', 'error')
        return redirect(url_for('home'))

    new_portfolio = Portfolio(quantity=quantity, user_id=user_id, stock_id=stock_id)

    try:
        db.session.add(new_portfolio)
        db.session.commit()
        flash(f'Portfolio {new_portfolio.id} added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding portfolio: {str(e)}', 'error')

    return redirect(url_for('stocks'))

#Add Sell Route
'''@app.route("/sell_stock/<float:balance>/<float:price>/<float:shares>", methods=["POST", "GET"])
def sell_stock(balance: float,price : int, shares: int):
    if not balance or not price or not shares:
        flash('Fill all fields!', 'error')
        return redirect(url_for('home'))   

    sell_stock = Sell(balance=balance, price=price, shares=shares) 
    new_balance = (balance - (price * shares))'''


#Routes to EDIT database tables

#Add to balance
@app.route('/add_funds', methods=["get", "post"])
def add_funds():
    
    if request.method == "POST":
        user = User.query.get_or_404(current_user.id)
        amount = float(request.form['deposit_amount'])

        try:
            user.balance += amount
            db.session.commit()
            flash(f'${amount:.2f} deposited!', 'success')
            return redirect(url_for('home'))

        except Exception as e:
                flash(f'Error: {str(e)}', 'error')
                return redirect(url_for('home'))
        
    return render_template("add_funds.html")
    

#Subtract from balance
@app.route('/subtract_funds', methods=['POST'])
def subtract_funds():  
    if request.method == "POST":
        user = User.query.get_or_404(current_user.id)
        amount = float(request.form['withdraw_amount'])
        if user.balance >= amount:
            try:
                user.balance -= amount
                db.session.commit()
                flash(f'${amount:.2f} withdrawn!', 'success')
                return redirect(url_for('home'))

            except Exception as e:
                    flash(f'Error: {str(e)}', 'error')
                    return redirect(url_for('home'))
        else:
            flash(f'Account balance insufficient', 'danger')
            return redirect(url_for('add_funds'))
        
    return render_template("add_funds.html")


#Stock
#@app.route('/edit_stock_page/<string:name>/<float:price>/<int:quantity>/<int:id>')
#def edit_stock(name, price, quantity, id):
#    if not name or not price or not quantity:
#        flash('Fill all fields!', 'error')
#        return redirect(url_for('home'))
#    
#    stock = Stock.query.get_or_404(id)
#    stock.name = name
#    stock.price = price
#    stock.quantity = quantity
#
#
#    try:
#        db.session.commit()
#        flash(f'Stock {name} updated!', 'success')
#    except Exception as e:
#        db.session.rollback()
#        flash(f'Error updating stock: {str(e)}', 'error')#
#
#    return redirect(url_for('stocks'))

#User
@app.route('/edit_user/<string:email>/<string:password>/<string:fname>/<string:lname>/<int:id>')
def edit_user(email, password, fname, lname, id):
    if not email or not password or not fname or not lname:
        flash('Fill all fields!', 'error')
        return redirect(url_for('home'))
    
    user = User.query.get_or_404(id)
    user.email = email
    user.password = password
    user.fname = fname
    user.lname = lname


    try:
        db.session.commit()
        flash(f'User {email} updated!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user: {str(e)}', 'error')

    return redirect(url_for('stocks'))

#Admin
@app.route('/edit_admin/<string:email>/<string:password>/<string:fname>/<string:lname>/<int:id>')
def edit_admin(email, password, fname, lname, id):
    if not email or not password or not fname or not lname:
        flash('Fill all fields!', 'error')
        return redirect(url_for('home'))
    
    admin = Admin.query.get_or_404(id)
    admin.email = email
    admin.password = password
    admin.fname = fname
    admin.lname = lname


    try:
        db.session.commit()
        flash(f'Admin {email} updated!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating Admin: {str(e)}', 'error')

    return redirect(url_for('stocks'))

#Portfolio
@app.route('/edit_portfolio/<int:quantity>/<int:user_id>/<int:stock_id>/<int:portfolio_id>')
def edit_portfolio(quantity, user_id, stock_id, portfolio_id):
    if not quantity or not user_id or not stock_id:
        flash('Fill all fields!', 'error')
        return redirect(url_for('home'))
    
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    portfolio.quantity = quantity

    try:
        db.session.commit()
        flash(f'Portfolio #{portfolio_id} updated!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating portfolio: {str(e)}', 'error')

    return redirect(url_for('stocks'))


#Routes to DELETE stuff

#Stock
@app.route('/delete_stock/<int:id>')
def delete_stock(id):
    stock = Stock.query.get_or_404(id)
    try:
        db.session.delete(stock)
        db.session.commit()
        flash(f'User {stock.name} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting stock: {str(e)}', 'error')
    return redirect(url_for('stock_admin'))


#User
@app.route('/delete_user/<int:id>')
def delete_user(id):
    user = User.query.get_or_404(id)
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.email} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
    return redirect(url_for('stocks'))


#Admin
@app.route('/delete_admin/<int:id>')
def delete_admin(id):
    admin = Admin.query.get_or_404(id)
    try:
        db.session.delete(admin)
        db.session.commit()
        flash(f'User {admin.email} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting admin: {str(e)}', 'error')
    return redirect(url_for('stocks'))


#Order
@app.route('/delete_order/<int:id>')
def delete_order(id):
    order = Transactions.query.get_or_404(id)
    try:
        db.session.delete(order)
        db.session.commit()
        flash(f'Order {order.id} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting order: {str(e)}', 'error')
    return redirect(url_for('stocks'))


#Portfolio
@app.route('/delete_portfolio/<int:id>')
def delete_portfolio(id):
    portfolio = Portfolio.query.get_or_404(id)
    try:
        db.session.delete(portfolio)
        db.session.commit()
        flash(f'Portfolio {portfolio.id} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting portfolio: {str(e)}', 'error')
    return redirect(url_for('stocks'))

@app.route('/test')
def test_page():
    return render_template('test.html')


#Registration Route
@app.route('/signup', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = User(
            email=request.form.get("email"),
            password=request.form.get("password"),
            fname=request.form.get("fname"),
            lname=request.form.get("lname"),
            balance=0.00,
            role="user"
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("signup.html")

#Log-in Route
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form.get("email")).first()
        if user and user.password == request.form.get("password"):
            login_user(user)
            return redirect(url_for("home"))
        
        else:
            flash(f"Error signing in: login invalid", "error")
    return render_template("login_page.html")

#Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

#stock_admin route
@app.route('/stock_admin')
@login_required
def stock_admin():
    # optional admin-only check
    if getattr(current_user, "role", None) != "admin":
        flash("Access denied: admin only", "error")
        return redirect(url_for("home"))
    stocks = Stock.query.order_by(Stock.name.asc()).all()
    return render_template('stock_admin.html', stocks=stocks)

#Add Stock Route
@app.route('/add_stock_page', methods=['GET', 'POST'])
@login_required
def add_stock_page():
    # admin-only access
    if getattr(current_user, "role", None) != "admin":
        flash("Access denied: admin only", "error")
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("name")
        ticker = request.form.get("ticker")
        try:
            price = float(request.form.get("price", 0))
        except (TypeError, ValueError):
            price = None
        try:
            quantity = int(request.form.get("quantity", 0))
        except (TypeError, ValueError):
            quantity = None

        if not name or not ticker or price is None or quantity is None:
            flash("Please fill all fields correctly.", "error")
            return redirect(url_for("add_stock_page"))

        new_stock = Stock(name=name, price=price, quantity=quantity, ticker=ticker)
        db.session.add(new_stock)
        db.session.commit()
        flash(f"Stock '{name}' added.", "success")
        return redirect(url_for("stock_admin"))

    return render_template("add_stock_page.html")

#Edit Stock Route
@app.route('/edit_stock_page/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_stock(id):
    if getattr(current_user, "role", None) != "admin":
        flash("Access denied: admin only", "error")
        return redirect(url_for("home"))

    stock = Stock.query.get_or_404(id)

    if request.method == 'POST':
        name = request.form.get('name')
        ticker = request.form.get('ticker')
        try:
            price = float(request.form.get('price', 0))
        except (TypeError, ValueError):
            price = None
        try:
            quantity = int(request.form.get('quantity', 0))
        except (TypeError, ValueError):
            quantity = None

        if not name or not ticker or price is None or quantity is None:
            flash("Please fill all fields correctly.", "error")
            return redirect(url_for('edit_stock_page', id=id))

        stock.name = name
        stock.price = price
        stock.quantity = quantity
        stock.ticker = ticker

        try:
            db.session.commit()
            flash(f"Stock '{name}' updated.", "success")
            return redirect(url_for('stock_admin'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating stock: {str(e)}", "error")
            return redirect(url_for('edit_stock_page', id=id))

    # GET -> show form pre-filled
    return render_template('edit_stock_page.html', stock=stock)

#Initialize Market Hours
def init_market_hours():
    days_of_week = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    for day in days_of_week:
        trading_hours = TradingHours(day_of_week=day, start_time=time(8, 0), end_time=time(17, 0))
        db.session.add(trading_hours)
    db.session.commit()

#run this to populate the db with the days of the week quickly.
#with app.app_context():
#    init_market_hours()

#Edit Market Hours
@app.route("/edit_market_hours", methods=["POST"])
def edit_market_hours():
    day = TradingHours.query.get_or_404(request.form["day_of_week"])
    day.start_time = request.form["start_time"]
    day.end_time = request.form["end_time"]
    db.session.commit()
    flash(f"Updated!", "success")
    return render_template("trading_hours.html")

if __name__ == '__main__':
    app.run(debug=True)

#testing git branch
#AHHHHHHHHHHHHHHHHHHHHHHHHHHH 