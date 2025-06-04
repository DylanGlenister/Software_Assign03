from datetime import datetime
from enum import Enum
from typing import Any, Generator, TypeAlias

import mariadb
from fastapi import HTTPException, status

#from ..utils.settings import SETTINGS


class MockSettings:
	database_username: str = 'admin'
	database_password: str = 'password'
	database_host: str = 'localhost'
	database_port: int = 3306
	database: str = 'awe_electronics'

SETTINGS = MockSettings()

# Type aliases
DictRow: TypeAlias = dict[str, Any]
Id: TypeAlias = int


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
			print(f'Attempting to create connection pool for database \'{SETTINGS.database}\' on {SETTINGS.database_host}:{SETTINGS.database_port}')
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
			error_message_lower = str(e).lower()
			is_access_denied = 'access denied' in error_message_lower or (hasattr(e, 'errno') and e.errno == 1045)

			if is_access_denied:
				detail_message = f'Database pool initialization failed: Access Denied. Check credentials. (Error: {e})'
			else:
				detail_message = f'Database pool initialization failed: {e}'

			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail=detail_message
			)

	@classmethod
	def get_connection(cls) -> mariadb.Connection:
		"""
		Retrieves a connection from the pool.
		Initializes the pool if it doesn't exist.

		Returns:
			A MariaDB connection object.

		Raises:
			HTTPException: If a connection cannot be obtained.
		"""
		if not cls.__pool:
			cls.initialize_pool()

		try:
			assert cls.__pool is not None, 'Connection pool is not initialized'
			return cls.__pool.get_connection()
		except mariadb.Error as e:
			print(f'Error getting connection from pool: {e}')
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail=f'Failed to get connection from database pool: {e}'
			)
		except AssertionError as e:
			print(f'Assertion error: {e}')
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail=str(e)
			)

	def __init__(self, _conn: mariadb.Connection, /):
		"""
		Initializes the Database instance with a MariaDB connection.

		Args:
			_conn: A MariaDB connection object.
		"""
		self.conn: mariadb.Connection = _conn
		self.cur: mariadb.Cursor = _conn.cursor()
		self.conn.autocommit = False # Ensure autocommit is off for manual transaction control

	def close(self):
		"""Closes the database cursor and connection."""
		if hasattr(self, 'cur') and self.cur:
			self.cur.close()
		if hasattr(self, 'conn') and self.conn:
			# Rollback any pending transaction if the connection is closed without explicit commit/rollback
			try:
				if self.conn.is_connected() and not self.conn.autocommit: # Check if in transaction
					# This check might be tricky depending on driver specifics for "in transaction"
					# A simple check is if there are uncommitted changes, but that's hard to query directly.
					# For now, we assume if autocommit is off, any operation might have started a transaction.
					# A more robust way is to track transaction state within the class if needed.
					# self.conn.rollback() # Potentially rollback if not committed
					pass # Let get_db handle final rollback on close if needed
			except mariadb.Error as e:
				print(f'Error during implicit rollback on close: {e}')
			finally:
				self.conn.close()
		print('Database connection closed.')


	def commit(self):
		"""Commits the current transaction."""
		try:
			self.conn.commit()
		except mariadb.Error as e:
			print(f'Error during commit: {e}')
			raise # Re-raise the error to be handled by the caller or get_db

	def rollback(self):
		"""Rolls back the current transaction."""
		try:
			self.conn.rollback()
		except mariadb.Error as e:
			print(f'Error during rollback: {e}')
			# Don't typically re-raise here as rollback is often in an except block already
			# However, the caller might want to know if rollback failed.

	# --- Internal query helpers ---

	def _fetch_one(self, _query: str, _params: tuple = (), /) -> DictRow | None:
		"""
		Executes a query and fetches a single row.

		Args:
			_query: The SQL query string.
			_params: A tuple of parameters for the query.

		Returns:
			A dictionary representing the row, or None if no row is found or an error occurs.
		"""
		try:
			self.cur.execute(_query, _params)
			row: tuple | None = self.cur.fetchone()

			if row is None:
				return None

			columns: list[str] = [desc[0] for desc in self.cur.description or []]
			return dict(zip(columns, row))

		except mariadb.Error as e:
			print(f'DB error in _fetch_one: {e}')
			# Do not rollback here, as this is a read operation
			return None
		except Exception as e:
			print(f'Unexpected error in _fetch_one: {e}')
			return None

	def _fetch_all(self, _query: str, _params: tuple = (), /) -> list[DictRow] | None:
		"""
		Executes a query and fetches all rows.

		Args:
			_query: The SQL query string.
			_params: A tuple of parameters for the query.

		Returns:
			A list of dictionaries representing the rows, or an empty list if no rows are found.
			Returns None if a database error occurs.
		"""
		try:
			self.cur.execute(_query, _params)
			rows: list[tuple] | None = self.cur.fetchall()

			if not rows:
				return []

			columns: list[str] = [desc[0] for desc in self.cur.description or []]
			return [dict(zip(columns, row)) for row in rows]

		except mariadb.Error as e:
			print(f'DB error in _fetch_all: {e}')
			return None
		except Exception as e:
			print(f'Unexpected error in _fetch_all: {e}')
			return None

	def _execute(self, _query: str, _params: tuple = (), /, *, _returnLastId: bool = False) -> int | Id | None:
		"""
		Executes a given SQL query (INSERT, UPDATE, DELETE) without committing or rolling back.
		The calling public method is responsible for transaction management.

		Args:
			_query: The SQL query string.
			_params: A tuple of parameters for the query.
			_returnLastId: If True, returns the last inserted row ID. Otherwise, returns the number of affected rows.

		Returns:
			The last inserted row ID (as Id) if _returnLastId is True and insert was successful.
			The number of affected rows for other operations.
			None if _returnLastId is True and no row was inserted/affected.
			Raises mariadb.Error on database execution errors.
		"""
		self.cur.execute(_query, _params)
		affected_rows: int = self.cur.rowcount

		if _returnLastId:
			return self.cur.lastrowid if affected_rows > 0 and self.cur.lastrowid is not None else None
		return affected_rows


	# --- Account Management ---

	def get_account(
		self,
		*,
		_accountId: Id | None = None,
		_email: str | None = None
	) -> DictRow | None:
		"""
		Retrieves a single account by its ID or email.

		Args:
			_accountId: The ID of the account to retrieve.
			_email: The email of the account to retrieve.
					Exactly one of _accountId or _email must be provided.

		Returns:
			A dictionary containing account data if found, otherwise None.

		Raises:
			ValueError: If neither or both _accountId and _email are provided.
		"""
		args_num = sum(x is not None for x in [_accountId, _email])

		if args_num == 0:
			raise ValueError('Must provide exactly one of: _accountId or _email')
		elif args_num > 1:
			raise ValueError('Keyword arguments _accountId and _email are mutually exclusive')

		if _accountId is not None:
			query = '''
				SELECT accountID, email, password, firstname, lastname, creationDate, role, status
				FROM Account
				WHERE accountID = %s
			'''
			params = (_accountId,)
		else: # _email is not None
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
		_role: Role | None = None,
		_status: Status | None = None,
		_olderThanDays: int | None = None
	) -> list[DictRow] | None:
		"""
		Retrieves multiple accounts based on optional filtering criteria.

		Args:
			_role: Filter accounts by role.
			_status: Filter accounts by status.
			_olderThanDays: Filter accounts created earlier than this many days ago.

		Returns:
			A list of dictionaries, each representing an account, or None if an error occurs.
			Returns an empty list if no accounts match the criteria.
		"""
		query = '''
			SELECT accountID, email, firstname, lastname, creationDate, role, status
			FROM Account
		'''
		conditions: list[str] = []
		params_list: list[Any] = []

		if _role is not None:
			conditions.append('role = %s')
			params_list.append(_role.value)

		if _status is not None:
			conditions.append('status = %s')
			params_list.append(_status.value)

		if _olderThanDays is not None:
			conditions.append('creationDate < DATE_SUB(CURDATE(), INTERVAL %s DAY)')
			params_list.append(_olderThanDays)

		if conditions:
			query += ' WHERE ' + ' AND '.join(conditions)

		return self._fetch_all(query, tuple(params_list))

	def create_account(
		self,
		_email: str,
		_password: str,
		_role: Role = Role.GUEST,
		/,
		_firstName: str | None = None,
		_lastName: str | None = None,
		*,
		_creationDate: datetime = datetime.now()
	) -> Id | None:
		"""
		Creates a new account.

		Args:
			_email: The email for the new account.
			_password: The hashed password for the new account.
			_role: The role for the new account (defaults to GUEST).
			_firstName: Optional first name.
			_lastName: Optional last name.
			_creationDate: Optional creation date (defaults to datetime.now()).

		Returns:
			The accountID of the newly created account, or None if creation failed.
		"""
		creation_date_str = _creationDate.strftime('%Y-%m-%d %H:%M:%S')
		query = '''
			INSERT INTO Account (email, password, firstname, lastname, creationDate, role)
			VALUES (%s, %s, %s, %s, %s, %s)
		'''
		params = (_email, _password, _firstName, _lastName, creation_date_str, _role.value)
		try:
			account_id = self._execute(query, params, _returnLastId=True)
			self.commit()
			return account_id
		except Exception as e:
			print(f'Error in create_account: {e}')
			self.rollback()
			raise # Re-raise the exception to be handled by the caller or get_db

	def update_account(self, _accountId: Id, /, **_fields: Any) -> int | None:
		"""
		Updates specified fields for an existing account.

		Args:
			_accountId: The ID of the account to update.
			_fields: Keyword arguments where keys are column names and values are the new values.
					 Allowed fields: 'email', 'password', 'firstname', 'lastname', 'role', 'status'.
					 'creationDate' and 'accountID' cannot be updated via this method.

		Returns:
			The number of affected rows (should be 1 if successful, 0 if no change or not found).

		Raises:
			ValueError: If no valid fields to update are provided.
		"""
		allowed_fields = {'email', 'password', 'firstname', 'lastname', 'role', 'status'}
		valid_fields = {k: v for k, v in _fields.items() if k in allowed_fields}

		if not valid_fields:
			raise ValueError('No valid fields to update')

		if 'role' in valid_fields and isinstance(valid_fields['role'], Role):
			valid_fields['role'] = valid_fields['role'].value
		if 'status' in valid_fields and isinstance(valid_fields['status'], Status):
			valid_fields['status'] = valid_fields['status'].value

		set_clause = ', '.join(f'{key} = %s' for key in valid_fields)
		params = tuple(valid_fields.values()) + (_accountId,)
		query = f'UPDATE Account SET {set_clause} WHERE accountID = %s'

		try:
			affected_rows = self._execute(query, params)
			self.commit()
			return affected_rows
		except Exception as e:
			print(f'Error in update_account: {e}')
			self.rollback()
			raise

	def delete_accounts(self, _accountIds: set[Id], /) -> int | None:
		"""
		Deletes one or more accounts by their IDs.

		Args:
			_accountIds: A set of account IDs to delete.

		Returns:
			The number of accounts successfully deleted. Returns 0 if _accountIds is empty.
		"""
		if not _accountIds:
			return 0

		placeholders = ', '.join(['%s'] * len(_accountIds))
		query = f'DELETE FROM Account WHERE accountID IN ({placeholders})'
		try:
			affected_rows = self._execute(query, tuple(_accountIds))
			self.commit()
			return affected_rows
		except Exception as e:
			print(f'Error in delete_accounts: {e}')
			self.rollback()
			raise

	# --- Address Management ---

	def create_address(self, _accountId: Id, _location: str, /) -> Id | None:
		"""
		Creates a new address for a given account.

		Args:
			_accountId: The ID of the account this address belongs to.
			_location: The location description of the address.

		Returns:
			The addressID of the newly created address.
		"""
		query = '''
			INSERT INTO Address (accountID, location)
			VALUES (%s, %s)
		'''
		try:
			address_id = self._execute(query, (_accountId, _location), _returnLastId=True)
			self.commit()
			return address_id
		except Exception as e:
			print(f'Error in create_address: {e}')
			self.rollback()
			raise

	def get_addresses(self, _accountId: Id, /) -> list[DictRow] | None:
		"""
		Retrieves all addresses associated with a given account.

		Args:
			_accountId: The ID of the account.

		Returns:
			A list of dictionaries, each representing an address. Returns empty list if none.
		"""
		query = '''
			SELECT addressID, accountID, location
			FROM Address
			WHERE accountID = %s
		'''
		return self._fetch_all(query, (_accountId,))

	def modify_address(self, _addressId: Id, _location: str, /) -> int | None:
		"""
		Modifies the location of an existing address.

		Args:
			_addressId: The ID of the address to modify.
			_location: The new location description.

		Returns:
			The number of affected rows (1 if successful, 0 if not found).
		"""
		query = 'UPDATE Address SET location = %s WHERE addressID = %s'
		try:
			affected_rows = self._execute(query, (_location, _addressId))
			self.commit()
			return affected_rows
		except Exception as e:
			print(f'Error in modify_address: {e}')
			self.rollback()
			raise

	def delete_address(self, _addressId: Id, /) -> int | None:
		"""
		Deletes an address by its ID.

		Args:
			_addressId: The ID of the address to delete.

		Returns:
			The number of affected rows (1 if successful).
		"""
		query = 'DELETE FROM Address WHERE addressID = %s'
		try:
			affected_rows = self._execute(query, (_addressId,))
			self.commit()
			return affected_rows
		except Exception as e:
			print(f'Error in delete_address: {e}')
			self.rollback()
			raise

	# --- Product Management ---

	def add_product(
		self,
		_name: str,
		_description: str,
		_price: float = 9999999999,
		/,
		_stock: int = 0,
		_available: int = 0,
		*,
		_creationDate: datetime = datetime.now(),
		_discontinued: bool = False
	) -> Id | None:
		"""
		Adds a new product to the database.

		Args:
			_name: Name of the product.
			_description: Description of the product.
			_price: Price of the product.
			_stock: Current quantity in stock (defaults to 0).
			_available: Quantity available for purchase (defaults to 0).
			_creationDate: Date of product creation (defaults to now).
			_discontinued: Whether the product is discontinued (defaults to False).

		Returns:
			The productID of the newly added product.
		"""
		creation_date_str = _creationDate.strftime('%Y-%m-%d %H:%M:%S')
		discontinued_int = 1 if _discontinued else 0

		query = '''
			INSERT INTO Product (name, description, price, stock, available, creationDate, discontinued)
			VALUES (%s, %s, %s, %s, %s, %s, %s)
		'''
		params = (_name, _description, _price, _stock, _available, creation_date_str, discontinued_int)
		try:
			product_id = self._execute(query, params, _returnLastId=True)
			self.commit()
			return product_id
		except Exception as e:
			print(f'Error in add_product: {e}')
			self.rollback()
			raise

	def get_product(self, _productId: Id) -> DictRow | None:
		"""
		Retrieves a single product by its ID.

		Args:
			_productId: The ID of the product to retrieve.

		Returns:
			A dictionary containing product data if found, otherwise None.
		"""
		query = '''
			SELECT productID, name, description, price, stock, available, creationDate, discontinued
			FROM Product
			WHERE productID = %s
		'''
		return self._fetch_one(query, (_productId,))

	def update_product(self, _productId: Id, /, **_fields: Any) -> int | None:
		"""
		Updates specified fields for an existing product.

		Args:
			_productId: The ID of the product to update.
			_fields: Keyword arguments for fields to update.
					 Allowed fields: 'name', 'description', 'price', 'stock', 'available', 'discontinued'.

		Returns:
			The number of affected rows.
		"""
		allowed_fields = {'name', 'description', 'price', 'stock', 'available', 'discontinued'}
		valid_fields = {k: v for k, v in _fields.items() if k in allowed_fields}

		if not valid_fields:
			raise ValueError('No valid fields provided for update_product.')

		if 'discontinued' in valid_fields:
			valid_fields['discontinued'] = 1 if valid_fields['discontinued'] else 0

		set_clause = ', '.join(f'{key} = %s' for key in valid_fields)
		params = tuple(valid_fields.values()) + (_productId,)
		query = f'UPDATE Product SET {set_clause} WHERE productID = %s'
		try:
			affected_rows = self._execute(query, params)
			self.commit()
			return affected_rows
		except Exception as e:
			print(f'Error in update_product: {e}')
			self.rollback()
			raise

	def set_product_discontinued(self, _productId: Id, _state: bool = True, /) -> int | None:
		"""
		Sets the discontinued status of a product.

		Args:
			_productId: The ID of the product.
			_state: True to mark as discontinued, False to mark as not discontinued.

		Returns:
			The number of affected rows.
		"""
		discontinued_int = 1 if _state else 0
		query = 'UPDATE Product SET discontinued = %s WHERE productID = %s'
		try:
			affected_rows = self._execute(query, (discontinued_int, _productId))
			self.commit()
			return affected_rows
		except Exception as e:
			print(f'Error in set_product_discontinued: {e}')
			self.rollback()
			raise

	def get_product_images(self, _productId: Id, /) -> list[str] | None:
		"""
		Retrieves all image URLs for a given product.

		Args:
			_productId: The ID of the product.

		Returns:
			A list of image URLs. Returns empty list if none.
		"""
		query = '''
			SELECT i.url
			FROM Image i
			JOIN `Product-Image` pi ON i.imageID = pi.imageID
			WHERE pi.productID = %s
		'''
		result = self._fetch_all(query, (_productId,))
		if result is None:
			return None # Error case from _fetch_all
		return [row['url'] for row in result]

	def get_products(self, _tags: list[str] | None = None, /) -> list[DictRow] | None:
		"""
		Retrieves products. If tags are provided, retrieves products matching ALL specified tags.
		If no tags are provided, retrieves all products.

		Args:
			_tags: A list of tag names to filter by.

		Returns:
			A list of dictionaries, each representing a product. Returns empty list if none.
		"""
		if not _tags:
			query = '''
				SELECT productID, name, description, price, stock, available, creationDate, discontinued
				FROM Product
			'''
			params = ()
		else:
			num_tags = len(_tags)
			placeholders = ', '.join(['%s'] * num_tags)
			query = f'''
				SELECT p.productID, p.name, p.description, p.price,
					   p.stock, p.available, p.creationDate, p.discontinued
				FROM Product p
				JOIN `Product-Tag` pt ON p.productID = pt.productID
				JOIN `Tag` t ON pt.tagID = t.tagID
				WHERE t.name IN ({placeholders})
				GROUP BY p.productID
				HAVING COUNT(DISTINCT t.tagID) = %s
			'''
			params = tuple(_tags) + (num_tags,)
		return self._fetch_all(query, params)

	def get_products_with_tagIDs(self, _tagIds: set[Id] | None = None, /) -> list[DictRow] | None:
		"""
		Retrieves products. If tag IDs are provided, retrieves products matching ALL specified tag IDs.
		If no tag IDs are provided (None or empty set), retrieves all products.

		Args:
			_tagIds: A set of tag IDs to filter by. Can be None or empty to get all products.

		Returns:
			A list of dictionaries, each representing a product. Returns empty list if no products match.
			Returns None if a database error occurs.
		"""
		if not _tagIds:
			query = '''
				SELECT productID, name, description, price, stock, available, creationDate, discontinued
				FROM Product
			'''
			params = ()
		else:
			num_tags = len(_tagIds)
			placeholders = ', '.join(['%s'] * num_tags)
			query = f'''
				SELECT p.productID, p.name, p.description, p.price,
						p.stock, p.available, p.creationDate, p.discontinued
				FROM Product p
				JOIN `Product-Tag` pt ON p.productID = pt.productID
				WHERE pt.tagID IN ({placeholders})
				GROUP BY p.productID, p.name, p.description, p.price, p.stock, p.available, p.creationDate, p.discontinued
				HAVING COUNT(DISTINCT pt.tagID) = %s
			'''
			params = tuple(_tagIds) + (num_tags,)

		return self._fetch_all(query, params)

	# --- Tag Management ---

	def create_tag(self, _name: str, /) -> Id | None:
		"""
		Creates a new tag.

		Args:
			_name: The name of the tag.

		Returns:
			The tagID of the newly created tag.
		"""
		query = 'INSERT INTO Tag (name) VALUES (%s)'
		try:
			tag_id = self._execute(query, (_name,), _returnLastId=True)
			self.commit()
			return tag_id
		except mariadb.IntegrityError:
			self.rollback() # Rollback if integrity error (e.g. duplicate name)
			print(f'Tag with name \'{_name}\' likely already exists.')
			raise # Re-raise to signal failure
		except Exception as e:
			print(f'Error in create_tag: {e}')
			self.rollback()
			raise

	def get_tag_id(self, _name: str, /) -> Id | None:
		"""
		Retrieves the ID of a tag by its name.

		Args:
			_name: The name of the tag.

		Returns:
			The tagID if found, otherwise None.
		"""
		query = 'SELECT tagID FROM `Tag` WHERE name = %s'
		result = self._fetch_one(query, (_name,))
		return result['tagID'] if result else None

	def get_all_tags(self) -> list[DictRow] | None:
		"""
		Retrieves all tags from the database.

		Returns:
			A list of dictionaries, each representing a tag (tagID, name). Returns empty list if none.
		"""
		query = 'SELECT tagID, name FROM Tag'
		return self._fetch_all(query)

	def delete_tag(self, _tagId: Id, /) -> int | None:
		"""
		Deletes a tag by its ID. Associated entries in Product-Tag will be cascade deleted.

		Args:
			_tagId: The ID of the tag to delete.

		Returns:
			The number of affected rows (1 if successful).
		"""
		query = 'DELETE FROM Tag WHERE tagID = %s'
		try:
			affected_rows = self._execute(query, (_tagId,))
			self.commit()
			return affected_rows
		except Exception as e:
			print(f'Error in delete_tag: {e}')
			self.rollback()
			raise

	def add_tag_to_product(self, _productId: Id, _tagId: Id, /) -> int | None:
		"""
		Associates a tag with a product.

		Args:
			_productId: The ID of the product.
			_tagId: The ID of the tag.

		Returns:
			The number of affected rows (1 if successful).
		"""
		query = 'INSERT INTO `Product-Tag` (productID, tagID) VALUES (%s, %s)'
		try:
			affected_rows = self._execute(query, (_productId, _tagId))
			self.commit()
			return affected_rows
		except mariadb.IntegrityError:
			self.rollback()
			print(f'Product {_productId} already has tag {_tagId} or one of the IDs is invalid.')
			raise
		except Exception as e:
			print(f'Error in add_tag_to_product: {e}')
			self.rollback()
			raise

	def remove_tag_from_product(self, _productId: Id, _tagId: Id, /) -> int | None:
		"""
		Removes a tag association from a product.

		Args:
			_productId: The ID of the product.
			_tagId: The ID of the tag.

		Returns:
			The number of affected rows (1 if successful).

		Raises:
			ValueError: If the tag is not associated with the product.
		"""
		query = 'DELETE FROM `Product-Tag` WHERE productID = %s AND tagID = %s'
		try:
			affected_rows = self._execute(query, (_productId, _tagId))
			if affected_rows == 0:
				self.rollback() # Nothing was changed, but good practice
				raise ValueError(f'Tag ID {_tagId} is not associated with Product ID {_productId}.')
			self.commit()
			return affected_rows
		except Exception as e:
			print(f'Error in remove_tag_from_product: {e}')
			self.rollback()
			raise

	# --- Image Management ---

	def add_image_to_product(self, _url: str, _productId: Id, /) -> Id | None:
		"""
		Adds an image and associates it with a product. This is an atomic operation.

		Args:
			_url: The URL of the image.
			_productId: The ID of the product to associate the image with.

		Returns:
			The imageID of the newly added image if successful.
		"""
		try:
			image_query = 'INSERT INTO Image (url) VALUES (%s)'
			image_id = self._execute(image_query, (_url,), _returnLastId=True)

			if image_id is None: # Should not happen if _execute works as expected and insert is valid
				raise Exception('Failed to create image entry, image_id is None.')

			link_query = 'INSERT INTO `Product-Image` (productID, imageID) VALUES (%s, %s)'
			link_result = self._execute(link_query, (_productId, image_id))

			if link_result is None or link_result == 0:
				raise Exception(f'Failed to link image {image_id} to product {_productId}.')

			self.commit()
			return image_id
		except Exception as e:
			print(f'Error in add_image_to_product: {e}')
			self.rollback()
			raise

	def delete_image(self, _imageId: Id, /) -> int | None:
		"""
		Deletes an image by its ID. Associated entries in Product-Image will be cascade deleted.

		Args:
			_imageId: The ID of the image to delete.

		Returns:
			The number of affected rows (1 if successful).
		"""
		query = 'DELETE FROM Image WHERE imageID = %s'
		try:
			affected_rows = self._execute(query, (_imageId,))
			self.commit()
			return affected_rows
		except Exception as e:
			print(f'Error in delete_image: {e}')
			self.rollback()
			raise

	# --- Trolley & Line Item Management ---

	def get_trolley(self, _accountId: Id, /) -> list[DictRow] | None:
		"""
		Retrieves all line items in an account's trolley.

		Args:
			_accountId: The ID of the account.

		Returns:
			A list of dictionaries, each representing a line item in the trolley. Empty list if none.
		"""
		query = '''
			SELECT li.lineItemID, li.productID, p.name as productName,
				   li.quantity, li.priceAtSale, p.price as currentPrice
			FROM Trolley t
			JOIN LineItem li ON t.lineItemID = li.lineItemID
			JOIN Product p ON li.productID = p.productID
			WHERE t.accountID = %s
		'''
		return self._fetch_all(query, (_accountId,))

	def add_to_trolley(self, _accountId: Id, _productId: Id, /, *, _quantity: int = 1) -> Id | None:
		"""
		Adds a product to an account's trolley. This is an atomic operation.

		Args:
			_accountId: The ID of the account.
			_productId: The ID of the product to add.
			_quantity: The quantity of the product to add.

		Returns:
			The lineItemID of the newly created line item if successful.

		Raises:
			ValueError: If _quantity is less than 1.
		"""
		if _quantity < 1:
			raise ValueError('Quantity must be at least 1.')
		try:
			line_item_query = 'INSERT INTO LineItem (productID, quantity) VALUES (%s, %s)'
			line_item_id = self._execute(line_item_query, (_productId, _quantity), _returnLastId=True)

			if line_item_id is None:
				raise Exception('Failed to create line item, line_item_id is None.')

			trolley_query = 'INSERT INTO Trolley (accountID, lineItemID) VALUES (%s, %s)'
			trolley_add_result = self._execute(trolley_query, (_accountId, line_item_id))

			if trolley_add_result is None or trolley_add_result == 0:
				raise Exception(f'Failed to add line item {line_item_id} to trolley for account {_accountId}.')

			self.commit()
			return line_item_id
		except Exception as e:
			print(f'Error in add_to_trolley: {e}')
			self.rollback()
			raise

	def change_quantity_of_product_in_trolley(
		self, _accountId: Id, _productId: Id, _newQuantity: int, /
	) -> int | None:
		"""
		Changes the quantity of a product in an account's trolley.
		If _newQuantity is 0 or less, the item is removed from the trolley.

		Args:
			_accountId: The ID of the account.
			_productId: The ID of the product whose quantity is to be changed.
			_newQuantity: The new quantity.

		Returns:
			The number of affected LineItem rows (1 if quantity updated).
			If item removed, returns result of remove_from_trolley.

		Raises:
			ValueError: If _newQuantity is less than 1.
						If the product is not found in the account's trolley.
		"""
		if _newQuantity < 1:
			raise ValueError('New quantity must be at least 1.')

		try:
			find_query = """
				SELECT t.lineItemID
				FROM Trolley t
				JOIN LineItem li ON t.lineItemID = li.lineItemID
				WHERE t.accountID = %s AND li.productID = %s
			"""
			item = self._fetch_one(find_query, (_accountId, _productId))

			if not item:
				raise ValueError(f'Product ID {_productId} not found in trolley for account ID {_accountId}.')

			line_item_id: Id = item['lineItemID']

			update_query = 'UPDATE LineItem SET quantity = %s WHERE lineItemID = %s'
			affected_rows = self._execute(update_query, (_newQuantity, line_item_id))
			self.commit()
			return affected_rows
		except Exception as e:
			print(f'Error in change_quantity_of_product_in_trolley: {e}')
			self.rollback()
			raise

	def remove_from_trolley(self, _accountId: Id, _lineItemId: Id, /) -> tuple[int, int] :
		"""
		Removes a specific line item from an account's trolley and deletes the line item itself.
		This is an atomic operation.

		Args:
			_accountId: The ID of the account.
			_lineItemId: The ID of the line item to remove.

		Returns:
			A tuple containing: (affected rows from Trolley deletion, affected rows from LineItem deletion).
			Typically (1, 1) on success.

		Raises:
			ValueError: If the line item is not found in the specified account's trolley.
		"""
		try:
			trolley_check_query = 'SELECT 1 FROM Trolley WHERE accountID = %s AND lineItemID = %s'
			if not self._fetch_one(trolley_check_query, (_accountId, _lineItemId)):
				raise ValueError(f'LineItem ID {_lineItemId} not found in trolley for account ID {_accountId}.')

			trolley_delete_res = self._execute('DELETE FROM Trolley WHERE accountID = %s AND lineItemID = %s', (_accountId, _lineItemId))
			if trolley_delete_res is None or trolley_delete_res == 0: # Should be 1 if check passed
				raise Exception(f'Failed to delete LineItem ID {_lineItemId} from Trolley for account ID {_accountId}.')


			line_item_delete_res = self._execute('DELETE FROM LineItem WHERE lineItemID = %s', (_lineItemId,))
			if line_item_delete_res is None or line_item_delete_res == 0: # Should be 1
				raise Exception(f'Failed to delete LineItem ID {_lineItemId} from LineItem table.')

			self.commit()
			return (trolley_delete_res, line_item_delete_res)
		except Exception as e:
			print(f'Error in remove_from_trolley: {e}')
			self.rollback()
			raise

	def clear_trolley(self, _accountId: Id, /) -> int | None:
		"""
		Clears all items from an account's trolley.
		This involves deleting entries from the Trolley table and also deleting the associated LineItems
		that are not part of any existing order. This is an atomic operation.

		Args:
			_accountId: The ID of the account whose trolley is to be cleared.

		Returns:
			The number of LineItems successfully deleted from the LineItem table.
		"""
		try:
			trolley_items_query = 'SELECT lineItemID FROM Trolley WHERE accountID = %s'
			trolley_items_result = self._fetch_all(trolley_items_query, (_accountId,))

			if trolley_items_result is None: # Error fetching
				raise Exception(f'Failed to fetch trolley items for account {_accountId}.')
			if not trolley_items_result: # Trolley is empty
				return 0

			line_item_ids_in_trolley = [item['lineItemID'] for item in trolley_items_result]
			placeholders = ', '.join(['%s'] * len(line_item_ids_in_trolley))

			delete_trolley_query = f'DELETE FROM Trolley WHERE accountID = %s AND lineItemID IN ({placeholders})'
			params_trolley = (_accountId,) + tuple(line_item_ids_in_trolley)
			trolley_deleted_count = self._execute(delete_trolley_query, params_trolley)

			if trolley_deleted_count is None:
				raise Exception(f'Error clearing trolley entries for account {_accountId}.')

			delete_line_items_query = f'''
				DELETE FROM LineItem
				WHERE lineItemID IN ({placeholders})
				AND lineItemID NOT IN (SELECT DISTINCT lineItemID FROM OrderItem)
			'''
			line_items_deleted_count = self._execute(delete_line_items_query, tuple(line_item_ids_in_trolley))

			if line_items_deleted_count is None:
				raise Exception(f'Error deleting orphaned line items for account {_accountId} after trolley clear.')

			self.commit()
			return line_items_deleted_count
		except Exception as e:
			print(f'Error in clear_trolley: {e}')
			self.rollback()
			raise

	# --- Order Management ---

	def create_order(self, _accountId: Id, _addressId: Id, /) -> Id | None:
		"""
		Creates an order for an account using all items currently in their trolley.
		Sets `priceAtSale` for each line item and moves items from trolley to order.
		This is an atomic operation.

		Args:
			_accountId: The ID of the account placing the order.
			_addressId: The ID of the address for the order.

		Returns:
			The orderID of the newly created order.

		Raises:
			ValueError: If the specified address does not belong to the account,
						or if the trolley is empty.
			Exception: If any database operation fails during order creation.
		"""
		try:
			address_check_query = 'SELECT 1 FROM Address WHERE addressID = %s AND accountID = %s'
			if not self._fetch_one(address_check_query, (_addressId, _accountId)):
				raise ValueError(f'Address ID {_addressId} does not belong to account ID {_accountId}.')

			trolley_line_items = self.get_trolley(_accountId) # This is a read, doesn't need explicit transaction part here
			if trolley_line_items is None:
				raise Exception(f'Error fetching trolley for account {_accountId} during order creation.')
			if not trolley_line_items:
				raise ValueError(f'Trolley is empty for account {_accountId}. Cannot create order.')

			# Start of transactional operations
			for item in trolley_line_items:
				line_item_id: Id = item['lineItemID']
				product_id: Id = item['productID']
				product_info = self.get_product(product_id) # Read operation

				if not product_info or product_info['price'] is None:
					raise Exception(f'Could not fetch price for product {product_id}. Aborting order.')
				current_price = product_info['price']

				update_price_query = 'UPDATE LineItem SET priceAtSale = %s WHERE lineItemID = %s'
				update_res = self._execute(update_price_query, (current_price, line_item_id))
				if update_res is None or update_res == 0:
					raise Exception(f'Failed to update priceAtSale for lineItem {line_item_id}.')

			order_query = '''
				INSERT INTO `Order` (accountID, addressID, date)
				VALUES (%s, %s, %s)
			'''
			order_id = self._execute(order_query, (_accountId, _addressId, datetime.now()), _returnLastId=True)

			if order_id is None:
				raise Exception('Failed to create order entry.')

			line_item_ids_in_order: list[Id] = []
			for item in trolley_line_items:
				line_item_id: Id = item['lineItemID']
				link_query = 'INSERT INTO OrderItem (orderID, lineItemID) VALUES (%s, %s)'
				link_res = self._execute(link_query, (order_id, line_item_id))
				if link_res is None or link_res == 0:
					raise Exception(f'Failed to link lineItem {line_item_id} to order {order_id}.')
				line_item_ids_in_order.append(line_item_id)

			if line_item_ids_in_order:
				placeholders = ', '.join(['%s'] * len(line_item_ids_in_order))
				clear_trolley_query = f'DELETE FROM Trolley WHERE accountID = %s AND lineItemID IN ({placeholders})'
				params_clear = (_accountId,) + tuple(line_item_ids_in_order)
				clear_res = self._execute(clear_trolley_query, params_clear)
				if clear_res is None or clear_res != len(line_item_ids_in_order):
					# Check if the number of cleared items matches expected
					raise Exception(f'Failed to clear all ordered items from trolley for account {_accountId}. Expected {len(line_item_ids_in_order)}, got {clear_res}.')

			self.commit()
			return order_id
		except Exception as e:
			print(f'Error in create_order: {e}')
			self.rollback()
			raise

	# --- Invoice Management ---

	def save_invoice(self, _accountId: Id, _orderId: Id, _data: bytes, /) -> Id | None:
		"""
		Saves invoice data for an order.

		Args:
			_accountId: The ID of the account associated with the invoice.
			_orderId: The ID of the order this invoice is for.
			_data: The invoice data (e.g., PDF bytes).

		Returns:
			The invoiceID of the saved invoice.
		"""
		query = '''
			INSERT INTO Invoice (accountID, orderID, creationDate, data)
			VALUES (%s, %s, %s, %s)
		'''
		try:
			invoice_id = self._execute(query, (_accountId, _orderId, datetime.now(), _data), _returnLastId=True)
			self.commit()
			return invoice_id
		except Exception as e:
			print(f'Error in save_invoice: {e}')
			self.rollback()
			raise

	def get_invoice(self, _invoiceId: Id, /) -> DictRow | None:
		"""
		Retrieves invoice data by its ID.

		Args:
			_invoiceId: The ID of the invoice.

		Returns:
			A dictionary containing invoice data, or None if not found or error.
		"""
		query = '''
			SELECT invoiceID, accountID, orderID, creationDate, data
			FROM Invoice
			WHERE invoiceID = %s
		'''
		return self._fetch_one(query, (_invoiceId,))

	# --- Receipt Management ---

	def save_receipt(self, _accountId: Id, _orderId: Id, _data: bytes, /) -> Id | None:
		"""
		Saves receipt data for an order.

		Args:
			_accountId: The ID of the account associated with the receipt.
			_orderId: The ID of the order this receipt is for.
			_data: The receipt data (e.g., PDF bytes).

		Returns:
			The receiptID of the saved receipt.
		"""
		query = '''
			INSERT INTO Receipt (accountID, orderID, creationDate, data)
			VALUES (%s, %s, %s, %s)
		'''
		try:
			receipt_id = self._execute(query, (_accountId, _orderId, datetime.now(), _data), _returnLastId=True)
			self.commit()
			return receipt_id
		except Exception as e:
			print(f'Error in save_receipt: {e}')
			self.rollback()
			raise

	def get_receipt(self, _receiptId: Id, /) -> DictRow | None:
		"""
		Retrieves receipt data by its ID.

		Args:
			_receiptId: The ID of the receipt.

		Returns:
			A dictionary containing receipt data, or None if not found or error.
		"""
		query = '''
			SELECT receiptID, accountID, orderID, creationDate, data
			FROM Receipt
			WHERE receiptID = %s
		'''
		return self._fetch_one(query, (_receiptId,))

	# --- Report Management ---

	def save_report(self, _creatorId: Id, _data: bytes, /) -> Id | None:
		"""
		Saves report data.

		Args:
			_creatorId: The accountID of the user who created the report.
			_data: The report data (e.g., PDF or CSV bytes).

		Returns:
			The reportID of the saved report.
		"""
		query = '''
			INSERT INTO Report (creator, creationDate, data)
			VALUES (%s, %s, %s)
		'''
		try:
			report_id = self._execute(query, (_creatorId, datetime.now(), _data), _returnLastId=True)
			self.commit()
			return report_id
		except Exception as e:
			print(f'Error in save_report: {e}')
			self.rollback()
			raise

	def get_report(self, _reportId: Id, /) -> DictRow | None:
		"""
		Retrieves report data by its ID.

		Args:
			_reportId: The ID of the report.

		Returns:
			A dictionary containing report data, or None if not found or error.
		"""
		query = '''
			SELECT reportID, creator, creationDate, data
			FROM Report
			WHERE reportID = %s
		'''
		return self._fetch_one(query, (_reportId,))

	# --- Utilities ---

	def get_enum_values(self, tableName: str, columnName: str) -> list[str] | None:
		"""
		Retrieves the possible enum values for a specified column.

		Args:
			tableName: The name of the table.
			columnName: The name of the ENUM column.

		Returns:
			A list of string enum values, or None if the column is not found or not an ENUM.
		"""
		query = '''
			SELECT COLUMN_TYPE
			FROM INFORMATION_SCHEMA.COLUMNS
			WHERE TABLE_SCHEMA = DATABASE()
			AND TABLE_NAME = %s
			AND COLUMN_NAME = %s
		'''
		result = self._fetch_one(query, (tableName, columnName))
		if not result:
			print(f'Column \'{columnName}\' in table \'{tableName}\' not found.')
			return None

		column_type: str = result['COLUMN_TYPE']
		if not column_type.lower().startswith('enum('):
			print(f'Column \'{columnName}\' in table \'{tableName}\' is not an ENUM type. Type: {column_type}')
			return None

		enum_str = column_type[column_type.find('(')+1 : column_type.rfind(')')]
		enum_values = [val.strip("'") for val in enum_str.split(',')]
		return enum_values


