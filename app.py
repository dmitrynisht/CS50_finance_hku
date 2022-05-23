import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime as dt, timezone

from helpers import apology, login_required, lookup, usd, sandbox_lookup, report_variables

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
# + deploying to Heroku. Still using CS50 SQL library, but connecting to PostgeSQL instead of SQLite
# db = SQL("sqlite:///finance.db")
uri = os.getenv("DATABASE_URL")
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://")
db = SQL(uri)
# - deploying to Heroku

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    
    portfolio = get_portfolio_with_prices()
    return apology(f"Portfolio {portfolio}", 400)
    # Printing report №
    report_variables(
        'portfolio',
        *portfolio,
        ['type of portfolio: ', type(portfolio)],
    )

    stock_total = 0
    if portfolio:
        for stock in portfolio:
            # response, msg_url, error_msg = sandbox_lookup(stock['symbol'])
            response = lookup(stock['symbol'])

            # # Printing report №
            # report_variables(
            #   stock['symbol'],
            #   [stock['price']],
            #   [response['price']],
            # )

            stock['price'] = response['price']
            stock['total'] = response['price'] * stock['shares']
            stock_total += stock['total']

    rows = get_user(username=session["username"])
    if len(rows) == 0:
        # Redirect user to home page
        return redirect(url_for(".logout"), code=400)

    cash = rows[0]["cash"]
    total = stock_total + cash

    return render_template("index.html", portfolio=portfolio, cash=cash, total=total)


@app.route("/stocks", methods=["GET", "POST"])
@login_required
def top_stocks():
    """List of top stocks"""

    stmt = 'top stocks are coming soon!'
    # stmt='https://sandbox.iexapis.com/stable/tops?token=Tpk_7a91d97de0a341a3be6115e86011a1ff'

    flash(stmt)

    return render_template("stocks.html", name=request.args.get("name", "name-world"))


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    s_action = request.form.get("quoteMode") or "/quote"

    # # Printing report №
    # report_variables(
    #     "QUOTE MODE",
    #     ["quoteMode:", s_action],
    #     ["request.method:", request.method],
    # )

    if request.method == "POST":

        symbol = request.form.get("symbol")

        # redirect to /buy after correct quoting and clicking the "buy" button
        if s_action == "/buy":
            return redirect(url_for("buy", symbol=symbol, s_action=s_action))

        if not symbol:
            return apology("Invalid symbol!", 400)

        msg_symbol = "Just quoted for: " + symbol
        sandbox_mode = False

        if sandbox_mode == False:
            response = lookup(symbol)
            if response is None:
                return apology("invalid symbol", 400)

        elif sandbox_mode == True:
            # testing sanbox_lookup() function
            error_msg = ""

            # # Printing report №
            # report_variables(__name__, ["calling sandbox_lookup() via /quote"])

            response, msg_url, error_msg = sandbox_lookup(symbol)

            if response is None:
                flash(error_msg)
                return apology("invalid symbol", 400)

        # flash(msg_symbol)
        # flash(msg_url)
        # flash(response)

        # report_variables(
        #     "QUOTE METHOD POST",
        #     ["s_action:", s_action],
        #     ["request.method:", request.method],
        #     # ["msg_url:", msg_url],
        # )

        return render_template("quote.html", symbol=request.form.get("symbol", symbol), stock=response, s_action=s_action)

    else:
        # User reached route via GET
        return render_template("quote.html", s_action=request.args.get("s_action", s_action))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    s_action = "/buy"

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        # # Printing report №
        # report_variables(
        #     "NUMBER OF SHARES TESTING",
        #     ["symbol:", symbol],
        #     ["shares:", shares],
        #     ["type of shares:", type(shares)],
        # )

        if not symbol:
            return apology("Invalid symbol!", 400)

        if not symbol.isalpha():
            return apology("Invalid symbol!", 400)

        if not shares:
            return apology("Shares required as positive INTEGER!", 400)

        if shares.isdecimal():
            shares = float(shares)
        else:
            return apology("Shares required as positive INTEGER!", 400)

        if shares == int(shares):
            shares = int(shares)
        else:
            return apology("Shares required as positive INTEGER!", 400)

        if shares < 1:
            return apology("Shares required as positive INTEGER!", 400)

        # # Printing report №
        # report_variables(
        #     "NUMBER OF SHARES UPDATING",
        #     ["symbol:", symbol],
        #     ["shares:", shares],
        #     ["type of shares:", type(shares)],
        # )

        transaction_data = buy_stocks(symbol=symbol, shares=shares, method=request.method)
        if not transaction_data["trn_complete"]:
            trn_msg = transaction_data["trn_msg"] if "trn_msg" in transaction_data else "Invalid symbol!"
            return apology(trn_msg, 400)

        # Reporting results
        return redirect("/")

    else:

        symbol = request.args.get("symbol")
        # # Printing report №
        # report_variables(
        #   "BUY GET",
        #   ["symbol:", symbol],
        # )

        return render_template("buy.html", symbol=request.args.get("symbol", symbol), s_action=request.args.get("s_action", s_action))


