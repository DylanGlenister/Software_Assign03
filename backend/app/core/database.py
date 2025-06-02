from datetime import datetime
from enum import Enum
from typing import Generator

import mariadb

from ..utils.settings import SETTINGS


class Role(Enum):
	'owner'
	'admin'
	'employee'
	'customer'
	'guest'


class Status(Enum):
	'active'
	'inactive'
	'deactive'


class Database:
	__pool: mariadb.ConnectionPool | None = None

	@classmethod
	def initialize_pool(cls):
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
	def get_connection(cls):
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

	def _fetch_one(self, _query: str, _params: tuple = ()):
		try:
			self.cur.execute(_query, _params)
			return self.cur.fetchone()
		except mariadb.Error as e:
			print(f'DB error in fetchone: {e}')
			return None

	def _fetch_all(self, _query: str, _params: tuple = ()):
		try:
			self.cur.execute(_query, _params)
			return self.cur.fetchall()
		except mariadb.Error as e:
			print(f'DB error in fetchall: {e}')
			return []

	def _execute(self, _query: str, _params: tuple = (), _return_last_id: bool = False):
		try:
			self.cur.execute(_query, _params)
			self.commit()
			return self.cur.lastrowid if _return_last_id else True
		except mariadb.Error as e:
			print(f'DB error in execute: {e}, rolling back')
			self.rollback()
			return None if _return_last_id else False

	# --- Public API methods ---

	def get_account(self, *, email: str | None = None, account_id: int | None = None):
		if email:
			query = '''
				SELECT accountID, email, password, creationDate, roleID, statusID
				FROM accounts
				WHERE email = ?
			'''
			return self._fetch_one(query, (email,))
		elif account_id:
			query = '''
				SELECT accountID, email, password, creationDate, roleID, statusID
				FROM accounts
				WHERE accountID = ?
			'''
			return self._fetch_one(query, (account_id,))
		else:
			return None

	def create_account(self, email: str, password: str, creation_date: datetime, role_ID: int = 1, status_ID: int = 1):
		query = '''
			INSERT INTO accounts (email, password, creationDate, roleID, statusID)
			VALUES (?, ?, ?, ?, ?)
		'''
		params = (email, password, creation_date, role_ID, status_ID)
		return self._execute(query, params, _return_last_id=True)

	def get_role(self, role_id: int):
		query = 'SELECT roleID, name FROM roles WHERE roleID = ?'
		return self._fetch_one(query, (role_id,))

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

	def test_select(self):
		query: str = 'SELECT * FROM test'
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

	return

if __name__ == '__main__':
	main()
