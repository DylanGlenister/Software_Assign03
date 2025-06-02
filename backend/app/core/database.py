from datetime import datetime
from enum import Enum
from typing import Generator

import mariadb

from ..utils.settings import SETTINGS


class Role(Enum):
	"""
	Accounts all have a role that dictates what they can and cannot do.
	(These may be innaccurate I don't remember what roles we chose.)
	"""
	OWNER = 'owner'
	ADMIN = 'admin'
	EMPLOYEE = 'employee'
	CUSTOMER = 'customer'
	GUEST = 'guest'


class Status(Enum):
	UNVERIFIED = 'unverified'
	ACTIVE = 'active'
	INACTIVE = 'inactive'
	CONDEMNED = 'condemned'


class Database:
	__pool: mariadb.ConnectionPool | None = None

	@classmethod
	def initialize_pool(cls):
		"""
		Create a pooling object. Pooling allows more efficient accessing of the database.
		"""
		if cls.__pool:
			return

		try:
			cls.__pool = mariadb.ConnectionPool(
				pool_name='mypool',
				pool_size=5,
				user=SETTINGS.database_username,
				password=SETTINGS.database_password,
				host=SETTINGS.database_host,
				port=SETTINGS.database_port,
				database=SETTINGS.database
			)
			print('Connection pool created successfully')
		except mariadb.Error as e:
			print(f'Error creating connection pool: {e}')

	@classmethod
	def get_connection(cls) -> mariadb.Connection:
		"""

		"""
		print(cls.__pool)
		if not cls.__pool:
			cls.initialize_pool()
		assert(cls.__pool)
		return cls.__pool.get_connection()

	def __init__(self, conn: mariadb.Connection):
		self.conn: mariadb.Connection = conn
		self.cur: mariadb.Cursor = conn.cursor()

	def close(self):
		self.cur.close()
		self.conn.close()

	def commit(self):
		self.conn.commit()

	def rollback(self):
		self.conn.rollback()

	# --- Internal query helpers ---

	def _fetch_one(self, _query: str, _params: tuple = (), /) -> dict | None:
		"""
		Execute a query and return a single row as a dictionary.

		Args:
			_query: SQL query string
			_params: Query parameters

		Returns:
			Single row as dict or None if no results/error
		"""
		try:
			self.cur.execute(_query, _params)
			row = self.cur.fetchone()

			if row is None:
				return None

			# Convert to dictionary using column descriptions
			columns = [desc[0] for desc in self.cur.description]
			return dict(zip(columns, row))

		except mariadb.Error as e:
			print(f'DB error in fetchone: {e}')
			return None
		except Exception as e:
			print(f'Unexpected error in fetchone: {e}')
			return None

	def _fetch_all(self, _query: str, _params: tuple = (), /) -> list[dict] | None:
		"""
		Execute a query and return all rows as a list of dictionaries.

		Args:
			_query: SQL query string
			_params: Query parameters

		Returns:
			List of rows as dictionaries or None if no results/error
		"""
		try:
			self.cur.execute(_query, _params)
			rows = self.cur.fetchall()

			if not rows:
				return None

			# Convert to list of dictionaries using column descriptions
			columns = [desc[0] for desc in self.cur.description]
			return [dict(zip(columns, row)) for row in rows]

		except mariadb.Error as e:
			print(f'DB error in fetchall: {e}')
			return None
		except Exception as e:
			print(f'Unexpected error in fetchall: {e}')
			return None

	def _execute(self, _query: str, _params: tuple = (), /, *, _returnLastId: bool = False) -> bool | int | None:
		"""
		Execute a query that modifies data (INSERT, UPDATE, DELETE).

		Args:
			_query: SQL query string
			_params: Query parameters
			_returnLastId: Whether to return the last inserted row ID

		Returns:
			- If _returnLastId=True: last row ID (int) or None on error
			- If _returnLastId=False: True on success, False on error
		"""
		try:
			self.cur.execute(_query, _params)

			# Check if any rows were affected
			affected_rows = self.cur.rowcount

			self.commit()

			if _returnLastId:
				# Only return lastrowid if rows were actually affected
				return self.cur.lastrowid if affected_rows > 0 else None
			else:
				return affected_rows > 0

		except mariadb.Error as e:
			print(f'DB error in execute: {e}, rolling back')
			try:
				self.rollback()
			except Exception as rollback_error:
				print(f'Error during rollback: {rollback_error}')

			return None if _returnLastId else False

		except Exception as e:
			print(f'Unexpected error in execute: {e}, rolling back')
			try:
				self.rollback()
			except Exception as rollback_error:
				print(f'Error during rollback: {rollback_error}')

			return None if _returnLastId else False

	# --- Public API methods ---

	def get_account(
		self,
		*,
		_accountID: int | None = None,
		_email: str | None = None
	):
		"""
		Retrieve information about an account using an accessor.

		Args:
			_accountID: Mutually exclusive with other args
			_email: Mutually exclusive with other args
			_firstname: Mutually exclusive with other args

		Returns:
			A dictionary containing information about the account.
		"""
		# Count non-None arguments
		args_num = sum(x is not None for x in [_accountID, _email])

		if args_num == 0:
			raise ValueError("Must provide exactly one of: _accountID, _email, or _firstname")
		elif args_num > 1:
			raise ValueError("Keyword arguments are mutually exclusive, only provide one of: _accountID, _email, or _firstname")

		selector = []

		if _accountID is not None:
			selector = ['accountID', (_accountID,)]
		elif _email is not None:
			selector = ['email', (_email,)]

		query = f'''
				SELECT (accountID, email, password, firstname, lastname, creationDate, role, status)
				FROM accounts
				WHERE {selector[0]} = %s
			'''
		return self._fetch_one(query, selector[1])

	def create_account(
		self,
		_email: str,
		_password: str,
		_role: Role = Role.GUEST,
		/,
		_firstname: str | None = None,
		_lastname: str | None = None,
		_creation_date: datetime = datetime.now()
	):
		"""
		Create a new account on the database.

		Args:
			email: The email account for the account
		"""

		if _firstname is not None and _lastname is not None:
			query = '''
				INSERT INTO accounts (email, password, firstname, lastname, creationDate, role)
				VALUES (%s, %s, %s, %s, %s, %s)
			'''
			params = (_email, _password, _firstname, _lastname, _creation_date, _role)
		else:
			query = '''
				INSERT INTO accounts (email, password, creationDate, role)
				VALUES (%s, %s, %s, %s)
			'''
			params = (_email, _password, _creation_date, _role)
		return self._execute(query, params, _returnLastId=True)

	def update_account(self, account_id: int, **fields):
		if not fields:
			return False

		set_clause = ', '.join(f'{key} = ?' for key in fields)
		params = tuple(fields.values()) + (account_id,)

		query = f'UPDATE accounts SET {set_clause} WHERE accountID = ?'
		return self._execute(query, params)

	def get_all_products(self):
		query: str = 'SELECT * FROM products'
		return self._fetch_all(query)

	def get_trolley(self, account_id: int):
		query = '''
			SELECT productID, amount
			FROM trolleys
			WHERE customerID = ?
		'''
		return self._fetch_all(query, (account_id,))

	def add_to_trolley(self, account_id: int, product_id: int, amount: int = 1):
		select_query = '''
			SELECT amount FROM trolleys
			WHERE customerID = ? AND productID = ?
		'''
		existing = self._fetch_one(select_query, (account_id, product_id))
		if existing:
			new_amount = existing[0] + amount
			update_query = '''
				UPDATE trolleys SET amount = ?
				WHERE customerID = ? AND productID = ?
			'''
			return self._execute(update_query, (new_amount, account_id, product_id))
		else:
			insert_query = '''
				INSERT INTO trolleys (customerID, productID, amount)
				VALUES (?, ?, ?)
			'''
			return self._execute(insert_query, (account_id, product_id, amount))

	def remove_from_trolley(self, account_id: int, product_id: int, amount: int = 1):
		select_query = '''
			SELECT amount FROM trolleys
			WHERE customerID = ? AND productID = ?
		'''
		existing = self._fetch_one(select_query, (account_id, product_id))
		if not existing:
			return False

		current_amount = existing[0]
		if current_amount <= amount:
			delete_query = '''
				DELETE FROM trolleys
				WHERE customerID = ? AND productID = ?
			'''
			return self._execute(delete_query, (account_id, product_id))
		else:
			new_amount = current_amount - amount
			update_query = '''
				UPDATE trolleys SET amount = ?
				WHERE customerID = ? AND productID = ?
			'''
			return self._execute(update_query, (new_amount, account_id, product_id))

	def clear_trolley(self, account_id: int):
		delete_all_query = '''
			DELETE FROM trolleys
			WHERE customerID = ?
		'''
		return self._execute(delete_all_query, (account_id,))

	def delete_account(self, account_id: int):
		query = 'DELETE FROM accounts WHERE accountID = ?'
		return self._execute(query, (account_id,))

	def get_all_accounts(self):
		query = '''
			SELECT accountID, email, creationDate, roleID, statusID
			FROM accounts
		'''
		return self._fetch_all(query)

	def delete_old_accounts_by_role(self, role_ID: int, before_date: str):
		query = '''
			DELETE FROM accounts
			WHERE roleID = %s AND creationDate < %s
		'''
		return self._execute(query, (role_ID, before_date))


def get_db() -> Generator[Database, None, None]:
	Database.initialize_pool()
	conn = Database.get_connection()
	db: Database = Database(conn)
	try:
		yield db
	finally:
		db.close()

def main():
	Database.initialize_pool()
	conn = Database.get_connection()
	db: Database = Database(conn)
	db.create_account('test@email.com', 'fuck', Role.OWNER)
	return

if __name__ == '__main__':
	main()