@app.route("/index_buy")
def index_buy():
    """
    expected args:
    symbol              - symbol beeing bought;
    i_shares            - number of shares beeing bought;
    stock_shares        - total number of shares of symbol before i_shares beeing bought;
    stock_total_before  - total cost of stock_shares before i_shares beeing bought;
    total               - total cost of shares of all symbols before i_shares beeing bought;
    """

    symbol = request.args.get("symbol")
    i_shares = request.args.get("i_shares") or 0
    stock_shares = request.args.get("stock_shares") or 0
    stock_shares = int(stock_shares)
    stock_total_before = request.args.get("stock_total") or 0
    stock_total_before = round(float(stock_total_before), 4)
    total = request.args.get("total") or 0
    total = round(float(total), 4)

    # # Printing report №
    # report_variables(
    #     "index_buy TESTING: data recieved",
    #     ["method:",             request.method],
    #     ["symbol:",             symbol],
    #     ["stock_shares:",       stock_shares],
    #     ["i_shares:",           i_shares],
    #     ["stock_total_before:", stock_total_before],
    #     ["total:",              total],
    # )

    # Providing some tests before transacting
    if not symbol:
        return {
            'trn_complete': False,
            'trn_msg': 'Invalid symbol!',
        }

    if not i_shares:
        return {
            'trn_complete': False,
            'trn_msg': 'Shares required as positive INTEGER!',
        }

    if i_shares.isdecimal():
        i_shares = float(i_shares)
    else:
        return {
            'trn_complete': False,
            'trn_msg': 'Shares required as positive INTEGER!',
        }

    if i_shares == int(i_shares):
        i_shares = int(i_shares)
    else:
        return {
            'trn_complete': False,
            'trn_msg': 'Shares required as positive INTEGER!',
        }

    if i_shares < 1:
        return {
            'trn_complete': False,
            'trn_msg': 'Shares required as positive INTEGER!',
        }

    # Commiting transaction
    transaction_data = buy_stocks(symbol=symbol, shares=i_shares, method=request.method)
    if not transaction_data["trn_complete"]:
        trn_msg = transaction_data["trn_msg"] if "trn_msg" in transaction_data else "Invalid symbol!"
        stock_data = {
            'trn_complete': False,
            'trn_msg': trn_msg,
        }
        return stock_data

    cash_balance = transaction_data["cash"]
    cash_delta = transaction_data["cash_delta"]
    stock_shares += i_shares
    stock_total_balance = round(transaction_data["price"] * stock_shares, 4)
    stock_total_delta = stock_total_balance - stock_total_before
    total = round(total + (cash_delta + stock_total_delta), 4)

    # # Printing report №
    # report_variables(
    #     "TOTAL_BUY_transaction TESTING",
    #     ['cash_delta', cash_delta],
    #     ['cash_delta type', type(cash_delta)],
    #     ['price', transaction_data["price"]],
    #     ['price type', type(transaction_data["price"])],
    #     ['stock_shares', stock_shares],
    #     ['stock_shares type', type(stock_shares)],
    #     ['stock_total_balance', stock_total_balance],
    #     ['stock_total_balance type', type(stock_total_balance)],
    #     ['stock_total_delta', stock_total_delta],
    #     ['stock_total_delta type', type(stock_total_delta)],
    #     ['total', total],
    #     ['total type', type(total)],
    # )

    stock_data = {
        'trn_complete': True,
        'price':        transaction_data["price"],
        'shares':       stock_shares,
        'stock_total':  stock_total_balance,
        'cash':         cash_balance,
        'total':        total,
    }

    return stock_data


