def stmt_plpgsql_recieve_kwargs_v1():
    """LANGUAGE plpgsql;
    recieve_kwargs is testing function.
    I'm testing 'passing parameters to request' process.
    I'm passing to request two parameters and receiving in response one string.
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
            kwarg1 ALIAS FOR recieve_kwargs.kwarg1;
            kwarg2 ALIAS FOR recieve_kwargs.kwarg2;
        BEGIN
            RETURN QUERY SELECT
                            'kwarg1 val' AS f1name,
                            filter.kwarg1 AS f1val,
                            'kwarg2 val' AS f2name,
                            filter.kwarg2 AS f2val;
        END filter;
    $any-tag can_be_used$ LANGUAGE plpgsql;
    """
    return stmt


def stmt_sql_recieve_kwargs_v2():
    """LANGUAGE SQL;
    recieve_kwargs is testing function.
    I'm testing 'passing parameters to request' process.
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
    RETURNS TABLE (id integer, username text, hash text, cash float)
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
    RETURNS TABLE (id integer, usrename text)
    AS $$
        INSERT INTO users (username, hash) VALUES (usr_name_in, usr_hash_in)
            RETURNING users.id, users.username;
    $$
    LANGUAGE SQL;
    """
    return stmt


def stmt_sql_get_portfolio_with_prices():
    """LANGUAGE SQL;
    """

    stmt = """
    CREATE OR REPLACE FUNCTION sql_portfolio_with_prices(usr_id_in integer, dont_filter_by_symbol boolean DEFAULT TRUE, symbol_in text DEFAULT '')
    RETURNS TABLE (symbol text, name text, shares integer, price_bought float)
    AS $$
        WITH
            filter (user_id, dont_filter_by_symbol, symbol) AS (
                VALUES
                    (usr_id_in::integer, dont_filter_by_symbol::boolean, symbol_in::text)
            )
        SELECT
            UPPER(balance.symbol) AS symbol,
            balance.name,
            balance.shares,
            last_prices.price_bought AS price_bought
        FROM (
                SELECT
                    hist1.symbol,
                    hist1.name,
                    SUM(hist1.shares) AS shares
                FROM history AS hist1
                INNER JOIN filter
                USING (user_id)
                WHERE (filter.dont_filter_by_symbol
                    OR (hist1.symbol = filter.symbol))
                GROUP BY	
                    hist1.symbol,
                    hist1.name
                HAVING SUM(shares) > 0
            ) AS balance
        INNER JOIN (
                SELECT
                    hist3.symbol,
                    hist3.name,	
                    hist3.price_bought,
                    hist3.date_bought
                FROM (
                        SELECT
                            hist2.user_id,
                            hist2.symbol,
                            hist2.name,
                            MAX(hist2.date_bought) AS date_bought
                        FROM history AS hist2
                        INNER JOIN filter
                        USING (user_id)
                        WHERE (filter.dont_filter_by_symbol
                            OR (hist2.symbol = filter.symbol))
                        GROUP BY
                            hist2.user_id,
                            hist2.symbol,
                            hist2.name
                    ) AS last_date
                INNER JOIN history AS hist3
                USING (user_id, symbol)
                WHERE
                    hist3.transacted = last_date.date_bought
            ) AS last_prices
        USING (symbol)
    $$
    LANGUAGE SQL;
    """

    return stmt


def stmt_sql_get_history():
    """LANGUAGE SQL;
    """

    stmt = """
    CREATE OR REPLACE FUNCTION sql_get_history(usr_id_in INTEGER)
    RETURNS TABLE (transacted TIMESTAMP, symbol TEXT, shares INTEGER, price FLOAT, total FLOAT, price_bought FLOAT, date_bought TIMESTAMP, name TEXT)
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
            transacted ASC,
            symbol;
    $$
    LANGUAGE SQL;
    """

    return stmt


def stmt_sql_upd_user():
    stmt = """
    CREATE OR REPLACE FUNCTION sql_user_upd(usr_name text, cash_delta float DEFAULT 101)
    RETURNS TABLE (usr_id integer, usr_name text, usr_cash float)
    AS $$
        UPDATE users
            SET cash = cash + cash_delta
            WHERE username = usr_name;
        SELECT * FROM sql_get_user(usr_name);
    $$
    LANGUAGE SQL;
    """

    return stmt


