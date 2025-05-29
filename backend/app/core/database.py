import mariadb
from typing import Generator, Any, List, Optional, Tuple
from datetime import datetime
from ..utils.settings import SETTINGS

class Database:
	__pool: mariadb.ConnectionPool = None

	@classmethod
	def initialize_pool(cls):
		if cls.__pool:
			return

		try:
			cls.__pool = mariadb.ConnectionPool(
				pool_name="mypool",
				pool_size=5,
				user=SETTINGS.database_username,
				password=SETTINGS.database_password,
				host=SETTINGS.database_host,
				port=SETTINGS.database_port,
				database=SETTINGS.database
			)
			print("Connection pool created successfully")
			print(cls.__pool)
		except mariadb.Error as e:
			print(f"Error creating connection pool: {e}")

	@classmethod
	def get_connection(cls):
		print(cls.__pool)
		if not cls.__pool:
			cls.initialize_pool()
			print(cls.__pool)
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

	def _fetch_one(self, query: str, params: Tuple = ()) -> Optional[Tuple[Any]]:
		try:
			self.cur.execute(query, params)
			return self.cur.fetchone()
		except mariadb.Error as e:
			print(f"DB error in fetchone: {e}")
			return None

	def _fetch_all(self, query: str, params: Tuple = ()) -> List[Tuple[Any]]:
		try:
			self.cur.execute(query, params)
			return self.cur.fetchall()
		except mariadb.Error as e:
			print(f"DB error in fetchall: {e}")
			return []

	def _execute(self, query: str, params: Tuple = (), return_last_id: bool = False):
		try:
			self.cur.execute(query, params)
			self.commit()
			return self.cur.lastrowid if return_last_id else True
		except mariadb.Error as e:
			print(f"DB error in execute: {e}, rolling back")
			self.rollback()
			return None if return_last_id else False

	# --- Public API methods ---

	def get_account(self, *, email: Optional[str] = None, account_id: Optional[int] = None) -> Optional[Tuple]:
		if email:
			query = """
				SELECT accountID, email, password, creationDate, roleID, statusID
				FROM accounts
				WHERE email = ?
			"""
			return self._fetch_one(query, (email,))
		elif account_id:
			query = """
				SELECT accountID, email, password, creationDate, roleID, statusID
				FROM accounts
				WHERE accountID = ?
			"""
			return self._fetch_one(query, (account_id,))
		else:
			return None


	def create_account(self, email: str, password: str, creation_date: datetime, roleID: int = 1, statusID: int = 1) -> Optional[int]:
		query = """
			INSERT INTO accounts (email, password, creationDate, roleID, statusID)
			VALUES (?, ?, ?, ?, ?)
		"""
		params = (email, password, creation_date, roleID, statusID)
		return self._execute(query, params, return_last_id=True)

	def role_exists(self, role_id: int) -> bool:
		query = "SELECT 1 FROM roles WHERE roleID = ?"
		return self._fetch_one(query, (role_id,)) is not None

	def status_exists(self, status_id: int) -> bool:
		query = "SELECT 1 FROM status WHERE statusID = ?"
		return self._fetch_one(query, (status_id,)) is not None


	def get_role(self, role_id: int) -> Optional[Tuple]:
		query = "SELECT roleID, name FROM roles WHERE roleID = ?"
		return self._fetch_one(query, (role_id,))

	def update_account(self, account_id: int, **fields) -> bool:
		if not fields:
			return False

		set_clause = ", ".join(f"{key} = ?" for key in fields)
		params = tuple(fields.values()) + (account_id,)

		query = f"UPDATE accounts SET {set_clause} WHERE accountID = ?"
		return self._execute(query, params)

	def get_all_products(self) -> List[Tuple]:
		query: str = "SELECT * FROM products"
		return self._fetch_all(query)

	def test_select(self) -> List[Tuple[int, int]]:
		query: str = "SELECT * FROM test"
		return self._fetch_all(query)

	def get_trolly(self, account_id: int) -> list[tuple]:
		query = """
			SELECT productID, amount
			FROM trolleys
			WHERE customerID = ?
		"""
		return self._fetch_all(query, (account_id,))

	def add_to_trolly(self, account_id: int, product_id: int, amount: int = 1) -> bool:
		select_query = """
			SELECT amount FROM trolleys
			WHERE customerID = ? AND productID = ?
		"""
		existing = self._fetch_one(select_query, (account_id, product_id))
		if existing:
			new_amount = existing[0] + amount
			update_query = """
				UPDATE trolleys SET amount = ?
				WHERE customerID = ? AND productID = ?
			"""
			return self._execute(update_query, (new_amount, account_id, product_id))
		else:
			insert_query = """
				INSERT INTO trolleys (customerID, productID, amount)
				VALUES (?, ?, ?)
			"""
			return self._execute(insert_query, (account_id, product_id, amount))

	def remove_from_trolly(self, account_id: int, product_id: int, amount: int = 1) -> bool:
		select_query = """
			SELECT amount FROM trolleys
			WHERE customerID = ? AND productID = ?
		"""
		existing = self._fetch_one(select_query, (account_id, product_id))
		if not existing:
			return False

		current_amount = existing[0]
		if current_amount <= amount:
			delete_query = """
				DELETE FROM trolleys
				WHERE customerID = ? AND productID = ?
			"""
			return self._execute(delete_query, (account_id, product_id))
		else:
			new_amount = current_amount - amount
			update_query = """
				UPDATE trolleys SET amount = ?
				WHERE customerID = ? AND productID = ?
			"""
			return self._execute(update_query, (new_amount, account_id, product_id))

	def clear_trolly(self, account_id: int) -> bool:
		delete_all_query = """
			DELETE FROM trolleys
			WHERE customerID = ?
		"""
		return self._execute(delete_all_query, (account_id,))

	def delete_account(self, account_id: int) -> bool:
		query = "DELETE FROM accounts WHERE accountID = ?"
		return self._execute(query, (account_id,))

	def get_all_accounts(self) -> List[Tuple]:
		query = """
			SELECT accountID, email, creationDate, roleID, statusID
			FROM accounts
		"""
		return self._fetch_all(query)


def get_db() -> Generator[Database, None, None]:
	Database.initialize_pool()
	conn = Database.get_connection()
	db: Database = Database(conn)
	try:
		yield db
	finally:
		db.close()