def buy_stocks(*, symbol, shares, method):
    """"""

    symbol = symbol.lower()

    # Final quote before commiting transaction
    quote = lookup(symbol)

    # # Printing report №
    # report_variables(
    #     "buy_stocks quote TESTING",
    #     ["quote:", quote],
    #     # ["msg_url:", msg_url],
    #     # ["error_msg:", error_msg],
    #     ["method:", method],
    # )

    if not quote:
        transaction_data = {
            'trn_complete': False,
        }
        return transaction_data

    # Lets check how much cash the user currently has
    cash_rows = get_user(username=session["username"])
    if len(cash_rows) == 0:
        # Redirect user to home page
        transaction_data = {
            'trn_complete': False,
            'trn_msg': 'Your session has expired! Log in again please.',
            'trn_logout': True,
        }
        return transaction_data

    # It seems like data is correct. lets collect all the data into dict
    cash = cash_rows[0]["cash"]
    transacted = dt.now(timezone.utc).isoformat()
    name = quote["name"]
    price = float(quote["price"])
    total = price * shares

    if cash < total:
        transaction_data = {
            'trn_complete': False,
            'trn_msg': f"Not enough cash of {usd(cash)} to commit transaction of total {usd(total)}",
        }
        return transaction_data

    transaction_data = {
        "user_id": session["user_id"],
        "transacted": transacted,
        "symbol": symbol,
        "name": name,
        "shares": shares,
        "price": price,
        "total": total,
        "cash": cash,
        "price_bought": price,
        "date_bought": transacted,
        "transaction_type": "shares bought",
    }

    # Adding data
    try:
        # Commiting transaction
        commit_transaction(transaction_data=transaction_data)

    except:
        # Printing report №
        report_variables(
            "PURCHASE HANDLING",
            ["AN ERROR OCCURED WHILE EXECUTING TRANSACTION"],
        )
        transaction_data = {
            'trn_complete': False,
            'trn_msg': 'AN ERROR OCCURED WHILE EXECUTING TRANSACTION',
        }
        return transaction_data

    transaction_data["trn_complete"] = True
    transaction_data["cash_delta"] = -total
    transaction_data["cash"] -= total
    transaction_data["cash"] = round(transaction_data["cash"], 4)

    return transaction_data


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    s_action = "/sell"

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        # # Printing report №
        # report_variables("NUMBER OF SHARES TESTING",
        # ["symbol:", symbol],
        # ["shares:", shares],
        # )

        if not symbol:
            return apology("Invalid symbol!", 400)

        if not symbol.isalpha():
            return apology("Invalid symbol!", 400)

        if not shares:
            return apology("Shares required as positive INTEGER!", 400)

        if shares.isdecimal():
            shares = float(shares)
        else:
            return apology("Shares required as positive INTEGER!", 400)

        if shares == int(shares):
            shares = int(shares)
        else:
            return apology("Shares required as positive INTEGER!", 400)

        if shares < 1:
            return apology("Shares required as positive INTEGER!", 400)

        transaction_data = sell_stocks(symbol=symbol, shares=shares, method=request.method)
        if not transaction_data["trn_complete"]:
            trn_msg = transaction_data["trn_msg"] if "trn_msg" in transaction_data else "Invalid symbol!"
            return apology(trn_msg, 400)

        # Reporting results
        return redirect("/")

    else:

        portfolio = get_portfolio()
        symbol_selected = request.args.get("symbol_selected")

        # # Printing report №
        # report_variables(
        #   "VIEW REQUEST SUCCESS",
        #   ["ROWS:", portfolio],
        # )

        return render_template("sell.html", symbols=portfolio, s_action=request.args.get("s_action", s_action), symbol_selected=request.args.get("symbol_selected", symbol_selected))