#--------ARCHIVE------------------------------------------------
################################################################
#---------------------------------------------------------------


def stmt_plpgsql_proc_insert_user():
    """LANGUAGE plpgsql"""
    
    stmt = """
    CREATE OR REPLACE PROCEDURE plpgsql_insert_user(usr_name_in text)
    AS $$
        BEGIN
            INSERT INTO users (username) VALUES (usr_name_in);
            COMMIT;
        END;
    $$
    LANGUAGE plpgsql;
    """
    return stmt


def stmt_plpgsql_proc_add_user():
    """Execute first:
        stmt_plpgsql_proc_insert_user();
    """

    stmt = """
    DROP FUNCTION IF EXISTS plpgsql_proc_add_user(text);
    CREATE OR REPLACE FUNCTION plpgsql_proc_add_user(usr_name_in text, OUT usr_name text)
    AS $$
        BEGIN
            usr_name := usr_name_in;
            CALL plpgsql_insert_user(usr_name_in);
        END;
    $$ 
    LANGUAGE plpgsql;
    """
    return stmt


def stmt_sql_add_user():
    """Execute first:
        stmt_get_user();
    """

    stmt = """
    CREATE OR REPLACE FUNCTION sql_add_user(usr_name_in text)
    RETURNS TABLE (usr_id integer, usr_name text)
    AS $$
        INSERT INTO users (username) VALUES (usr_name_in);
        SELECT
            usr.usr_id,
            usr.usr_name
        FROM sql_get_user(usr_name_in) AS usr;
    $$ 
    LANGUAGE SQL;
    """

    # DROP FUNCTION IF EXISTS sql_add_user(text);        
    # CALL sql_insert_user(usr_name_in);
    # SELECT
    #     usr.usr_id
    # FROM sql_get_user(usr_name_in) AS usr

    # SELECT
    #     users.id
    # FROM users 
    # WHERE username = usr_name_in;

    # SELECT
    #     usr.usr_id
    # FROM get_user(usr_name_in) AS usr;

    return stmt


def stmt_sql_proc_add_user():
    """Execute first:
        stmt_sql_insert_user();
    """
    
    stmt = """
    CREATE OR REPLACE PROCEDURE sql_proc_add_user(usr_name_in text)
    AS $$
        CALL sql_insert_user(usr_name_in);
    $$ 
    LANGUAGE SQL;
    """
    return stmt


def stmt_sql_func_add_user():
    """Execute first:
        sql_proc_add_user();
        stmt_get_user();
    """

    stmt = """
    CREATE OR REPLACE FUNCTION sql_add_user(usr_name_in text)
    RETURNS TABLE (usr_id integer, usr_name text)
    AS $$
        CALL sql_proc_add_user(usr_name_in);
        SELECT
            usr.usr_id,
            usr.usr_name
        FROM sql_get_user(usr_name_in) AS usr;
    $$ 
    LANGUAGE SQL;
    """
    return stmt


def stmt_sql_proc_insert_user():
    """"""
    
    stmt = """
    CREATE OR REPLACE PROCEDURE sql_insert_user(usr_name_in text)
    LANGUAGE SQL
    BEGIN ATOMIC
        INSERT INTO users (username) VALUES (usr_name_in);
    END;
    """
    return stmt


def stmt_sql_add_user_v1():
    """Execute first:
        stmt_get_user();
        this pocedure works, but does not save ultimately new user
    """

    stmt = """
    CREATE OR REPLACE FUNCTION sql_add_user(usr_name_in text)
    RETURNS TABLE (usr_id integer, usr_name text)
    AS $$
        INSERT INTO users (username) VALUES (usr_name_in);
        SELECT
            usr.usr_id,
            usr.usr_name
        FROM sql_get_user(usr_name_in) AS usr;
    $$ 
    LANGUAGE SQL;
    """
    return stmt


def stmt_sql_add_user_vx():
    """Execute first:
        stmt_get_user();
    """

    stmt = """
    """

    # DROP FUNCTION IF EXISTS sql_add_user(text);        
    # CALL sql_insert_user(usr_name_in);
    # SELECT
    #     usr.usr_id
    # FROM sql_get_user(usr_name_in) AS usr

    # SELECT
    #     users.id
    # FROM users 
    # WHERE username = usr_name_in;

    # SELECT
    #     usr.usr_id
    # FROM get_user(usr_name_in) AS usr;

    return stmt