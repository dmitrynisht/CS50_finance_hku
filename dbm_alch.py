from cs50 import SQL
import threading
import psycopg2
import psycopg2.extras

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


class nt9kSQL(SQL):
    """Wrap CS50-SQL to enable .raw_connection() to provide a .callproc()"""
    # consider __init__ ok
    # consider execute  ok

    def _rawconnect(self):
        """Open RAW database connection."""
        if not hasattr(_data, self._name()):
            # Connect to database
            # using raw_connection() instead of connect() to enable .callproc()
            setattr(_data, self._name(), self._engine.raw_connection())
        
        # Use this connection
        return getattr(_data, self._name())

    @_enable_logging
    def stproc_execute(self, stmt, kwargs, *args, connection=None):
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
