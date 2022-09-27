import os
import requests
requests.adapters.DEFAULT_RETRIES = 3 # increase retries number
import urllib.parse

from flask import redirect, render_template, session
from functools import wraps

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        url = f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}"
        # report_variables(
        #     'stock request ',
        #     [url],
        # )
        response = requests.get(url, timeout=5)
        response.raise_for_status()
    except requests.RequestException as var_error:
        report_variables(
            'stock request ERROR',
            [var_error.strerror],
        )
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def sandbox_lookup(symbol):
    """Look up quote for single symbol."""

    api_key = os.environ.get("API_KEY")
    response = None
    url = ""
    error_msg = ""

    if api_key == None:
        error_msg = "API_KEY missing!"
        return response, url, error_msg

    stmt_url = 'https://sandbox.iexapis.com/stable/stock/'
    stmt_url_symb = f"{urllib.parse.quote_plus(symbol)}"
    stmt_url_type = '/quote?'
    stmt_url_token = f"token={api_key}"

    # stmt_url += stmt_url_symb + stmt_url_type + stmt_url_filter + stmt_url_token #
    url = f"{stmt_url}{stmt_url_symb}{stmt_url_type}{stmt_url_token}"

    # Contact API
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        response = None
        error_msg = "Wrong URL"
        return response, url, error_msg

    # Parse response
    #
    try:
        quote = response.json()

        # # Printing report №
        # report_variables(__name__, ["=======quote=data======="], [quote])

        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }, url, error_msg

    except (KeyError, TypeError, ValueError):
        response = None
        error_msg = "Wrong response processing!"
        return response, url, error_msg


def usd(value):
    """Format value as USD."""
    if f"${value:,.2f}" == "$0.00":
        return f"${value:,.5f}"
    return f"${value:,.2f}"


def report_variables(*args):
    """Printing pasted args"""
    print("###########################################")
    print("#######-report-№-", args[0], "-start-######")
    print(*args[1:], sep='\n')
    print("#######-end-№-", args[0], "-########")

    pass


def mkappdir():
    # creating session tempdir
    # Configure session to use filesystem (instead of signed cookies)
    from tempfile import gettempdir, mkdtemp
    import os
    
    # """A bytes version of tempfile.gettempdir()."""
    # from tempfile import gettempdirb
    # app_dir = os.fsencode("CS50_finance")
    # tmp_dir = gettempdirb()
    # dir = os.path.join(tmp_dir, app_dir)
    # try:
    #     os.mkdir(dir, 0o700)
    # except FileExistsError:
    #     pass # already exists
    
    # return os.fsdecode(mkdtemp(dir=dir))
    
    # Custom behaviour for mkdtemp()
    # return mkdtemp()

    app_dir = 'CS50_finance'
    tmp_dir = gettempdir()
    dir = os.path.join(tmp_dir, app_dir)
    try:
        os.mkdir(dir, 0o700)
    except FileExistsError:
        pass # already exists

    app_dir_prefix = 'cs50_'
    app_dir_suffix = ''
    return mkdtemp(prefix=app_dir_prefix, suffix=app_dir_suffix, dir=dir)