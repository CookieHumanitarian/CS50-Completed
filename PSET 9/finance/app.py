import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    id = db.execute("SELECT id FROM users WHERE id = ?", session["user_id"])
    id = id[0]["id"]
    rows = db.execute("SELECT * FROM purchases WHERE user_id = ?", session["user_id"])
    prices = {}
    total = {}
    name = {}
    sum = 0

    for row in rows:
        output1 = lookup(row["symbol"])
        prices[row["symbol"]] = output1["price"]
        total[row["symbol"]] = float(output1["price"]) * float(row["shares"])
        name[row["symbol"]] = output1["name"]
        sum += float(output1["price"]) * float(row["shares"])

    new_balance = db.execute("SELECT cash FROM users WHERE id = ?", id)
    cash = float(new_balance[0]["cash"])

    # I will get name, price and symbol from lookup
    return render_template(
        "index.html",
        rows=rows,
        name=name,
        prices=prices,
        total=total,
        sum=sum,
        cash=cash,
    )


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        input = request.form.get("symbol")
        shares = request.form.get("shares")
        id = session["user_id"]
        symbol = lookup(input)
        if len(input) == 0:
            return apology("Blank input", 400)
        if symbol == None:
            return apology("Symbol not found", 400)

        symbol_sign = symbol["symbol"]

        check_input = lookup(input)
        if check_input == None:
            return apology("Invalid input")
        try:
            shares = int(shares)
        except ValueError:
            return apology("Shares not found", 400)
        if shares <= 0:
            return apology("Invalid Shares", 400)

        id = session["user_id"]

        temp = symbol["price"]
        price = float(temp)
        balance = db.execute("SELECT cash FROM users WHERE id = ?", id)
        balance = balance[0]["cash"]
        now = datetime.now()
        time = now.strftime("%d/%m/%Y %H:%M:%S")
        transaction_type = "buy"

        if int(balance) < (int(price) * shares):
            return apology("Not enough cash at the current price", 400)

        array1 = db.execute("SELECT symbol FROM purchases WHERE user_id = ?", id)

        for s in array1:
            if symbol_sign == str(s["symbol"]):
                old_shares = db.execute(
                    "SELECT shares FROM purchases WHERE user_id = ? AND symbol = ?",
                    id,
                    symbol_sign,
                )
                number = int(shares) + int(old_shares[0]["shares"])
                db.execute(
                    "UPDATE purchases SET shares = ? WHERE user_id = ? AND symbol = ?",
                    number,
                    id,
                    symbol_sign,
                )
                new_balance = int(balance) - (int(price) * shares)
                db.execute("UPDATE users SET cash = ? WHERE id = ?", new_balance, id)
                rows = db.execute(
                    "SELECT * FROM purchases WHERE user_id = ?", session["user_id"]
                )
                prices = {}
                total = {}
                name = {}
                sum = 0
                for row in rows:
                    output1 = lookup(row["symbol"])
                    prices[row["symbol"]] = output1["price"]
                    total[row["symbol"]] = float(output1["price"]) * float(
                        row["shares"]
                    )
                    name[row["symbol"]] = output1["name"]
                    sum += float(output1["price"]) * float(row["shares"])
                    db.execute(
                        "INSERT INTO stocks(id, price, shares, time, type, symbol) VALUES(?,?,?,?,?,?)",
                        id,
                        price,
                        shares,
                        time,
                        transaction_type,
                        input.upper(),
                    )

                new_balance = db.execute("SELECT cash FROM users WHERE id = ?", id)
                cash = float(new_balance[0]["cash"])
                return render_template(
                    "index.html",
                    rows=rows,
                    name=name,
                    prices=prices,
                    total=total,
                    sum=sum,
                    cash=cash,
                )

        db.execute(
            "INSERT INTO purchases(user_id, price, shares, time, type, symbol) VALUES(?,?,?,?,?,?)",
            id,
            price,
            shares,
            time,
            transaction_type,
            input.upper(),
        )
        db.execute(
            "INSERT INTO stocks(id, price, shares, time, type, symbol) VALUES(?,?,?,?,?,?)",
            id,
            price,
            shares,
            time,
            transaction_type,
            input.upper(),
        )
        new_balance = int(balance) - (int(price) * shares)
        db.execute("UPDATE users SET cash = ? WHERE id = ?", new_balance, id)

        rows = db.execute(
            "SELECT * FROM purchases WHERE user_id = ?", session["user_id"]
        )
        prices = {}
        total = {}
        name = {}
        sum = 0

        for row in rows:
            output1 = lookup(row["symbol"])
            prices[row["symbol"]] = output1["price"]
            total[row["symbol"]] = float(output1["price"]) * float(row["shares"])
            name[row["symbol"]] = output1["name"]
            sum += float(output1["price"]) * float(row["shares"])

        new_balance = db.execute("SELECT cash FROM users WHERE id = ?", id)
        cash = float(new_balance[0]["cash"])

        # I will get name, price and symbol from lookup
        return render_template(
            "index.html",
            rows=rows,
            name=name,
            prices=prices,
            total=total,
            sum=sum,
            cash=cash,
        )

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    id = session["user_id"]
    rows = db.execute("SELECT * FROM stocks WHERE id = ?", id)

    type = {}

    for row in rows:
        temp = row["type"]
        type[row["type"]] = temp.capitalize()

    return render_template("history.html", rows=rows, type=type)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        list = lookup(symbol)
        if list == None:
            return apology("Invalid symbol")

        name = list["name"]
        symbol = list["symbol"]
        temp = list["price"]
        price = float(temp)
        return render_template("quoted.html", name=name, symbol=symbol, price=price)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password_register = request.form.get("password")
        password_confirmation = request.form.get("confirmation")

        if (
            password_register != password_confirmation
            or len(password_register) == 0
            or len(username) == 0
        ):
            flash("Invalid password or username")
            return apology("Invalid password or username", 400)

        rows = db.execute("SELECT * FROM users WHERE username LIKE ?", username)
        if len(rows) != 0:
            return apology("Username already taken")

        amount = 10000
        hash = generate_password_hash(password_register)
        db.execute(
            "INSERT INTO users(username, hash, cash) VALUES(?, ?,?)",
            username,
            hash,
            amount,
        )
        flash("Sucessfully")
        return render_template("login.html")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        input = request.form.get("symbol")
        number_sold = request.form.get("shares")
        id = session["user_id"]

        if len(input) == 0:
            return apology("Blank input", 400)
        try:
            if int(number_sold) < 0:
                return apology("Invalid number of shares", 400)
        except ValueError:
            return apology("Blank shares", 400)

        stocks = db.execute("SELECT * FROM purchases WHERE user_id = ?", id)

        for s in stocks:
            if input == s["symbol"]:
                if int(number_sold) <= int(s["shares"]):
                    flash("Successfully sold stock")
                    # MINUS CASH AND REMOVE STOCK FROM PORTFOLIO IF THE SHARES == 0
                    rows = db.execute(
                        "SELECT * FROM purchases WHERE user_id = ?", session["user_id"]
                    )
                    prices = {}
                    total = {}
                    name = {}
                    sum = 0
                    # for row in rows:
                    # input = symbol
                    # number_sold = shares wanna sold
                    for row in rows:
                        if input == row["symbol"]:
                            new_shares = row["shares"] - int(number_sold)
                            db.execute(
                                "UPDATE purchases SET shares = ? WHERE user_id = ? AND symbol = ?",
                                new_shares,
                                id,
                                input,
                            )
                            delete_value = 0
                            db.execute(
                                "DELETE FROM purchases WHERE shares = ?", delete_value
                            )

                    updated = db.execute(
                        "SELECT * FROM purchases WHERE user_id = ?", id
                    )

                    # to get how much money user made
                    placeholder = lookup(input)
                    cost = placeholder["price"]
                    money_made = int(cost) * int(number_sold)
                    now = datetime.now()
                    time = now.strftime("%d/%m/%Y %H:%M:%S")
                    transaction_type = "Sell"

                    for row in updated:
                        output1 = lookup(row["symbol"])
                        prices[row["symbol"]] = output1["price"]
                        total[row["symbol"]] = float(output1["price"]) * float(
                            row["shares"]
                        )
                        name[row["symbol"]] = output1["name"]
                        sum += float(output1["price"]) * float(row["shares"])
                    # I will get name, price and symbol from lookup
                    new_balance = db.execute("SELECT cash FROM users WHERE id = ?", id)
                    cash = float(new_balance[0]["cash"]) + float(money_made)
                    db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, id)
                    db.execute(
                        "INSERT INTO stocks(id, price, shares, time, type, symbol) VALUES(?,?,?,?,?,?)",
                        id,
                        output1["price"],
                        number_sold,
                        time,
                        transaction_type,
                        input.upper(),
                    )
                    return render_template(
                        "index.html",
                        rows=updated,
                        name=name,
                        prices=prices,
                        total=total,
                        sum=sum,
                        cash=cash,
                    )

        return apology("stock or invalid number of shares", 400)

    else:
        delete_value = 0
        db.execute("DELETE FROM purchases WHERE shares = ?", delete_value)
        rows = db.execute(
            "SELECT * FROM purchases WHERE user_id = ?", session["user_id"]
        )
        return render_template("sell.html", rows=rows)


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change():
    return render_template("change_password.html")
