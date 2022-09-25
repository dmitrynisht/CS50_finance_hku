import psycopg2
import psycopg2.extras
import threading

# Thread-local data
_data = threading.local()


def _enable_logging(f):
    """Enable logging of SQL statements when Flask is in use."""

    import logging
    import functools

    @functools.wraps(f)
    def decorator(*args, **kwargs):

        # Infer whether Flask is installed
        try:
            import flask
        except ModuleNotFoundError:
            return f(*args, **kwargs)

        # Enable logging
        disabled = logging.getLogger("nt9k").disabled
        if flask.current_app:
            logging.getLogger("nt9k").disabled = False
        try:
            return f(*args, **kwargs)
        finally:
            logging.getLogger("nt9k").disabled = disabled

    return decorator


class SQL(object):
    """Wrap SQLAlchemy to provide a simple SQL API."""

    """nisht9k:
    this is truncated and less functional implementation
    of CS50 SQL-object"""

    def __init__(self, db_URL, **kwargs):

        # Lazily import
        import logging
        import sqlalchemy
        from sqlalchemy import create_engine

        """ Connect to the PostgreSQL database server. Using sqlalchemy + psycopg2 connection"""
        self._engine = create_engine(
            db_URL,
            execution_options={
                "isolation_level": "AUTOCOMMIT"
            }
        )

        # Autocommit by default
        self._autocommit = True

        # Get logger
        self._logger = logging.getLogger("nt9k")

        # Test database
        disabled = self._logger.disabled
        self._logger.disabled = True
        try:
            connection = self._engine.connect()
            connection.execute("SELECT 1")
            connection.close()
        except sqlalchemy.exc.OperationalError as e:
            e = RuntimeError(_parse_exception(e))
            e.__cause__ = None
            raise e
        finally:
            self._logger.disabled = disabled

    def __del__(self):
        """Disconnect from database."""
        self._disconnect()

    def _disconnect(self):
        """Close database connection."""
        if hasattr(_data, self._name()):
            getattr(_data, self._name()).close()
            delattr(_data, self._name())

    def _rawconnect(self):
        """Open RAW database connection."""
        if not hasattr(_data, self._name()):
            # Connect to database
            # using raw_connection() instead of connect() to enable .callproc()
            setattr(_data, self._name(), self._engine.raw_connection())
        
        # Use this connection
        return getattr(_data, self._name())

    def _name(self):
        """Return object's hash as a str."""
        return str(hash(self))

    @_enable_logging
    def execute(self, stmt, kwargs, *args, connection=None):
        """Execute a SQL stored procedure.
        returns rows"""
        
        import sqlalchemy
        import warnings
        import termcolor

        if connection:
            # Already connected
            self._autocommit = False
        else:
            # If no connection yet
            self._autocommit = True

            # Connect to database
            connection = self._rawconnect()
        
        # Disconnect if/when a Flask app is torn down
        try:
            import flask
            assert flask.current_app
            def teardown_appcontext(exception):
                self._disconnect()
            if teardown_appcontext not in flask.current_app.teardown_appcontext_funcs:
                flask.current_app.teardown_appcontext(teardown_appcontext)
        except (ModuleNotFoundError, AssertionError):
            pass

        # Catch SQLAlchemy warnings
        with warnings.catch_warnings():

            # Raise exceptions for warnings
            warnings.simplefilter("error")

            # Prepare, execute statement
            try:
                # we are using 'cursor_factory=psycopg2.extras.DictCursor' to make cursor return request results as dictionary
                db_cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
                
                # create stored procedures
                for stored_func in stmt['stored_func']: 
                    db_cursor.execute(stored_func())
                
                # execute main request, commit when altering data
                for proc_name, f_commit_required in stmt['proc_name'].items():
                    db_cursor.callproc(proc_name, kwargs)
                    if f_commit_required:
                        connection.commit()
                
                rows = [dict(row) for row in db_cursor.fetchall()]
                
                db_cursor.close()

            # If constraint violated, return None
            except sqlalchemy.exc.IntegrityError as e:
                self._logger.debug(termcolor.colored(stmt['proc_name'], "yellow"))
                e = ValueError(e.orig)
                e.__cause__ = None
                raise e

            # If user error
            except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.ProgrammingError) as e:
                self._disconnect()
                self._logger.debug(termcolor.colored(stmt['proc_name'], "red"))
                e = RuntimeError(e.orig)
                e.__cause__ = None
                raise e

            # Return value
            else:
                self._logger.debug(termcolor.colored(stmt['proc_name'], "green"))
                if self._autocommit:
                    # Don't stay connected unnecessarily
                    self._disconnect()

                return rows

    @_enable_logging
    def exec_commit(self, stmt, kwargs):
        """Execute a SQL stored procedure.
        returns rows"""
        
        import sqlalchemy
        import warnings
        import termcolor

        # If no connection yet
        if not hasattr(_data, self._name()):

            # Connect to database
            # using raw_connection() instead of connect() to enable .callproc()
            setattr(_data, self._name(), self._engine.raw_connection())
            # setattr(_data, self._name(), self._engine.connect())

        # Use this connection
        connection = getattr(_data, self._name())
        
        # # Disconnect if/when a Flask app is torn down
        # try:
        #     import flask
        #     assert flask.current_app
        #     def teardown_appcontext(exception):
        #         self._disconnect()
        #     if teardown_appcontext not in flask.current_app.teardown_appcontext_funcs:
        #         flask.current_app.teardown_appcontext(teardown_appcontext)
        # except (ModuleNotFoundError, AssertionError):
        #     pass

        # Catch SQLAlchemy warnings
        with warnings.catch_warnings():

            # Raise exceptions for warnings
            warnings.simplefilter("error")

            # # READING SQLALCHEMY
            # with connection.begin():
            #     for stored_func in stmt['stored_func']:
            #         connection.execute(stored_func())
            #         # conn.execute(some_other_table.insert().values(bat='hoho'))

            #     res = connection.execute(stmt['proc_name'], kwargs)

            # return ['empty list']

            # Prepare, execute statement
            # try:
            # we are using 'cursor_factory=psycopg2.extras.DictCursor' to make cursor return request results as dictionary
            db_cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            for stored_func in stmt['stored_func']: 
                db_cursor.execute(stored_func())
            
            # db_cursor.execute(sqlalchemy.text("BEGIN"))
            db_cursor.callproc(stmt['proc_name'], kwargs)
            rows = [dict(row) for row in db_cursor.fetchall()]
            # db_cursor.execute(sqlalchemy.text("COMMIT"))
            
            db_cursor.close()

            # # If constraint violated, return None
            # except sqlalchemy.exc.IntegrityError as e:
            #     self._logger.debug(termcolor.colored(stmt['proc_name'], "yellow"))
            #     e = ValueError(e.orig)
            #     e.__cause__ = None
            #     raise e

            # # If user error
            # except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.ProgrammingError) as e:
            #     self._disconnect()
            #     self._logger.debug(termcolor.colored(stmt['proc_name'], "red"))
            #     e = RuntimeError(e.orig)
            #     e.__cause__ = None
            #     raise e

            # # Return value
            # else:
            #     self._logger.debug(termcolor.colored(stmt['proc_name'], "green"))
            #     if self._autocommit:
            #         # Don't stay connected unnecessarily
            #         self._disconnect()

            #     return rows
            pass

def _parse_exception(e):
    """Parses an exception, returns its message."""

    # Lazily import
    import re

    # PostgreSQL
    matches = re.search(r"^\(psycopg2\.OperationalError\) (.+)$", str(e))
    if matches:
        return matches.group(1)