@app.route("/index_sell")
def index_sell():
    """
    expected args:
    symbol              - symbol beeing sold;
    i_shares            - number of shares beeing sold;
    stock_shares        - total number of shares of symbol before i_shares beeing sold;
    stock_total_before  - total cost of stock_shares before i_shares beeing sold;
    total               - total cost of shares of all symbols before i_shares beeing sold;
    """

    symbol = request.args.get("symbol")
    i_shares = request.args.get("i_shares") or 0
    stock_shares = request.args.get("stock_shares") or 0
    stock_shares = int(stock_shares)
    stock_total_before = request.args.get("stock_total") or 0
    stock_total_before = round(float(stock_total_before), 4)
    total = request.args.get("total") or 0
    total = round(float(total), 4)

    # # Printing report №
    # report_variables("index_sell TESTING: data recieved",
    # ["method:",             request.method],
    # ["symbol:",             symbol],
    # ["stock_shares:",       stock_shares],
    # ["i_shares:",           i_shares],
    # ["stock_total_before:", stock_total_before],
    # ["total:",              total],
    # )

    # Providing some tests before transacting
    if not symbol:
        return {
            'trn_complete': False,
            'trn_msg': 'Invalid symbol!',
        }

    if not i_shares:
        return {
            'trn_complete': False,
            'trn_msg': 'Shares required as positive INTEGER!',
        }

    if i_shares.isdecimal():
        i_shares = float(i_shares)
    else:
        return {
            'trn_complete': False,
            'trn_msg': 'Shares required as positive INTEGER!',
        }

    if i_shares == int(i_shares):
        i_shares = int(i_shares)
    else:
        return {
            'trn_complete': False,
            'trn_msg': 'Shares required as positive INTEGER!',
        }

    if i_shares < 1:
        return {
            'trn_complete': False,
            'trn_msg': 'Shares required as positive INTEGER!',
        }

    # Commiting transaction
    transaction_data = sell_stocks(symbol=symbol, shares=i_shares, method=request.method)
    if not transaction_data["trn_complete"]:
        trn_msg = transaction_data["trn_msg"] if "trn_msg" in transaction_data else "Invalid symbol!"
        stock_data = {
            'trn_complete': False,
            'trn_msg': trn_msg,
        }
        return stock_data

    cash_balance = transaction_data["cash"]
    cash_delta = transaction_data["cash_delta"]
    stock_shares -= i_shares
    stock_total_balance = round(transaction_data["stock_total_balance"], 4)
    stock_total_delta = stock_total_balance - stock_total_before

    # # Printing report №
    # report_variables(
    #     "TOTAL_SELL_transaction TESTING",
    #     ['cash_delta', cash_delta],
    #     ['cash_delta type', type(cash_delta)],
    #     ['stock_total_delta', stock_total_delta],
    #     ['stock_total_delta type', type(stock_total_delta)],
    #     ['total', total],
    #     ['total type', type(total)],
    # )

    total = round(total + (cash_delta + stock_total_delta), 4)

    stock_data = {
        'trn_complete': True,
        'price':        transaction_data["price"],
        'shares':       stock_shares,
        'stock_total':  stock_total_balance,
        'cash':         cash_balance,
        'total':        total,
    }

    return stock_data


