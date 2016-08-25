'''
A wrapper for the securitybot to access its database.
'''
import MySQLdb
import logging

from typing import Any, Sequence

class SQLEngine(object):
    # Whether the singleton has been instantiated
    _host = None # type: str
    _user = None # type: str
    _passwd = None # type: str
    _db = None # type: str
    _created = False # type: bool
    _conn = None
    _cursor = None

    def __init__(self, host, user, passwd, db):
        # type: (str, str, str, str) -> None
        '''
        Initializes the SQL connection to be used for the bot.

        Args:
            host (str): The hostname of the SQL server.
            user (str): The username to use.
            passwd (str): Password for MySQL user.
            db (str): The name of the database to connect to.
        '''
        if not SQLEngine._created:
            SQLEngine._host = host
            SQLEngine._user = user
            SQLEngine._passwd = passwd
            SQLEngine._db = db
            SQLEngine._create_engine(host, user, passwd, db)
            SQLEngine._created = True

    @staticmethod
    def _create_engine(host, user, passwd, db):
        # type: (str, str, str, str) -> None
        '''
        Args:
            host (str): The hostname of the SQL server.
            user (str): The username to use.
            passwd (str): Password for MySQL user.
            db (str): The name of the database to connect to.
        '''
        SQLEngine._conn = MySQLdb.connect(host=host,
                                        user=user,
                                        passwd=passwd,
                                        db=db)
        SQLEngine._cursor = SQLEngine._conn.cursor()

    @staticmethod
    def execute(query, params=None):
        # type: (str, Sequence[Any]) -> Sequence[Sequence[Any]]
        '''
        Executes a given SQL query with some possible params.

        Args:
            query (str): The query to perform.
            params (Tuple[str]): Optional parameters to pass to the query.
        Returns:
            Tuple[Tuple[str]]: The output from the SQL query.
        '''
        if params is None:
            params = ()
        try:
            SQLEngine._cursor.execute(query, params)
            rows = SQLEngine._cursor.fetchall()
            SQLEngine._conn.commit()
        except (AttributeError, MySQLdb.OperationalError):
            # Recover from lost connection
            logging.warn('Recovering from lost MySQL connection.')
            SQLEngine._create_engine(SQLEngine._host,
                                     SQLEngine._user,
                                     SQLEngine._passwd,
                                     SQLEngine._db)
            return SQLEngine.execute(query, params)
        except MySQLdb.Error as e:
            try:
                raise SQLEngineException('MySQL error [{0}]: {1}'.format(e.args[0], e.args[1]))
            except IndexError:
                raise SQLEngineException('MySQL error: {0}'.format(e))
        return rows

class SQLEngineException(Exception):
    pass

def init_sql():
    # type: () -> None
    '''Initializes SQL.'''
    SQLEngine('localhost', 'root', '', 'securitybot')
