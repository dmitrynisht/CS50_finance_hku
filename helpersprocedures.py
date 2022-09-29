def stmt_plpgsql_recieve_kwargs_v1():
    """LANGUAGE plpgsql;
    plpgsql_recieve_kwargs_v1 is testing function.
    I'm testing passing parameters to request.
    I'm passing to request two parameters and receiving in response a table.
    """

    # =========================================================================
    # Version 1.
    # Verbose. More appropriate for complicated requests.
    # Several rows in resulting table could be expected.
    
    stmt = """
    CREATE OR REPLACE FUNCTION plpgsql_recieve_kwargs_v1(kwarg1 text, kwarg2 text)
    RETURNS TABLE (f1name text, f1val text, f2name text, f2val text) AS
    $any-tag can_be_used$
        --one string comment--
        /*multi
        string comment*/
        <<filter>>
        DECLARE
            kwarg1 ALIAS FOR plpgsql_recieve_kwargs_v1.kwarg1;
            kwarg2 ALIAS FOR plpgsql_recieve_kwargs_v1.kwarg2;
        BEGIN
            RETURN QUERY SELECT
                            'kwarg1 val' AS f1name,
                            filter.kwarg1 AS f1val,
                            'kwarg2 val' AS f2name,
                            filter.kwarg2 AS f2val;
        END filter;
    $any-tag can_be_used$
    LANGUAGE plpgsql;
    """
    return stmt


def stmt_sql_recieve_kwargs_v2():
    """LANGUAGE SQL;
    sql_recieve_kwargs_v2 is testing function.
    I'm testing passing parameters to request.
    I'm passing to request two parameters and receiving in response one string.
    """

    # =========================================================================
    # Version 2.
    # Using IN, OUT, INOUT parameters.
    
    stmt = """
    CREATE OR REPLACE FUNCTION sql_recieve_kwargs_v2(INOUT kwarg1 text, OUT f1name text, INOUT kwarg2 text, OUT f2name text) AS
    $$
        SELECT
            kwarg1,
            'kwarg1 val',
            kwarg2,
            'kwarg2 val';
    $$
    LANGUAGE SQL;
    """
    return stmt


def stmt_sql_get_user():
    """LANGUAGE SQL;
    """

    stmt = """
    CREATE OR REPLACE FUNCTION sql_get_user(usr_name_in text)
    RETURNS TABLE (id bigint, username text, hash text, cash float)
    AS $$
        SELECT
            users.id,
            users.username,
            users.hash,
            users.cash
        FROM users 
        WHERE username = usr_name_in;
    $$
    LANGUAGE SQL;
    """

    return stmt


def stmt_sql_func_insert_user():
    """LANGUAGE SQL;
    """
    
    stmt = """
    CREATE OR REPLACE FUNCTION sql_insert_user(usr_name_in text, usr_hash_in text)
    RETURNS TABLE (id bigint, username text)
    AS $$
        INSERT INTO users (username, hash) VALUES (usr_name_in, usr_hash_in)
            RETURNING users.id, users.username;
    $$
    LANGUAGE SQL;
    """
    return stmt


def stmt_sql_get_portfolio():
    """LANGUAGE SQL;
    
    Summarizing, for the user currently logged in, which stocks the user owns.
        expected keyword arguments:
            dont_filter_by_symbol: True/False/None, if empty regarded as True
            symbol: 'string', when dont_filter_by_symbol is False, otherwise regarded as empty string

        In other words, to filter portfolio by some symbol we might call this function as following:
            get_portfolio(dont_filter_by_symbol=False, symbol='AAPL')
    """

    stmt = """
    CREATE OR REPLACE FUNCTION sql_portfolio(usr_id_in bigint, dont_filter_by_symbol boolean DEFAULT TRUE, symbol_in text DEFAULT '')
    RETURNS TABLE (symbol text, name text, shares bigint)
    AS $$
    WITH
        filter (user_id, dont_filter_by_symbol, symbol) AS (
            VALUES
                (usr_id_in::bigint, dont_filter_by_symbol::boolean, symbol_in::text)
        )
    SELECT
        UPPER(hist.symbol) AS symbol,
        hist.name,
        SUM(hist.shares) AS shares
    FROM history AS hist
    INNER JOIN filter
    USING (user_id)
    WHERE (filter.dont_filter_by_symbol
        OR (hist.symbol = filter.symbol))
    GROUP BY
        hist.symbol,
        hist.name
    HAVING SUM(shares) > 0
    ORDER BY
        symbol ASC
    $$
    LANGUAGE SQL;
    """

    return stmt