def sell_stocks(*, symbol, shares, method):
    """"""

    symbol = symbol.lower()

    # Final quote before commiting transaction
    quote = lookup(symbol)

    if not quote:
        transaction_data = {
            'trn_complete': False,
        }
        return transaction_data

    # Lets check how much cash the user currently has
    cash_rows = get_user(username=session["username"])
    if len(cash_rows) == 0:
        # Redirect user to home page
        transaction_data = {
            'trn_complete': False,
            'trn_msg': 'Your session has expired! Log in again please.',
            'trn_logout': True,
        }
        return transaction_data

    # Making shure user have that many shares
    portfolio = get_portfolio(dont_filter_by_symbol=False, symbol=symbol)
    if portfolio[0]['shares'] < shares:
        transaction_data = {
            'trn_complete': False,
            'trn_msg': f"You dont own that many shares of {symbol}! Maximum is {portfolio[0]['shares']}",
        }
        return transaction_data

    # It seems like data is correct. lets collect all the data into dict
    cash = cash_rows[0]["cash"]
    transacted = dt.now(timezone.utc).isoformat()
    name = quote["name"]
    price = float(quote["price"])
    stock_total_balance = 0
    cash_delta = 0

    transaction_data = {
        "user_id": session["user_id"],
        "transacted": transacted,
        "symbol": symbol,
        "name": name,
        "price": price,
        "transaction_type": "shares sold",
        "cash": cash,
    }

    # lets collect all the data into dict
    balance_with_prices = get_balance_with_prices(dont_filter_by_symbol=False, symbol=symbol)
    for row in balance_with_prices:

        if shares <= 0:
            # updating stock_total only, no transactions needed
            if row["shares"] > 0:
                stock_total_balance += row["shares"] * price

            continue

        # negative "shares" as we selling them
        if row["shares"] < shares:
            transaction_data["shares"] = -row["shares"]
            shares -= row["shares"]
            row["shares"] = 0

        else:
            transaction_data["shares"] = -shares
            row["shares"] -= shares
            shares = 0
            # updating stock_total
            stock_total_balance += row["shares"] * price

        total = transaction_data["shares"] * price
        transaction_data["total"] = total
        transaction_data["price_bought"] = row["price_bought"]
        transaction_data["date_bought"] = row["date_bought"]

        # Adding transaction to database
        try:
            # Commiting transaction
            commit_transaction(transaction_data=transaction_data)
            transaction_data["cash"] = cash - total
            cash -= total
            cash_delta -= total

        except:
            # Printing report №
            report_variables(
                "SELL HANDLING",
                ["AN ERROR OCCURED WHILE EXECUTING TRANSACTION"],
            )
            transaction_data = {
                'trn_complete': False,
                'trn_msg': 'AN ERROR OCCURED WHILE EXECUTING TRANSACTION',
            }
            return transaction_data

    transaction_data["trn_complete"] = True
    transaction_data["stock_total_balance"] = stock_total_balance
    transaction_data["cash_delta"] = cash_delta
    transaction_data["cash"] = round(transaction_data["cash"], 4)

    return transaction_data


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    s_action = "/history"

    stmt = "SELECT *, datetime(transacted) AS dt FROM history WHERE user_id = ? ORDER BY transacted ASC"
    rows = db.execute(stmt, int(session["user_id"]))

    return render_template("history.html", history=rows, s_action=s_action)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    if 'user_id' in session:
        session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = get_user(username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]
        
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    # session.clear()

    # Redirect user to login form
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        # Ensure username was submitted
        username = request.form.get("username")
        if not username:
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure password was confirmed
        elif not request.form.get("confirmation"):
            return apology("must confirm password", 400)

        # Ensure password confirmed correctly
        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        # Query database for username
        rows = get_user(username=username)

        if len(rows) >= 1:
            # User already exists
            return apology(f"User {username} already exists!", 400)

        else:
            ins_stmt = "INSERT INTO users (username, hash) VALUES(?, ?)"
            user = db.execute(ins_stmt, username, generate_password_hash(request.form.get("password")))

            # Remember which user has logged in
            session["user_id"] = user
            session["username"] = username

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


