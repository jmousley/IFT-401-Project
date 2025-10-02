from flask import Flask, render_template, request, redirect, url_for, flash, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__, template_folder="pages")


#SQL Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/project_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'

db = SQLAlchemy(app)

#Tables

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    orders = db.relationship('Order', backref='stock')
    portfolio_entries = db.relationship('Portfolio', backref='stock')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    fname = db.Column(db.String(100), nullable=False)
    lname = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Float, nullable=False)
    orders = db.relationship('Order', backref='user')
    portfolio_entries = db.relationship('Portfolio', backref='user')

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    fname = db.Column(db.String(100), nullable=False)
    lname = db.Column(db.String(100), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(100), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(100), nullable=False)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)


# Create tables
with app.app_context():
    #db.drop_all()
    db.create_all()

#Routes

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/stocks")
def stocks():
    stocks = Stock.query.all()
    return render_template('stocks.html', stocks=stocks)

@app.route("/login_signup")
def login_signup():
    return render_template('login_signup.html')

@app.route("/buy")
def buy():
    if request.method == "POST":
        stock_id = request.form.get("stock_id", type=int)
        qty      = request.form.get("quantity", type=int)

        if not stock_id or not qty or qty < 1:
            flash("Pick a stock and enter a quantity.", "warning")
            return redirect(url_for("buy"))

        stock = Stock.query.get_or_404(stock_id)

        stock.quantity = (stock.quantity or 0) - qty
        db.session.commit()

        flash(f"Success: bought {qty} × {stock.name}.", "success")
        return redirect(url_for("stocks"))

    # GET: load stocks from MySQL
    stocks = Stock.query.order_by(Stock.name.asc()).all()
    return render_template("buy.html", stocks=stocks)

@app.route("/sell")
def sell():
    stocks = Stock.query.all()
    return render_template('sell.html', stocks=stocks)

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

    new_order = Order(quantity=quantity, date=date, total_price=total_price, transaction_type=transaction_type, user_id=user_id, stock_id=stock_id)

    try:
        db.session.add(new_order)
        db.session.commit()
        flash(f'Order {new_order.id} added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding admin: {str(e)}', 'error')

    return redirect(url_for('stocks'))

@app.route('/buy_stock', methods=["POST"])
def buy_stock():
    stock_id = request.form['stock_id']
    stock = Stock.query.get_or_404(stock_id)
    stock_price = stock.price
    quantity = request.form['quantity']
    total_price = stock_price * float(quantity)

    user = User.query.get_or_404(2)
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
@app.route('/add_funds/<int:id>')
def add_funds(id):
    
    user = User.query.get_or_404(id)
    #amount = request.form['addamount']
    amount = 500.00
    new_amount = user.balance + float(amount)

    try:
        user.balance = new_amount
        db.session.commit()
        flash('Success!', 'success')
        return redirect(url_for('home'))

    except Exception as e:
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('home'))
    

#Subtract from balance
# @app.route('/subtract_funds/<int:id>/<float:amount>', methods=['GET', 'POST'])
# def subtract_funds(id, amount):
    
#     user = User.query.get_or_404(id)
#     new_amount = user.balance - float(amount)

#     try:
#         user.balance = new_amount
#         db.session.commit()
#         flash('Success!', 'success')
#         return redirect(url_for('home'))

#     except Exception as e:
#             flash(f'Error: {str(e)}', 'error')
#             return redirect(url_for('home'))


#Stock
@app.route('/edit_stock/<string:name>/<float:price>/<int:quantity>/<int:id>')
def edit_stock(name, price, quantity, id):
    if not name or not price or not quantity:
        flash('Fill all fields!', 'error')
        return redirect(url_for('home'))
    
    stock = Stock.query.get_or_404(id)
    stock.name = name
    stock.price = price
    stock.quantity = quantity


    try:
        db.session.commit()
        flash(f'Stock {name} updated!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating stock: {str(e)}', 'error')

    return redirect(url_for('stocks'))

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
    return redirect(url_for('stocks'))


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
    order = Order.query.get_or_404(id)
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


if __name__ == '__main__':
    app.run(debug=True)

#testing git branch
#AHHHHHHHHHHHHHHHHHHHHHHHHHHH 