def stmt_sql_balance_with_prices():
    """LANGUAGE SQL;
    """

    stmt = """
    CREATE OR REPLACE FUNCTION sql_balance_with_prices(usr_id_in bigint, dont_filter_by_symbol boolean DEFAULT TRUE, symbol_in text DEFAULT '')
    RETURNS TABLE (symbol text, name text, shares bigint, price_bought float, date_bought timestamp with time zone)
    AS $$
    WITH
        filter (user_id, dont_filter_by_symbol, symbol) AS (
            VALUES
                (usr_id_in::bigint, dont_filter_by_symbol::boolean, symbol_in::text)
        )
    SELECT
        hist.symbol,
        hist.name,
        SUM(hist.shares) AS shares,
        hist.price_bought,
        hist.date_bought
    FROM history AS hist
    INNER JOIN filter
    USING (user_id)
    WHERE (filter.dont_filter_by_symbol
        OR (hist.symbol = filter.symbol))
    GROUP BY
        hist.symbol,
        hist.name,
        hist.price_bought,
        hist.date_bought
    HAVING SUM(shares) > 0
    ORDER BY
        hist.symbol ASC,
        hist.date_bought ASC
    $$
    LANGUAGE SQL;
    """

    return stmt


def stmt_sql_get_portfolio_with_prices():
    """LANGUAGE SQL;
    """

    stmt = """
    CREATE OR REPLACE FUNCTION sql_portfolio_with_prices(usr_id_in bigint, dont_filter_by_symbol boolean DEFAULT TRUE, symbol_in text DEFAULT '')
    RETURNS TABLE (symbol text, name text, shares bigint, price_bought float)
    AS $$
    WITH
        filter (user_id, dont_filter_by_symbol, symbol) AS (
            VALUES
                (usr_id_in::bigint, dont_filter_by_symbol::boolean, symbol_in::text)
        )
    SELECT
        UPPER(last_date.symbol) AS symbol,
        last_date.name,	
        last_date.shares,
        last_date.price_bought
    FROM (
            SELECT
                hist2.user_id,
                hist2.symbol,
                hist2.name,
                hist2.price_bought,
                SUM(hist2.shares) OVER w_last_bought AS shares,
                hist2.date_bought AS date_bought,
                MAX(hist2.date_bought) OVER w_last_bought AS max_date_bought
            FROM history AS hist2
            INNER JOIN filter
            USING (user_id)
            WHERE (filter.dont_filter_by_symbol
                OR (hist2.symbol = filter.symbol))
            WINDOW
                w_last_bought AS (
                    PARTITION BY 
                        hist2.user_id,
                        hist2.symbol,
                        hist2.name
                )
        ) AS last_date
    WHERE
        last_date.date_bought = last_date.max_date_bought
        AND last_date.shares > 0
    ORDER BY
        symbol ASC
    $$
    LANGUAGE SQL;
    """

    return stmt


def stmt_sql_get_history():
    """LANGUAGE SQL;
    """

    stmt = """
    CREATE OR REPLACE FUNCTION sql_get_history(usr_id_in bigint)
    RETURNS TABLE (transacted TIMESTAMP, symbol TEXT, shares bigint, price FLOAT, total FLOAT, price_bought FLOAT, date_bought TIMESTAMP, name TEXT)
    AS $$
        SELECT
            transacted,
            symbol,
            shares,
            price,
            total,
            price_bought,
            date_bought,
            name
        FROM history
        WHERE user_id = usr_id_in
        ORDER BY
            transacted DESC,
            symbol;
    $$
    LANGUAGE SQL;
    """

    return stmt


def stmt_sql_func_insert_history():
    stmt = """
    CREATE OR REPLACE FUNCTION sql_insert_history(user_id_in bigint, transacted_in timestamp with time zone, symbol_in text, name_in text, shares_in bigint, price_in numeric, total_in numeric, price_bought_in numeric, date_bought_in timestamp with time zone)
    RETURNS TABLE (user_id bigint, transacted timestamp with time zone, symbol text, name text, shares bigint, price numeric, total numeric, price_bought numeric, date_bought timestamp with time zone)
    AS $$
        INSERT INTO history (user_id, transacted, symbol, name, shares, price, total, price_bought, date_bought) VALUES (user_id_in, transacted_in, symbol_in, name_in, shares_in, price_in, total_in, price_bought_in, date_bought_in)
            RETURNING user_id, transacted, symbol, name, shares, price, total, price_bought, date_bought;
    $$
    LANGUAGE SQL;
    """

    return stmt


def stmt_sql_upd_user():
    stmt = """
    CREATE OR REPLACE FUNCTION sql_user_upd(usr_name_in text, cash_delta_in float DEFAULT 0)
    RETURNS TABLE (user_id bigint, username text, cash float)
    AS $$
        UPDATE users
            SET cash = cash - cash_delta_in
            WHERE username = usr_name_in
            RETURNING id, username, cash;
    $$
    LANGUAGE SQL;
    """

    return stmt


#--------ARCHIVE------------------------------------------------
################################################################
#---------------------------------------------------------------