def get_portfolio_with_prices(**kwargs):
    """
    """
    stmt_last_prices = ("""
    SELECT
        COALESCE(Null, 999) AS nonull
    """)
    rows = db.execute(
        stmt_last_prices)
    return rows
    # stmt_last_prices = ("""
    # SELECT
    #     UPPER(balance.symbol) AS symbol,
    #     balance.name,
    #     balance.shares
    # FROM
    #     (SELECT
    #         symbol,
    #         name,
    #         SUM(shares) AS shares
    #     FROM history AS hist1
    #     INNER JOIN
    #         (SELECT
    #             (:user_id) AS user_id,
    #             (:dont_filter_by_symbol) AS dont_filter_by_symbol,
    #             (:f_symbol) AS f_symbol) AS filter
    #     ON hist1.user_id = filter.user_id
    #     AND (filter.dont_filter_by_symbol
    #         OR (hist1.symbol = filter.f_symbol))
    #     GROUP BY hist1.symbol
    #     HAVING SUM(shares) > 0) AS balance
    # """)
    stmt_last_prices = ("""
        SELECT
            symbol,
            name,
            SUM(shares) AS shares
        FROM history AS hist1
        INNER JOIN
            (SELECT
                (:user_id) AS user_id,
                (:dont_filter_by_symbol) AS dont_filter_by_symbol,
                (:f_symbol) AS f_symbol) AS filter
        ON hist1.user_id = filter.user_id
    """)
    dont_filter_by_symbol = kwargs['dont_filter_by_symbol'] if ('dont_filter_by_symbol' in kwargs) else True
    symbol = '' if dont_filter_by_symbol else kwargs['symbol']
    rows = db.execute(
        stmt_last_prices, user_id=int(session["user_id"]), dont_filter_by_symbol=dont_filter_by_symbol, f_symbol=symbol)
    return rows
    
    stmt_last_prices = ("""
    SELECT
        UPPER(balance.symbol) AS symbol,
        balance.name,
        balance.shares,
        last_prices.price AS price_bought
    FROM
        (SELECT
            symbol,
            name,
            SUM(shares) AS shares
        FROM history AS hist1
        INNER JOIN
            (SELECT
                (:user_id) AS user_id,
                (:dont_filter_by_symbol) AS dont_filter_by_symbol,
                (:f_symbol) AS f_symbol) AS filter
        ON hist1.user_id = filter.user_id
        AND (filter.dont_filter_by_symbol
            OR (hist1.symbol = filter.f_symbol))
        GROUP BY hist1.symbol
        HAVING SUM(shares) > 0) AS balance
    INNER JOIN
        (SELECT
            symbol,
            name,
            price,
            MAX(date_bought) AS date_bought
        FROM history AS hist2
        INNER JOIN
            (SELECT
                (:user_id) AS user_id,
                (:dont_filter_by_symbol) AS dont_filter_by_symbol,
                (:f_symbol) AS f_symbol) AS filter
        ON hist2.user_id = filter.user_id
        AND (filter.dont_filter_by_symbol
            OR (hist2.symbol = filter.f_symbol))
        GROUP BY hist2.symbol
        HAVING SUM(shares) > 0
        ) AS last_prices
    ON balance.symbol = last_prices.symbol
    """)
    
    dont_filter_by_symbol = kwargs['dont_filter_by_symbol'] if ('dont_filter_by_symbol' in kwargs) else True
    symbol = '' if dont_filter_by_symbol else kwargs['symbol']
    
    # # Printing report №
    # report_variables(
    #     "get_portfolio checking",
    #     ["dont_filter_by_symbol:", dont_filter_by_symbol],
    #     ["dont_filter_by_symbol type:", type(dont_filter_by_symbol)],
    #     ["symbol:", symbol],
    #     ["symbol type:", type(symbol)],
    # )
    
    rows = db.execute(
        stmt_last_prices, user_id=int(session["user_id"]), dont_filter_by_symbol=dont_filter_by_symbol,
        f_symbol=symbol)
        # , user_id=int(session["user_id"]), dont_filter_by_symbol=dont_filter_by_symbol, f_symbol=symbol)

    return rows


