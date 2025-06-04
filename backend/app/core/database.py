from datetime import datetime
from enum import Enum
from typing import Any, Generator, TypeAlias

import mariadb
from fastapi import HTTPException, status

from ..utils.settings import SETTINGS


class MockSettings:
	database_username: str = 'admin'
	database_password: str = 'password'
	database_host: str = 'localhost'
	database_port: int = 3306
	database: str = 'awe_electronics'

SETTINGS = MockSettings()

# Type alias for database row representation
DictRow: TypeAlias = dict[str, Any]

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
			print(f"Attempting to create connection pool for database '{SETTINGS.database}' on {SETTINGS.database_host}:{SETTINGS.database_port}")
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
			assert cls.__pool is not None, "Connection pool is not initialized"
			return cls.__pool.get_connection()
		except mariadb.Error as e:
			print(f"Error getting connection from pool: {e}")
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail=f"Failed to get connection from database pool: {e}"
			)
		except AssertionError as e:
			print(f"Assertion error: {e}")
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

	def close(self):
		"""Closes the database cursor and connection."""
		if hasattr(self, 'cur') and self.cur:
			self.cur.close()
		if hasattr(self, 'conn') and self.conn:
			self.conn.close()
		print("Database connection closed.")

	def commit(self):
		"""Commits the current transaction."""
		self.conn.commit()

	def rollback(self):
		"""Rolls back the current transaction."""
		self.conn.rollback()

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
			A list of dictionaries representing the rows, or None if no rows are found or an error occurs.
			Returns an empty list if the query executes successfully but yields no rows.
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

	def _execute(self, _query: str, _params: tuple = (), /, *, _returnLastId: bool = False) -> int | None:
		"""
		Executes a given SQL query (INSERT, UPDATE, DELETE).

		Args:
			_query: The SQL query string.
			_params: A tuple of parameters for the query.
			_returnLastId: If True, returns the last inserted row ID (for INSERT statements). Otherwise, returns the number of affected rows.

		Returns:
			The last inserted row ID if _returnLastId is True and insert was successful.
			The number of affected rows for other operations (INSERT, UPDATE, DELETE).
			None if a database error occurs, or if _returnLastId is True and no row was inserted/affected.
		"""
		try:
			self.cur.execute(_query, _params)
			affected_rows: int = self.cur.rowcount
			self.commit()

			if _returnLastId:
				# lastrowid is only meaningful if rows were affected (e.g. an insert happened)
				return self.cur.lastrowid if affected_rows > 0 and self.cur.lastrowid is not None else None
			return affected_rows
		except mariadb.Error as e:
			print(f'DB error in _execute: {e}, rolling back')
			try:
				self.rollback()
			except Exception as rollback_error:
				print(f'Error during rollback: {rollback_error}')
			return None
		except Exception as e:
			print(f'Unexpected error in _execute: {e}, rolling back')
			try:
				self.rollback()
			except Exception as rollback_error:
				print(f'Error during rollback: {rollback_error}')
			return None

	# --- Account Management ---

	def get_account(
		self,
		*,
		_accountId: int | None = None,
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
			raise ValueError("Must provide exactly one of: _accountId or _email")
		elif args_num > 1:
			raise ValueError("Keyword arguments _accountId and _email are mutually exclusive")

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
			role: Filter accounts by role.
			status: Filter accounts by status.
			olderThanDays: Filter accounts created earlier than this many days ago.

		Returns:
			A list of dictionaries, each representing an account, or None if an error occurs.
			Returns an empty list if no accounts match the criteria.
		"""
		query = '''
			SELECT accountID, email, firstname, lastname, creationDate, role, status
			FROM Account
		'''
		conditions: list[str] = []
		params: list[Any] = []

		if _role is not None:
			conditions.append("role = %s")
			params.append(_role.value)

		if _status is not None:
			conditions.append("status = %s")
			params.append(_status.value)

		if _olderThanDays is not None:
			conditions.append("creationDate < DATE_SUB(CURDATE(), INTERVAL %s DAY)")
			params.append(_olderThanDays)

		if conditions:
			query += " WHERE " + " AND ".join(conditions)

		return self._fetch_all(query, tuple(params))

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
	) -> int | None:
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
		creation_date_str = _creationDate.strftime("%Y-%m-%d %H:%M:%S")

		# Always include all fields, using NULL for optional ones if not provided
		query = '''
			INSERT INTO Account (email, password, firstname, lastname, creationDate, role)
			VALUES (%s, %s, %s, %s, %s, %s)
		'''
		params = (_email, _password, _firstName, _lastName, creation_date_str, _role.value)

		return self._execute(query, params, _returnLastId=True)

	# NOTE Using dictonary args might be a bit fucky but it seems the best for the case.
	def update_account(self, _accountId: int, /, **_fields) -> int | None:
		"""
		Updates specified fields for an existing account.

		Args:
			_accountId: The ID of the account to update.
			_fields: Keyword arguments where keys are column names and values are the new values.
					 Allowed fields: 'email', 'password', 'firstname', 'lastname', 'role', 'status'.
					 'creationDate' and 'accountID' cannot be updated via this method.

		Returns:
			The number of affected rows (should be 1 if successful, 0 if no change or not found),
			or None if an error occurred or no valid fields were provided.
		"""
		allowed_fields = {'email', 'password', 'firstname', 'lastname', 'role', 'status'}
		valid_fields = {k: v for k, v in _fields.items() if k in allowed_fields}

		if not valid_fields:
			raise ValueError("No valid fields to update")

		# Convert Enum values if present
		if 'role' in valid_fields and isinstance(valid_fields['role'], Role):
			valid_fields['role'] = valid_fields['role'].value
		if 'status' in valid_fields and isinstance(valid_fields['status'], Status):
			valid_fields['status'] = valid_fields['status'].value

		set_clause = ', '.join(f'{key} = %s' for key in valid_fields)
		params = tuple(valid_fields.values()) + (_accountId,)

		query = f'UPDATE Account SET {set_clause} WHERE accountID = %s'
		return self._execute(query, params)

	def delete_accounts(self, _accountIds: set[int], /) -> int | None:
		"""
		Deletes one or more accounts by their IDs.
		Deleting an account deletes all associated addresses and the entry in the order will be set to null.

		Args:
			_accountIds: A set of account IDs to delete.

		Returns:
			The number of accounts successfully deleted, or None if an error occurred.
			Returns 0 if _accountIds is empty.
		"""
		if not _accountIds:
			return 0

		placeholders = ', '.join(['%s'] * len(_accountIds))
		query = f'DELETE FROM Account WHERE accountID IN ({placeholders})'
		return self._execute(query, tuple(_accountIds))

	# --- Address Management ---

	def create_address(self, _accountId: int, _location: str, /) -> int | None:
		"""
		Creates a new address for a given account.

		Args:
			_accountId: The ID of the account this address belongs to.
			_location: The location description of the address.

		Returns:
			The addressID of the newly created address, or None if creation failed.
		"""
		query = '''
			INSERT INTO Address (accountID, location)
			VALUES (%s, %s)
		'''
		return self._execute(query, (_accountId, _location), _returnLastId=True)

	def get_addresses(self, _accountId: int, /) -> list[DictRow] | None:
		"""
		Retrieves all addresses associated with a given account.

		Args:
			_accountId: The ID of the account.

		Returns:
			A list of dictionaries, each representing an address, or None if an error occurs.
			Returns an empty list if the account has no addresses.
		"""
		query = '''
			SELECT addressID, accountID, location
			FROM Address
			WHERE accountID = %s
		'''
		return self._fetch_all(query, (_accountId,))

	def modify_address(self, _addressId: int, _location: str, /) -> int | None:
		"""
		Modifies the location of an existing address.

		Args:
			_addressId: The ID of the address to modify.
			_location: The new location description.

		Returns:
			The number of affected rows (1 if successful, 0 if not found), or None on error.
		"""
		query = 'UPDATE Address SET location = %s WHERE addressID = %s'
		return self._execute(query, (_location, _addressId))

	def delete_address(self, _addressId: int, /) -> int | None:
		"""
		Deletes an address by its ID.

		Args:
			_addressId: The ID of the address to delete.

		Returns:
			The number of affected rows (1 if successful), or None on error.
		"""
		query = 'DELETE FROM Address WHERE addressID = %s'
		return self._execute(query, (_addressId,))

	# --- Product Management ---

	def add_product(
		self,
		_name: str,
		_description: str,
		_price: float,
		_stock: int,
		_available: int,
		/,
		*,
		_creationDate: datetime | None = None,
		_discontinued: bool = False
	) -> int | None:
		"""
		Adds a new product to the database.

		Args:
			_name: Name of the product.
			_description: Description of the product.
			_price: Price of the product.
			_stock: Current quantity in stock.
			_available: Quantity available for purchase.
			_creationDate: Date of product creation (defaults to now).
			_discontinued: Whether the product is discontinued (defaults to False).

		Returns:
			The productID of the newly added product, or None if addition failed.
		"""
		creation_date_to_use = _creationDate if _creationDate is not None else datetime.now()
		creation_date_str = creation_date_to_use.strftime("%Y-%m-%d %H:%M:%S")
		discontinued_int = 1 if _discontinued else 0

		query = '''
			INSERT INTO Product (name, description, price, stock, available, creationDate, discontinued)
			VALUES (%s, %s, %s, %s, %s, %s, %s)
		'''
		params = (_name, _description, _price, _stock, _available, creation_date_str, discontinued_int)
		return self._execute(query, params, _returnLastId=True)

	def get_product(self, _productId: int) -> DictRow | None:
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

	def update_product(self, _productId: int, /, **_fields) -> int | None:
		"""
		Updates specified fields for an existing product.

		Args:
			_productId: The ID of the product to update.
			_fields: Keyword arguments for fields to update.
					 Allowed fields: 'name', 'description', 'price', 'stock', 'available', 'discontinued'.
					 'creationDate' and 'productID' cannot be updated.

		Returns:
			The number of affected rows (1 if successful, 0 if no change or not found),
			or None if an error occurred or no valid fields were provided.
		"""
		allowed_fields = {'name', 'description', 'price', 'stock', 'available', 'discontinued'}
		valid_fields = {k: v for k, v in _fields.items() if k in allowed_fields}

		if not valid_fields:
			print("No valid fields provided for update_product.")
			return 0

		if 'discontinued' in valid_fields: # Ensure boolean is converted to int
			valid_fields['discontinued'] = 1 if valid_fields['discontinued'] else 0

		set_clause = ', '.join(f'{key} = %s' for key in valid_fields)
		params = tuple(valid_fields.values()) + (_productId,)

		query = f'UPDATE Product SET {set_clause} WHERE productID = %s'
		return self._execute(query, params)

	def set_product_discontinued(self, _productId: int, _state: bool = True, /) -> int | None:
		"""
		Sets the discontinued status of a product.

		Args:
			_productId: The ID of the product.
			_state: True to mark as discontinued, False to mark as not discontinued.

		Returns:
			The number of affected rows (1 if successful), or None on error.
		"""
		discontinued_int = 1 if _state else 0
		query = 'UPDATE Product SET discontinued = %s WHERE productID = %s'
		return self._execute(query, (discontinued_int, _productId))

	def get_product_images(self, _productId: int, /) -> list[str] | None:
		"""
		Retrieves all image URLs for a given product.

		Args:
			_productId: The ID of the product.

		Returns:
			A list of image URLs, or None if an error occurs.
			Returns an empty list if the product has no images or product not found.
		"""
		query = '''
			SELECT i.url
			FROM Image i
			JOIN `Product-Image` pi ON i.imageID = pi.imageID
			WHERE pi.productID = %s
		'''
		result = self._fetch_all(query, (_productId,))
		if result is None: # Error case
			return None
		return [row['url'] for row in result]

	def get_products(self, _tags: list[str] | None = None, /) -> list[DictRow] | None:
		"""
		Retrieves products. If tags are provided, retrieves products matching ALL specified tags.
		If no tags are provided, retrieves all products.

		Args:
			_tags: A list of tag names to filter by.

		Returns:
			A list of dictionaries, each representing a product, or None if an error occurs.
			Returns an empty list if no products match.
		"""
		if not _tags: # No tags provided, get all products
			query = '''
				SELECT productID, name, description, price, stock, available, creationDate, discontinued
				FROM Product
			'''
			params = ()
		else:
			placeholders = ', '.join(['%s'] * len(_tags))
			query = f'''
				SELECT p.productID, p.name, p.description, p.price,
					   p.stock, p.available, p.creationDate, p.discontinued
				FROM Product p
				JOIN `Product-Tag` pt ON p.productID = pt.productID
				JOIN `Tag` t ON pt.tagID = t.tagID
				WHERE t.name IN ({placeholders})
				GROUP BY p.productID, p.name, p.description, p.price, p.stock, p.available, p.creationDate, p.discontinued
				HAVING COUNT(DISTINCT t.tagID) = %s
			'''
			params = tuple(_tags) + (len(_tags),)

		return self._fetch_all(query, params)

	def get_products_with_tagIDs(self, _tagIds: set[int], /) -> list[DictRow] | None:
		"""
		Retrieves products that have at least one of the specified tag IDs.

		Args:
			_tagIds: A set of tag IDs. Must not be empty.

		Returns:
			A list of dictionaries, each representing a product, or None if an error occurs.
			Returns an empty list if no products match.

		Raises:
			ValueError: If _tagIds is empty.
		"""
		if not _tagIds:
			raise ValueError("At least one tagID must be supplied for get_products_with_tagIDs.")

		placeholders = ','.join(['%s'] * len(_tagIds))
		query = f'''
			SELECT DISTINCT p.productID, p.name, p.description, p.price,
							p.stock, p.available, p.creationDate, p.discontinued
			FROM Product p
			JOIN `Product-Tag` pt ON p.productID = pt.productID
			WHERE pt.tagID IN ({placeholders})
		'''
		return self._fetch_all(query, tuple(_tagIds))

	# --- Tag Management ---

	def create_tag(self, _name: str, /) -> int | None:
		"""
		Creates a new tag.

		Args:
			_name: The name of the tag.

		Returns:
			The tagID of the newly created tag, or None if creation failed (e.g., duplicate name).
		"""
		query = 'INSERT INTO Tag (name) VALUES (%s)'
		try:
			return self._execute(query, (_name,), _returnLastId=True)
		except mariadb.IntegrityError: # Handles duplicate name if 'name' has a UNIQUE constraint
			print(f"Tag with name '{_name}' likely already exists.")
			return None

	def get_tag_id(self, _name: str, /) -> int | None:
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
			A list of dictionaries, each representing a tag (tagID, name), or None on error.
			Returns an empty list if no tags exist.
		"""
		query = 'SELECT tagID, name FROM Tag'
		return self._fetch_all(query)

	def delete_tag(self, _tagId: int, /) -> int | None:
		"""
		Deletes a tag by its ID. Associated entries in Product-Tag will be cascade deleted.

		Args:
			_tagId: The ID of the tag to delete.

		Returns:
			The number of affected rows (1 if successful), or None on error.
		"""
		query = 'DELETE FROM Tag WHERE tagID = %s'
		return self._execute(query, (_tagId,))

	def add_tag_to_product(self, _productId: int, _tagId: int, /) -> int | None:
		"""
		Associates a tag with a product.

		Args:
			_productId: The ID of the product.
			_tagId: The ID of the tag.

		Returns:
			The number of affected rows (1 if successful), or None on error (e.g. duplicate entry).
		"""
		query = 'INSERT INTO `Product-Tag` (productID, tagID) VALUES (%s, %s)'
		try:
			return self._execute(query, (_productId, _tagId))
		except mariadb.IntegrityError:
			print(f"Product {_productId} already has tag {_tagId} or one of the IDs is invalid.")
			return None

	def remove_tag_from_product(self, _productId: int, _tagId: int, /) -> int | None:
		"""
		Removes a tag association from a product.

		Args:
			_productId: The ID of the product.
			_tagId: The ID of the tag.

		Returns:
			The number of affected rows (1 if successful, 0 if not found), or None on error.
		"""
		query = 'DELETE FROM `Product-Tag` WHERE productID = %s AND tagID = %s'
		return self._execute(query, (_productId, _tagId))

	# --- Image Management ---

	def add_image_to_product(self, _url: str, _productId: int, /) -> int | None:
		"""
		Adds an image and associates it with a product.

		Args:
			_url: The URL of the image.
			_productId: The ID of the product to associate the image with.

		Returns:
			The imageID of the newly added image if successful, otherwise None.
		"""
		# Create image
		image_query = 'INSERT INTO Image (url) VALUES (%s)'
		image_id = self._execute(image_query, (_url,), _returnLastId=True)

		if image_id is not None:
			# Link to product
			link_query = 'INSERT INTO `Product-Image` (productID, imageID) VALUES (%s, %s)'
			link_result = self._execute(link_query, (_productId, image_id))
			if link_result is not None and link_result > 0:
				return image_id
			else: # Failed to link, rollback or delete the orphaned image
				print(f"Failed to link image {image_id} to product {_productId}.")
				return None
		return None

	def delete_image(self, _imageId: int, /) -> int | None:
		"""
		Deletes an image by its ID. Associated entries in Product-Image will be cascade deleted.

		Args:
			_imageId: The ID of the image to delete.

		Returns:
			The number of affected rows (1 if successful), or None on error.
		"""
		query = 'DELETE FROM Image WHERE imageID = %s'
		return self._execute(query, (_imageId,))

	# --- Trolley & Line Item Management ---

	def get_trolley(self, _accountId: int, /) -> list[DictRow] | None:
		"""
		Retrieves all line items in an account's trolley.

		Args:
			_accountId: The ID of the account.

		Returns:
			A list of dictionaries, each representing a line item in the trolley, or None on error.
			Returns an empty list if the trolley is empty.
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

	def add_to_trolley(self, _accountId: int, _productId: int, /, *, _quantity: int = 1) -> int | None:
		"""
		Adds a product to an account's trolley.
		If the product is already in the trolley, this method currently creates a new line item.
		Consider adding logic to update quantity if item already exists.

		Args:
			_accountId: The ID of the account.
			_productId: The ID of the product to add.
			_quantity: The quantity of the product to add (must be >= 1).

		Returns:
			The lineItemID of the newly created line item if successful, otherwise None.

		Raises:
			ValueError: If _quantity is less than 1.
		"""
		if _quantity < 1:
			raise ValueError("Quantity must be at least 1.")

		# Create line item (priceAtSale is null until order)
		line_item_query = 'INSERT INTO LineItem (productID, quantity) VALUES (%s, %s)'
		line_item_id = self._execute(line_item_query, (_productId, _quantity), _returnLastId=True)

		if line_item_id is not None:
			# Add to trolley
			trolley_query = 'INSERT INTO Trolley (accountID, lineItemID) VALUES (%s, %s)'
			trolley_add_result = self._execute(trolley_query, (_accountId, line_item_id))
			if trolley_add_result is not None and trolley_add_result > 0:
				return line_item_id
			else: # Failed to add to trolley, cleanup line item
				print(f"Failed to add line item {line_item_id} to trolley for account {_accountId}. Cleaning up line item.")
				self._execute('DELETE FROM LineItem WHERE lineItemID = %s', (line_item_id,))
				return None
		return None

	def change_quantity_of_product_in_trolley(
		self, _accountId: int, _productId: int, _newQuantity: int, /
	) -> int | None:
		"""
		Changes the quantity of a product in an account's trolley.
		If _newQuantity is 0 or less, the item is removed from the trolley.

		Args:
			_accountId: The ID of the account.
			_productId: The ID of the product whose quantity is to be changed.
			_newQuantity: The new quantity. If <= 0, the item is removed.

		Returns:
			The number of affected LineItem rows (1 if quantity updated, 0 if item not found),
			or the result of remove_from_trolley if quantity is <=0. None on error.
		"""
		# Find the lineItemID for the product in the user's trolley
		find_query = """
			SELECT t.lineItemID
			FROM Trolley t
			JOIN LineItem li ON t.lineItemID = li.lineItemID
			WHERE t.accountID = %s AND li.productID = %s
		"""
		item = self._fetch_one(find_query, (_accountId, _productId))

		if not item:
			return 0 # Item not in trolley

		line_item_id = item['lineItemID']

		if _newQuantity <= 0:
			# Remove item from trolley and delete the line item
			self._execute('DELETE FROM Trolley WHERE accountID = %s AND lineItemID = %s', (_accountId, line_item_id))
			return self._execute('DELETE FROM LineItem WHERE lineItemID = %s', (line_item_id,))
		else:
			# Update quantity
			update_query = 'UPDATE LineItem SET quantity = %s WHERE lineItemID = %s'
			return self._execute(update_query, (_newQuantity, line_item_id))

	def remove_from_trolley(self, _accountId: int, _lineItemId: int, /) -> tuple[int | None, int | None]:
		"""
		Removes a specific line item from an account's trolley and deletes the line item itself.

		Args:
			_accountId: The ID of the account.
			_lineItemId: The ID of the line item to remove.

		Returns:
			A tuple containing:
			 (affected rows from Trolley deletion or None on error,
			  affected rows from LineItem deletion or None on error)
		"""
		# Ensure the line item belongs to the account's trolley before deleting
		trolley_check_query = 'SELECT 1 FROM Trolley WHERE accountID = %s AND lineItemID = %s'
		if not self._fetch_one(trolley_check_query, (_accountId, _lineItemId)):
			print(f"LineItem {_lineItemId} not found in trolley for account {_accountId}.")
			return (0, 0)

		trolley_delete_res = self._execute('DELETE FROM Trolley WHERE accountID = %s AND lineItemID = %s', (_accountId, _lineItemId))
		line_item_delete_res = self._execute('DELETE FROM LineItem WHERE lineItemID = %s', (_lineItemId,))
		return (trolley_delete_res, line_item_delete_res)

	def clear_trolley(self, _accountId: int, /) -> int | None:
		"""
		Clears all items from an account's trolley.
		This involves deleting entries from the Trolley table and also deleting the associated LineItems
		that are not part of any existing order.

		Args:
			_accountId: The ID of the account whose trolley is to be cleared.

		Returns:
			The number of LineItems successfully deleted, or None if an error occurs.
		"""
		# Get all lineItemIDs in the user's trolley
		trolley_items_query = 'SELECT lineItemID FROM Trolley WHERE accountID = %s'
		trolley_items = self._fetch_all(trolley_items_query, (_accountId,))

		if trolley_items is None: # Error fetching
			return None
		if not trolley_items: # Trolley is empty
			return 0

		line_item_ids_in_trolley = [item['lineItemID'] for item in trolley_items]
		placeholders = ', '.join(['%s'] * len(line_item_ids_in_trolley))

		# First, delete items from the Trolley table
		delete_trolley_query = f'DELETE FROM Trolley WHERE accountID = %s AND lineItemID IN ({placeholders})'
		# We pass _accountId first, then unpack the list of line_item_ids
		params_trolley = (_accountId,) + tuple(line_item_ids_in_trolley)
		trolley_deleted_count = self._execute(delete_trolley_query, params_trolley)

		if trolley_deleted_count is None: # Error during trolley deletion
			print(f"Error clearing trolley entries for account {_accountId}.")
			# Rollback would have happened in _execute.
			return None

		# Now, delete LineItems that were in the trolley and are not in any OrderItem
		# This is a bit safer: only delete line items that are not referenced by OrderItem
		delete_line_items_query = f'''
			DELETE FROM LineItem
			WHERE lineItemID IN ({placeholders})
			AND lineItemID NOT IN (SELECT DISTINCT lineItemID FROM OrderItem)
		'''
		line_items_deleted_count = self._execute(delete_line_items_query, tuple(line_item_ids_in_trolley))

		if line_items_deleted_count is None:
			print(f"Error deleting orphaned line items for account {_accountId} after trolley clear.")
			# Potentially partial success, but _execute handles rollback on its own error.
			return None

		return line_items_deleted_count

	# --- Order Management ---

	def create_order(self, _accountId: int, _addressId: int, /) -> int | None:
		"""
		Creates an order for an account using all items currently in their trolley.
		Sets `priceAtSale` for each line item and moves items from trolley to order.

		Args:
			_accountId: The ID of the account placing the order.
			_addressId: The ID of the address for the order.

		Returns:
			The orderID of the newly created order, or None if creation failed (e.g., empty trolley).

		Raises:
			ValueError: If the specified address does not belong to the account.
		"""
		# Verify address belongs to account
		address_check_query = "SELECT 1 FROM Address WHERE addressID = %s AND accountID = %s"
		if not self._fetch_one(address_check_query, (_addressId, _accountId)):
			raise ValueError(f"Address ID {_addressId} does not belong to account ID {_accountId}.")

		trolley_line_items = self.get_trolley(_accountId)
		if trolley_line_items is None: # Error fetching trolley
			print(f"Error fetching trolley for account {_accountId} during order creation.")
			return None
		if not trolley_line_items:
			print(f"Trolley is empty for account {_accountId}. Cannot create order.")
			return None # Or raise an exception

		# Update priceAtSale for each line item in the trolley
		for item in trolley_line_items:
			line_item_id = item['lineItemID']
			product_id = item['productID']
			# Fetch current product price (could also use item['currentPrice'] from get_trolley)
			product_info = self.get_product(product_id)
			if not product_info or product_info['price'] is None:
				print(f"Could not fetch price for product {product_id}. Aborting order.")
				self.rollback() # Rollback any previous price updates in this loop
				return None
			current_price = product_info['price']

			update_price_query = 'UPDATE LineItem SET priceAtSale = %s WHERE lineItemID = %s'
			update_res = self._execute(update_price_query, (current_price, line_item_id))
			if update_res is None or update_res == 0:
				print(f"Failed to update priceAtSale for lineItem {line_item_id}. Aborting order.")
				self.rollback()
				return None

		# Create order
		order_query = '''
			INSERT INTO `Order` (accountID, addressID, date)
			VALUES (%s, %s, %s)
		'''
		order_id = self._execute(order_query, (_accountId, _addressId, datetime.now()), _returnLastId=True)

		if order_id is None:
			print("Failed to create order entry.")
			self.rollback() # Rollback price updates
			return None

		# Link line items to order and remove from trolley
		line_item_ids_in_order: list[int] = []
		for item in trolley_line_items:
			line_item_id = item['lineItemID']
			link_query = 'INSERT INTO OrderItem (orderID, lineItemID) VALUES (%s, %s)'
			link_res = self._execute(link_query, (order_id, line_item_id))
			if link_res is None or link_res == 0:
				print(f"Failed to link lineItem {line_item_id} to order {order_id}. Rolling back order.")
				# Complex rollback: delete OrderItems, delete Order, revert priceAtSale.
				# For simplicity, full transaction rollback is better handled by `get_db` context manager.
				# Here, we'll just signal failure. The commit in _execute might be an issue for multi-step operations.
				# A better pattern is to commit only at the very end of the entire operation.
				# For now, rely on _execute's rollback for its own operation.
				self.rollback() # Attempt to rollback the entire transaction if possible
				return None
			line_item_ids_in_order.append(line_item_id)

		# Clear these specific items from the trolley
		if line_item_ids_in_order:
			placeholders = ', '.join(['%s'] * len(line_item_ids_in_order))
			clear_trolley_query = f'DELETE FROM Trolley WHERE accountID = %s AND lineItemID IN ({placeholders})'
			params_clear = (_accountId,) + tuple(line_item_ids_in_order)
			clear_res = self._execute(clear_trolley_query, params_clear)
			if clear_res is None:
				print(f"Warning: Order {order_id} created, but failed to clear items from trolley.")
				# Order is still created, but trolley might be inconsistent.
				# This highlights the need for a single commit at the end of the whole method.
				# For now, we proceed with the order_id.

		# self.commit() # Ideally, commit would happen here for the whole operation.
		# Current _execute commits after each successful statement.
		return order_id

	# --- Invoice Management ---

	def save_invoice(self, _accountId: int, _orderId: int, _data: bytes, /) -> int | None:
		"""
		Saves invoice data for an order.

		Args:
			_accountId: The ID of the account associated with the invoice.
			_orderId: The ID of the order this invoice is for.
			_data: The invoice data (e.g., PDF bytes).

		Returns:
			The invoiceID of the saved invoice, or None if saving failed.
		"""
		query = '''
			INSERT INTO Invoice (accountID, orderID, creationDate, data)
			VALUES (%s, %s, %s, %s)
		'''
		return self._execute(query, (_accountId, _orderId, datetime.now(), _data), _returnLastId=True)

	def get_invoice(self, _invoiceId: int, /) -> DictRow | None:
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

	def save_receipt(self, _accountId: int, _orderId: int, _data: bytes, /) -> int | None:
		"""
		Saves receipt data for an order.

		Args:
			_accountId: The ID of the account associated with the receipt.
			_orderId: The ID of the order this receipt is for.
			_data: The receipt data (e.g., PDF bytes).

		Returns:
			The receiptID of the saved receipt, or None if saving failed.
		"""
		query = '''
			INSERT INTO Receipt (accountID, orderID, creationDate, data)
			VALUES (%s, %s, %s, %s)
		'''
		return self._execute(query, (_accountId, _orderId, datetime.now(), _data), _returnLastId=True)

	def get_receipt(self, _receiptId: int, /) -> DictRow | None:
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

	def save_report(self, _creatorId: int, _data: bytes, /) -> int | None:
		"""
		Saves report data.

		Args:
			_creatorId: The accountID of the user who created the report.
			_data: The report data (e.g., PDF or CSV bytes).

		Returns:
			The reportID of the saved report, or None if saving failed.
		"""
		query = '''
			INSERT INTO Report (creator, creationDate, data)
			VALUES (%s, %s, %s)
		'''
		return self._execute(query, (_creatorId, datetime.now(), _data), _returnLastId=True)

	def get_report(self, _reportId: int, /) -> DictRow | None:
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

		Raises:
			ValueError: If the column is not found or not an ENUM type (though currently returns None).
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
			print(f"Column '{columnName}' in table '{tableName}' not found.")
			return None # Changed from raise ValueError to return None for consistency

		column_type: str = result["COLUMN_TYPE"]
		if not column_type.lower().startswith("enum("):
			print(f"Column '{columnName}' in table '{tableName}' is not an ENUM type. Type: {column_type}")
			return None # Changed from raise ValueError

		# e.g., "enum('val1','val2','val3')"
		enum_str = column_type[column_type.find('(')+1 : column_type.rfind(')')]
		enum_values = [val.strip("'") for val in enum_str.split(",")]
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
		# If no exceptions, commit is handled by individual _execute calls for now.
		# For more complex transactions spanning multiple db_instance calls,
		# you might want to avoid auto-commit in _execute and commit here.
		# db_instance.commit() # Example if _execute didn't commit
	except mariadb.Error as e:
		print(f"MariaDB error within get_db context: {e}")
		if db_instance: # Rollback if instance was created
			try:
				db_instance.rollback()
				print("Transaction rolled back due to MariaDB error in get_db.")
			except Exception as rb_e:
				print(f"Error during rollback attempt in get_db: {rb_e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"A database error occurred: {e}"
		)
	except HTTPException: # Re-raise HTTPExceptions
		if db_instance: # Attempt rollback for HTTP exceptions that might imply failed operations
			try:
				db_instance.rollback()
				print("Transaction rolled back due to HTTPException in get_db.")
			except Exception as rb_e:
				print(f"Error during rollback attempt in get_db (HTTPException path): {rb_e}")
		raise
	except Exception as e:
		print(f"Unexpected error in get_db context: {e}")
		if db_instance: # Rollback for any other unexpected error
			try:
				db_instance.rollback()
				print("Transaction rolled back due to unexpected error in get_db.")
			except Exception as rb_e:
				print(f"Error during rollback attempt in get_db (unexpected error path): {rb_e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"An unexpected error occurred: {e}"
		)
	finally:
		if db_instance:
			db_instance.close()

# Example usage (optional, for testing)
if __name__ == "__main__":
	print("Running Database class example...")
	# Ensure you have a MariaDB/MySQL server running and configured in MockSettings
	# or replace MockSettings with your actual settings.
	# Also, the database schema needs to be applied.

	try:
		# Initialize pool (usually done at application startup)
		# Database.initialize_pool() # Called by get_connection if not initialized

		# Using the context manager
		db_gen = get_db()
		db = next(db_gen)

		try:
			print("Successfully obtained database connection.")

			# Example: Get enum values for Account status
			print("\n--- Testing get_enum_values ---")
			account_statuses = db.get_enum_values('Account', 'status')
			if account_statuses:
				print(f"Account statuses: {account_statuses}")
			else:
				print("Could not get account statuses.")

			account_roles = db.get_enum_values('Account', 'role')
			if account_roles:
				print(f"Account roles: {account_roles}")
			else:
				print("Could not get account roles.")

			# Example: Create an account
			print("\n--- Testing create_account ---")
			new_account_id = db.create_account(
				f'testuser_{datetime.now().timestamp()}@example.com',
				"hashed_password",
				Role.CUSTOMER,
				_firstName="Test",
				_lastName="User",
			)
			if new_account_id:
				print(f"Created account with ID: {new_account_id}")

				# Example: Get the created account
				print("\n--- Testing get_account ---")
				account = db.get_account(_accountId=new_account_id)
				if account:
					print(f"Retrieved account: {account}")
				else:
					print(f"Could not retrieve account ID {new_account_id}")

				# Example: Update account
				print("\n--- Testing update_account ---")
				updated_rows = db.update_account(new_account_id, _firstName="UpdatedTest", status=Status.ACTIVE)
				if updated_rows is not None:
					print(f"Updated account, rows affected: {updated_rows}")
					account_after_update = db.get_account(_accountId=new_account_id)
					print(f"Account after update: {account_after_update}")
				else:
					print("Failed to update account.")

				# Example: Create address
				print("\n--- Testing create_address ---")
				address_id = db.create_address(new_account_id, "123 Main St, Anytown")
				if address_id:
					print(f"Created address with ID: {address_id}")
					addresses = db.get_addresses(new_account_id)
					print(f"Addresses for account {new_account_id}: {addresses}")

					# Example: Modify address
					print("\n--- Testing modify_address ---")
					mod_addr_rows = db.modify_address(address_id, "456 New Ave, Anytown")
					if mod_addr_rows is not None:
						print(f"Modified address, rows affected: {mod_addr_rows}")
						addresses_after_mod = db.get_addresses(new_account_id)
						print(f"Addresses after modification: {addresses_after_mod}")

				# Example: Add product
				print("\n--- Testing add_product ---")
				product_id_1 = db.add_product("Laptop Pro", "High-end laptop", 1200.99, 50, 45)
				product_id_2 = db.add_product("Wireless Mouse", "Ergonomic mouse", 25.50, 200, 190)
				if product_id_1: print(f"Added product 1 ID: {product_id_1}")
				if product_id_2: print(f"Added product 2 ID: {product_id_2}")

				if product_id_1:
					# Example: Get product
					print("\n--- Testing get_product ---")
					product = db.get_product(product_id_1)
					print(f"Retrieved product: {product}")

					# Example: Add to trolley
					print("\n--- Testing add_to_trolley ---")
					line_item_id = db.add_to_trolley(new_account_id, product_id_1, _quantity=2)
					if line_item_id:
						print(f"Added product {product_id_1} to trolley, line item ID: {line_item_id}")
						trolley_items = db.get_trolley(new_account_id)
						print(f"Trolley contents: {trolley_items}")

						# Example: Change quantity in trolley
						print("\n--- Testing change_quantity_of_product_in_trolley ---")
						changed_qty_res = db.change_quantity_of_product_in_trolley(new_account_id, product_id_1, 3)
						print(f"Changed quantity result: {changed_qty_res}")
						trolley_items_after_qty_change = db.get_trolley(new_account_id)
						print(f"Trolley after quantity change: {trolley_items_after_qty_change}")


						if product_id_2 and address_id:
							db.add_to_trolley(new_account_id, product_id_2, _quantity=1)
							print(f"Trolley before order: {db.get_trolley(new_account_id)}")
							# Example: Create order
							print("\n--- Testing create_order ---")
							order_id = db.create_order(new_account_id, address_id)
							if order_id:
								print(f"Created order with ID: {order_id}")
								trolley_after_order = db.get_trolley(new_account_id)
								print(f"Trolley contents after order: {trolley_after_order}") # Should be empty or items not ordered

								# Example: Save and get invoice
								print("\n--- Testing save_invoice & get_invoice ---")
								invoice_data = b"This is a test invoice PDF content."
								invoice_id = db.save_invoice(new_account_id, order_id, invoice_data)
								if invoice_id:
									print(f"Saved invoice with ID: {invoice_id}")
									retrieved_invoice = db.get_invoice(invoice_id)
									if retrieved_invoice:
										print(f"Retrieved invoice data length: {len(retrieved_invoice.get('data', b''))}")
									else: print("Failed to retrieve invoice.")
								else: print("Failed to save invoice.")
							else:
								print("Failed to create order.")
						else:
							print("Skipping order creation due to missing product or address.")
					else:
						print("Failed to add to trolley.")

					# Example: Clear trolley (if anything is left or for testing)
					# print("\n--- Testing clear_trolley ---")
					# if product_id_2: # Add another item to test clear
					#    db.add_to_trolley(new_account_id, product_id_2, _quantity=5)
					# print(f"Trolley before clear: {db.get_trolley(new_account_id)}")
					# cleared_items_count = db.clear_trolley(new_account_id)
					# print(f"Cleared trolley, items deleted: {cleared_items_count}")
					# print(f"Trolley after clear: {db.get_trolley(new_account_id)}")


				# Example: Delete account (will cascade delete addresses)
				# print("\n--- Testing delete_accounts ---")
				# deleted_count = db.delete_accounts([new_account_id])
				# if deleted_count is not None:
				# 	print(f"Deleted accounts: {deleted_count}")
				# 	account_after_delete = db.get_account(_accountId=new_account_id)
				# 	print(f"Account after delete: {account_after_delete}") # Should be None
				# else:
				# 	print("Failed to delete account.")

			else:
				print("Failed to create account.")

		except Exception as e:
			print(f"An error occurred during database operations: {e}")
			import traceback
			traceback.print_exc()
			try:
				next(db_gen, None) # Trigger finally block in get_db for cleanup
			except StopIteration:
				pass # Expected if already cleaned up
		finally:
			# Ensure the generator's finally block is called for cleanup
			try:
				next(db_gen, None)
			except StopIteration:
				pass # Expected

	except HTTPException as e:
		print(f"HTTPException (likely during pool init or connection): {e.detail}")
	except Exception as e:
		print(f"A critical error occurred: {e}")
		import traceback
		traceback.print_exc()

	print("\nExample run finished.")
