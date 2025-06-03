from datetime import datetime
from enum import Enum
from typing import Any, Generator

import mariadb
from fastapi import HTTPException, status
from ..utils.settings import SETTINGS

# TODO Currently _execute can return 3 types, dependent on parameters. This fuckery trickles to all code that uses this function.

class Role(Enum):
	"""
	Accounts all have a role that dictates what they can and cannot do.
	"""
	OWNER = 'owner'
	ADMIN = 'admin'
	EMPLOYEE = 'employee'
	CUSTOMER = 'customer'
	GUEST = 'guest'


class Status(Enum):
	"""
	Account status. Condemned accounts are to be deleted.
	"""
	UNVERIFIED = 'unverified'
	ACTIVE = 'active'
	INACTIVE = 'inactive'
	CONDEMNED = 'condemned'


class Database:
	"""
	Database class for managing MariaDB connections and operations.
	"""
	__pool: mariadb.ConnectionPool | None = None

	@classmethod
	def initialize_pool(cls):
		"""
		Create a pooling object. Pooling allows more efficient accessing of the database.
		"""
		if cls.__pool:
			return
		try:
			print(cls.__pool)
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
			print(f"Error creating connection pool: {e}")
			error_message_lower = str(e).lower()
			is_access_denied = "access denied" in error_message_lower or (hasattr(e, 'errno') and e.errno == 1045)

			if is_access_denied:
				detail_message = f"Database pool initialization failed: Access Denied. Check credentials. (Error: {e})"
			else:
				detail_message = f"Database pool initialization failed: {e}"

			raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=detail_message
            )

	@classmethod
	def get_connection(cls) -> mariadb.Connection:
		"""
		Get a connection from the connection pool.

		Returns:
			MariaDB connection object
		"""
		if not cls.__pool:
			cls.initialize_pool()

		try:
			assert cls.__pool is not None
			return cls.__pool.get_connection()
		except mariadb.Error as e:
			print(f"Error getting connection from pool: {e}")

			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail=f"Failed to get connection from database pool: {e}"
			)

	def __init__(self, _conn: mariadb.Connection, /):
		"""
		Initialize Database instance with a connection.

		Args:
			_conn: MariaDB connection object
		"""
		self.conn: mariadb.Connection = _conn
		self.cur: mariadb.Cursor = _conn.cursor()

	def close(self):
		"""Close cursor and connection."""
		self.cur.close()
		self.conn.close()

	def commit(self):
		"""Commit current transaction."""
		self.conn.commit()

	def rollback(self):
		"""Rollback current transaction."""
		self.conn.rollback()

	# --- Internal query helpers ---

	def _fetch_one(self, _query: str, _params: tuple = (), /) -> dict[str, Any] | None:
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

	def _fetch_all(self, _query: str, _params: tuple = (), /) -> list[dict[str, Any]] | None:
		"""
		Execute a query and return all rows as a list of dictionaries.

		Args:
			_query: SQL query string
			_params: Query parameters

		Returns:
			list of rows as dictionaries or None if no results/error
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
			affected_rows = self.cur.rowcount
			self.commit()

			if _returnLastId:
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

	# --- Account Management ---

	def get_account(
		self,
		*,
		_accountId: int | None = None,
		_email: str | None = None
	) -> dict[str, Any] | None:
		"""
		Retrieve information about an account using an accessor.

		Args:
			_accountId: Account ID to search by
			_email: Email to search by

		Returns:
			A dictionary containing information about the account or None
		"""
		args_num = sum(x is not None for x in [_accountId, _email])

		if args_num == 0:
			raise ValueError("Must provide exactly one of: _accountId or _email")
		elif args_num > 1:
			raise ValueError("Keyword arguments are mutually exclusive")

		if _accountId is not None:
			query = '''
				SELECT accountID, email, password, firstname, lastname, creationDate, role, status
				FROM Account
				WHERE accountID = %s
			'''
			params = (_accountId,)
		else:
			query = '''
				SELECT accountID, email, password, firstname, lastname, creationDate, role, status
				FROM Account
				WHERE email = %s
			'''
			params = (_email,)

		return self._fetch_one(query, params)

	def get_accounts(
		self,
		*,
		role: Role | None = None,
		status: Status | None = None,
		olderThan: int | None = None
	) -> list[dict[str, Any]] | None:
		"""
		Retrieve accounts with optional filtering by role and/or status.
		If no filters are provided, returns all accounts.

		Args:
			role: Optional role to filter by
			status: Optional status to filter by
			olderThan: Optional int which signifies days, and can get accounts older than x days

		Returns:
			list of account dictionaries or None if no results/error
		"""
		query = '''
			SELECT accountID, email, firstname, lastname, creationDate, role, status
			FROM Account
		'''
		conditions = []
		params = []
		
		if role is not None:
			conditions.append("role = %s")
			params.append(role.value)
		
		if status is not None:
			conditions.append("status = %s")
			params.append(status.value)
		
		if olderThan is not None:
			conditions.append("creationDate < DATE_SUB(CURDATE(), INTERVAL %s DAY)")
			params.append(olderThan)
		
		if conditions:
			query += " WHERE " + " AND ".join(conditions)
		
		return self._fetch_all(query, tuple(params) if params else ())

	def create_account(
		self,
		_email: str,
		_password: str,
		_role: Role = Role.GUEST,
		*,
		_firstName: str | None = None,
		_lastName: str | None = None,
		_creationDate: datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	) -> int | None:
		"""
		Create a new account in the database.

		Args:
			_email: The email for the account
			_password: The password for the account
			_role: The role for the account
			_firstName: Optional first name
			_lastName: Optional last name
			_creationDate: Optional creation date (defaults to now)

		Returns:
			Account ID of created account or None on error
		"""
		if _creationDate is None:
			_creationDate = datetime.now()

		if _firstName is not None and _lastName is not None:
			query = '''
				INSERT INTO Account (email, password, firstname, lastname, creationDate, role)
				VALUES (%s, %s, %s, %s, %s, %s)
			'''
			params = (_email, _password, _firstName, _lastName, _creationDate, _role.value)
		else:
			query = '''
				INSERT INTO Account (email, password, creationDate, role)
				VALUES (%s, %s, %s, %s)
			'''
			params = (_email, _password, _creationDate, _role.value)

		return self._execute(query, params, _returnLastId=True)

	# NOTE Using dictonary args might be a bit fucky but it seems the best for the case.
	def update_account(self, _accountId: int, /, **_fields) -> bool | int | None:
		"""
		Update account fields.

		Args:
			_accountId: Account ID to update
			**_fields: Fields to update

		Returns:
			True on success, False on error
		"""
		if not _fields:
			return False

		set_clause = ', '.join(f'{key} = %s' for key in _fields)
		params = tuple(_fields.values()) + (_accountId,)

		query = f'UPDATE Account SET {set_clause} WHERE accountID = %s'
		return self._execute(query, params)

	# NOTE This currently does not work as the database constraints prevent it
	def delete_accounts(self, _accountIds: list[int], /) -> bool | int | None:
		"""
		Delete accounts from the database.

		Args:
			_accountIds: List of account IDs to delete

		Returns:
			True on success, False on error
		"""
		if not _accountIds:
			return False  # Nothing to delete

		placeholders = ', '.join(['%s'] * len(_accountIds))
		query = f'DELETE FROM Account WHERE accountID IN ({placeholders})'
		return self._execute(query, tuple(_accountIds))

	# --- Address Management ---

	def create_address(self, _accountId: int, _location: str, /) -> int | None:
		"""
		Create a new address for an account.

		Args:
			_accountId: Account ID to link address to
			_location: Address location string

		Returns:
			Address ID or None on error
		"""
		query = '''
			INSERT INTO Address (accountID, location)
			VALUES (%s, %s)
		'''
		return self._execute(query, (_accountId, _location), _returnLastId=True)

	def get_addresses(self, _accountId: int, /) -> list[dict[str, Any]] | None:
		"""
		Get all addresses for an account.

		Args:
			_accountId: Account ID to get addresses for

		Returns:
			list of address dictionaries or None
		"""
		query = '''
			SELECT addressID, accountID, location
			FROM Address
			WHERE accountID = %s
		'''
		return self._fetch_all(query, (_accountId,))

	# NOTE This currently does not work as the database constraints prevent it
	def delete_address(self, _addressId: int, /) -> bool | int | None:
		"""
		Delete an address.

		Args:
			_addressId: Address ID to delete

		Returns:
			True on success, False on error
		"""
		query = 'DELETE FROM Address WHERE addressID = %s'
		return self._execute(query, (_addressId,))

	# --- Product Management ---

	def get_products_with_tags(self, _tagIds: list[int] | None = None, /) -> list[dict[str, Any]] | None:
		"""
		Get all products, optionally filtered by tags.

		Args:
			_tagIds: Optional list of tag IDs to filter by

		Returns:
			list of product dictionaries or None
		"""
		if _tagIds:
			placeholders = ','.join(['%s'] * len(_tagIds))
			query = f'''
				SELECT DISTINCT p.productID, p.name, p.description, p.price,
					   p.stock, p.available, p.creationDate, p.discontinued
				FROM Product p
				JOIN `Product-Tag` pt ON p.productID = pt.productID
				WHERE pt.tagID IN ({placeholders})
			'''
			return self._fetch_all(query, tuple(_tagIds))
		else:
			query = '''
				SELECT productID, name, description, price, stock, available, creationDate, discontinued
				FROM Product
			'''
			return self._fetch_all(query)

	def get_product_images(self, _productId: int, /) -> list[str] | None:
		"""
		Get image URLs associated with a product.

		Args:
			_productId: Product ID to get images for

		Returns:
			list of image URLs or None
		"""
		query = '''
			SELECT i.url
			FROM Image i
			JOIN `Product-Image` pi ON i.imageID = pi.imageID
			WHERE pi.productID = %s
		'''
		result = self._fetch_all(query, (_productId,))
		return [row['url'] for row in result] if result else None

	# --- Tag Management ---

	def create_tag(self, _name: str, /) -> int | None:
		"""
		Create a new tag.

		Args:
			_name: Tag name

		Returns:
			Tag ID or None on error
		"""
		query = 'INSERT INTO Tag (name) VALUES (%s)'
		return self._execute(query, (_name,), _returnLastId=True)

	def add_tag_to_product(self, _tagId: int, _productId: int, /) -> bool | int | None:
		"""
		Link a product to a tag.

		Args:
			_productId: Product ID
			_tagId: Tag ID

		Returns:
			True on success, False on error
		"""
		query = 'INSERT INTO `Product-Tag` (productID, tagID) VALUES (%s, %s)'
		return self._execute(query, (_productId, _tagId))

	# --- Image Management ---

	def add_image_for_product(self, _url: str, _productId: int, /) -> int | None:
		"""
		Create a new image and link it to a product.

		Args:
			_url: Image URL
			_productId: Product ID to link to

		Returns:
			Image ID or None on error
		"""
		# Create image
		image_query = 'INSERT INTO Image (url) VALUES (%s)'
		image_id = self._execute(image_query, (_url,), _returnLastId=True)

		if image_id:
			# Link to product
			link_query = 'INSERT INTO `Product-Image` (productID, imageID) VALUES (%s, %s)'
			if self._execute(link_query, (_productId, image_id)):
				return image_id

		return None

	# --- Trolley Management ---

	def get_trolley(self, _accountId: int, /) -> list[dict[str, Any]] | None:
		"""
		Get trolley contents for an account.

		Args:
			_accountId: Account ID

		Returns:
			list of trolley items or None
		"""
		query = '''
			SELECT li.lineItemID, li.productID, li.quantity, li.priceAtSale
			FROM Trolley t
			JOIN LineItem li ON t.lineItemID = li.lineItemID
			WHERE t.accountID = %s
		'''
		return self._fetch_all(query, (_accountId,)) or []

	def add_to_trolley(self, _accountId: int, _productId: int, _quantity: int = 1, /) -> bool | int | None:
		"""
		Add item to trolley.

		Args:
			_accountId: Account ID
			_productId: Product ID
			_quantity: Quantity to add

		Returns:
			True on success, False on error
		"""
		# Create line item
		line_item_query = 'INSERT INTO LineItem (productID, quantity) VALUES (%s, %s)'
		line_item_id = self._execute(line_item_query, (_productId, _quantity), _returnLastId=True)

		if line_item_id:
			# Add to trolley
			trolley_query = 'INSERT INTO Trolley (accountID, lineItemID) VALUES (%s, %s)'
			return self._execute(trolley_query, (_accountId, line_item_id))

		return False

	def clear_trolley(self, _accountId: int, /) -> bool | int | None:
		"""
		Clear all items from trolley.

		Args:
			_accountId: Account ID

		Returns:
			True on success, False on error
		"""
		query = 'DELETE FROM Trolley WHERE accountID = %s'
		return self._execute(query, (_accountId,))

	# --- Order Management ---

	def create_order(self, _accountId: int, _addressId: int, _lineItemIds: list[int], /) -> int | None:
		"""
		Create a new order with line items.

		Args:
			_accountId: Account ID
			_addressId: Address ID for delivery
			_lineItemIds: list of line item IDs to include in order

		Returns:
			Order ID or None on error
		"""
		# Create order
		order_query = '''
			INSERT INTO `Order` (accountID, addressID, date)
			VALUES (%s, %s, %s)
		'''
		order_id = self._execute(order_query, (_accountId, _addressId, datetime.now()), _returnLastId=True)

		if order_id:
			# Link line items to order
			for line_item_id in _lineItemIds:
				link_query = 'INSERT INTO OrderItem (orderID, lineItemID) VALUES (%s, %s)'
				if not self._execute(link_query, (order_id, line_item_id)):
					return None

			return order_id

		return None

	# --- Invoice Management ---

	def save_invoice(self, _accountId: int, _orderId: int, _data: bytes, /) -> int | None:
		"""
		Save invoice data.

		Args:
			_accountId: Account ID
			_orderId: Order ID
			_data: Invoice data as bytes

		Returns:
			Invoice ID or None on error
		"""
		query = '''
			INSERT INTO Invoice (accountID, orderID, creationDate, data)
			VALUES (%s, %s, %s, %s)
		'''
		return self._execute(query, (_accountId, _orderId, datetime.now(), _data), _returnLastId=True)

	def get_invoice(self, _invoiceId: int, /) -> dict[str, Any] | None:
		"""
		Retrieve invoice data.

		Args:
			_invoiceId: Invoice ID

		Returns:
			Invoice dictionary or None
		"""
		query = '''
			SELECT invoiceID, accountID, orderID, creationDate, data
			FROM Invoice
			WHERE invoiceID = %s
		'''
		return self._fetch_one(query, (_invoiceId,))

	# --- Receipt Management ---

	def save_receipt(self, _accountId: int, _orderId: int, _data: bytes, /) -> int | None:
		"""
		Save receipt data.

		Args:
			_accountId: Account ID
			_orderId: Order ID
			_data: Receipt data as bytes

		Returns:
			Receipt ID or None on error
		"""
		query = '''
			INSERT INTO Receipt (accountID, orderID, creationDate, data)
			VALUES (%s, %s, %s, %s)
		'''
		return self._execute(query, (_accountId, _orderId, datetime.now(), _data), _returnLastId=True)

	def get_receipt(self, _receiptId: int, /) -> dict[str, Any] | None:
		"""
		Retrieve receipt data.

		Args:
			_receiptId: Receipt ID

		Returns:
			Receipt dictionary or None
		"""
		query = '''
			SELECT receiptID, accountID, orderID, creationDate, data
			FROM Receipt
			WHERE receiptID = %s
		'''
		return self._fetch_one(query, (_receiptId,))

	# --- Report Management ---

	def save_report(self, _creatorId: int, _data: bytes, /) -> int | None:
		"""
		Save report data.

		Args:
			_creatorId: Account ID of report creator
			_data: Report data as bytes

		Returns:
			Report ID or None on error
		"""
		query = '''
			INSERT INTO Report (creator, creationDate, data)
			VALUES (%s, %s, %s)
		'''
		return self._execute(query, (_creatorId, datetime.now(), _data), _returnLastId=True)

	def get_report(self, _reportId: int, /) -> dict[str, Any] | None:
		"""
		Retrieve report data.

		Args:
			_reportId: Report ID

		Returns:
			Report dictionary or None
		"""
		query = '''
			SELECT reportID, creator, creationDate, data
			FROM Report
			WHERE reportID = %s
		'''
		return self._fetch_one(query, (_reportId,))
	
	# --- Utilities ---
	def get_enum_values(self, tableName: str, columnName: str) -> list[str]:
		"""
		Retrieve the enum values for a specific column in a MariaDB table.

		Args:
			conn: Active mariadb connection.
			tableName: Name of the table.
			columnName: Name of the enum column.

		Returns:
			List of enum values as strings.

		Raises:
			ValueError if the column is not an ENUM type.
		"""
		query = """
			SELECT COLUMN_TYPE
			FROM INFORMATION_SCHEMA.COLUMNS
			WHERE TABLE_SCHEMA = DATABASE()
			AND TABLE_NAME = %s
			AND COLUMN_NAME = %s
		"""
		result = self._fetch_one(query, (tableName, columnName))
		if not result:
			raise ValueError(f"Column `{tableName}` in table `{columnName}` not found.")
		column_type = result["COLUMN_TYPE"]
		if not column_type.startswith("enum("):
			raise ValueError(f"Column `{columnName}` is not an ENUM type.")

		enum_str = column_type[5:-1]

		enum_values = [v.strip("'") for v in enum_str.split(",")]
		return enum_values


def get_db() -> Generator[Database, None, None]:
	"""
	Context manager for database connections.

	Yields:
		Database instance
	"""
	raw_conn = None
	db_instance = None

	try:
		raw_conn = Database.get_connection()
		db_instance = Database(raw_conn)
		yield db_instance

	except mariadb.Error as e:
		print(f"MariaDB error within get_db context: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"A database error occurred during the request: {e}"
		)

	except HTTPException:
		raise

	except Exception as e:
		print(f"Unexpected error in get_db context: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"An unexpected error occurred: {e}"
		)

	finally:
		if db_instance:
			db_instance.close()