def get_balance_with_prices(**kwargs):
    """
    """

    stmt_balance_with_prices = ("""
    SELECT
        symbol,
        name,
        SUM(shares) AS shares,
        price AS price_bought,
        date_bought
    FROM history AS history
    INNER JOIN
        (SELECT
            ? AS user_id,
            ? AS dont_filter_by_symbol,
            ? AS f_symbol) AS filter
    ON history.user_id = filter.user_id
    AND (filter.dont_filter_by_symbol
        OR (history.symbol = filter.f_symbol))
    GROUP BY
        history.symbol,
        history.date_bought
    HAVING SUM(shares) > 0
    ORDER BY
        symbol ASC,
        date_bought ASC
    """)

    dont_filter_by_symbol = kwargs['dont_filter_by_symbol'] if ('dont_filter_by_symbol' in kwargs) else True
    symbol = '' if dont_filter_by_symbol else kwargs['symbol']

    rows = db.execute(stmt_balance_with_prices, int(session["user_id"]), dont_filter_by_symbol, symbol)

    return rows


def get_portfolio(**kwargs):
    """
    Summarizing, for the user currently logged in, which stocks the user owns.
        expected keyword arguments:
            dont_filter_by_symbol: True/False/None, if empty regarded as True
            symbol: 'string', when dont_filter_by_symbol is False, otherwise regarded as empty string

        In other words, to filter portfolio by some symbol we might call this function as following:
            get_portfolio(dont_filter_by_symbol=False, symbol='AAPL')
    """

    stmt = ("""
    SELECT
        UPPER(symbol) AS symbol,
        name,
        SUM(shares) AS shares
    FROM history AS history
    INNER JOIN
        (SELECT
            ? AS user_id,
            ? AS dont_filter_by_symbol,
            ? AS f_symbol) AS filter
    ON history.user_id = filter.user_id
    AND (filter.dont_filter_by_symbol
        OR (history.symbol = filter.f_symbol))
    GROUP BY history.symbol
    HAVING SUM(shares) > 0
    ORDER BY
        symbol ASC
    """)

    dont_filter_by_symbol = kwargs['dont_filter_by_symbol'] if ('dont_filter_by_symbol' in kwargs) else True
    symbol = '' if dont_filter_by_symbol else kwargs['symbol']

    # # Printing report №
    # report_variables("get_portfolio checking",
    # ["dont_filter_by_symbol:", dont_filter_by_symbol],
    # ["dont_filter_by_symbol type:", type(dont_filter_by_symbol)],
    # ["symbol:", symbol],
    # ["symbol type:", type(symbol)],
    # )

    rows = db.execute(stmt, int(session["user_id"]), dont_filter_by_symbol, symbol)

    return rows


def get_user(*, username):
    """Search for user by username provided"""

    # # Named argument doesnt work. It seems like limitation of CS50
    # stmt = "SELECT * FROM users WHERE username=:username"
    # rows = db.execute(stmt, {"username": username})
    stmt = ("""
    SELECT
        *
    FROM users
    WHERE
        username = :username
    """)
    rows = db.execute(stmt, username=username)

    return rows


def commit_transaction(*, transaction_data):
    """
    """

    # Adding data into history table
    ins_stmt = ("INSERT INTO history (user_id, transacted, symbol, name, shares, price, total, price_bought, date_bought) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
    transaction_row = db.execute(
        ins_stmt,
        transaction_data["user_id"],
        transaction_data["transacted"],
        transaction_data["symbol"],
        transaction_data["name"],
        transaction_data["shares"],
        transaction_data["price"],
        transaction_data["total"],
        transaction_data["price_bought"],
        transaction_data["date_bought"])

    # Altering data into users table
    cash_left = transaction_data["cash"] - transaction_data["total"]
    stmt = "UPDATE users SET cash = ? WHERE username = ?"
    upd_row = db.execute(stmt, cash_left, session["username"])

    # # Printing report №
    # report_variables("TRANSACTION COMPLETE",
    # [transaction_data["transaction_type"], transaction_data["shares"]],
    # )

    pass


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