def get_db() -> Generator[Database, None, None]:
	"""
	FastAPI dependency generator for database sessions.
	Manages connection acquisition and release, and transaction rollback on exceptions.
	"""
	raw_conn: mariadb.Connection | None = None
	db_instance: Database | None = None

	try:
		raw_conn = Database.get_connection()
		db_instance = Database(raw_conn)
		yield db_instance
		# If yield was successful and no exceptions, assume commit was handled by methods or not needed.
		# If an unhandled exception occurs after yield and before finally,
		# the rollback in the finally block of this function will handle it.
	except Exception as e: # Catch all exceptions from the route handler or db methods
		if db_instance:
			try:
				db_instance.rollback()
				print(f'Transaction rolled back due to exception in get_db context: {e}')
			except Exception as rb_e:
				print(f'Error during rollback attempt in get_db: {rb_e}')
		if isinstance(e, HTTPException): # Re-raise HTTPExceptions
			raise
		# Wrap other exceptions in HTTPException for consistent error response
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f'An error occurred: {e}'
		)
	finally:
		if db_instance:
			db_instance.close()

# Example usage (optional, for testing)
if __name__ == '__main__':
	print('Running Database class example...')

	try:
		db_gen = get_db()
		db = next(db_gen)

		try:
			print('Successfully obtained database connection.')

			print('\n--- Testing get_enum_values ---')
			account_statuses = db.get_enum_values('Account', 'status')
			print(f'Account statuses: {account_statuses}')
			account_roles = db.get_enum_values('Account', 'role')
			print(f'Account roles: {account_roles}')

			print('\n--- Testing create_account ---')
			test_email = f'testuser_{datetime.now().timestamp()}@example.com'
			new_account_id = db.create_account(
				test_email,
				'hashed_password',
				Role.CUSTOMER,
				_firstName='Test',
				_lastName='User',
			)
			print(f'Created account ID: {new_account_id}')

			if new_account_id:
				print('\n--- Testing get_account ---')
				account = db.get_account(_accountId=new_account_id)
				print(f'Retrieved account: {account}')

				print('\n--- Testing update_account ---')
				updated_rows = db.update_account(new_account_id, _firstName='UpdatedTest', status=Status.ACTIVE.value)
				print(f'Updated account, rows affected: {updated_rows}')
				account_after_update = db.get_account(_accountId=new_account_id)
				print(f'Account after update: {account_after_update}')


				print('\n--- Testing Product and Tag Management ---')
				tag1_id = db.create_tag('ElectronicsTest')
				tag2_id = db.create_tag('GadgetTest')
				print(f'Created tags: {tag1_id}, {tag2_id}')

				product_id_1 = db.add_product('Test Laptop', 'A test laptop.', 999.99, 10, 5)
				print(f'Added product 1 ID: {product_id_1}')

				if product_id_1 and tag1_id and tag2_id:
					db.add_tag_to_product(product_id_1, tag1_id)
					db.add_tag_to_product(product_id_1, tag2_id)
					print(f'Added tags to product {product_id_1}')

					products_with_tags = db.get_products_with_tagIDs({tag1_id, tag2_id})
					print(f'Products with tags {tag1_id} & {tag2_id}: {products_with_tags}')

					try:
						db.remove_tag_from_product(product_id_1, tag1_id)
						print(f'Removed tag {tag1_id} from product {product_id_1}')
						# Try removing a non-existent tag association
						db.remove_tag_from_product(product_id_1, 99999) # Should raise ValueError
					except ValueError as ve:
						print(f'Caught expected error: {ve}')


				print('\n--- Testing Trolley and Order ---')
				address_id = db.create_address(new_account_id, '123 Test St, Testville')
				print(f'Created address ID: {address_id}')

				if product_id_1 and address_id:
					line_item_id = db.add_to_trolley(new_account_id, product_id_1, _quantity=2)
					print(f'Added product {product_id_1} to trolley, line item ID: {line_item_id}')

					db.change_quantity_of_product_in_trolley(new_account_id, product_id_1, 3)
					print('Changed quantity in trolley.')
					trolley_items = db.get_trolley(new_account_id)
					print(f'Trolley contents: {trolley_items}')

					order_id = db.create_order(new_account_id, address_id)
					print(f'Created order with ID: {order_id}')
					trolley_after_order = db.get_trolley(new_account_id)
					print(f'Trolley contents after order: {trolley_after_order}') # Should be empty

					if order_id:
						invoice_id = db.save_invoice(new_account_id, order_id, b'Test invoice data')
						print(f'Saved invoice ID: {invoice_id}')
						retrieved_invoice = db.get_invoice(invoice_id) # type: ignore
						print(f'Retrieved invoice data length: {len(retrieved_invoice.get("data", b"")) if retrieved_invoice else "Not found"}')


				# Cleanup (optional, as schema drops tables on rerun)
				# if new_account_id:
				#     db.delete_accounts({new_account_id})
				#     print(f'Deleted account {new_account_id}')
				# if product_id_1:
				#     # db.delete_product(product_id_1) # Assuming a delete_product method
				#     pass
				# if tag1_id: db.delete_tag(tag1_id)
				# if tag2_id: db.delete_tag(tag2_id)


		except Exception as e:
			print(f'An error occurred during database operations: {e}')
			import traceback
			traceback.print_exc()
		finally:
			try:
				next(db_gen, None) # Trigger finally block in get_db for cleanup
			except StopIteration:
				pass

	except HTTPException as e:
		print(f'HTTPException (likely during pool init or connection): {e.detail}')
	except Exception as e:
		print(f'A critical error occurred: {e}')
		import traceback
		traceback.print_exc()

	print('\nExample run finished.')
