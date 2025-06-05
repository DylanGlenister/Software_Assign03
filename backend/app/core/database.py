from datetime import datetime
from enum import Enum
from typing import Any, Generator, TypeAlias

import mariadb
from fastapi import HTTPException, status

from ..utils.fields import filter_dict
from ..utils.settings import SETTINGS

# def filter_dict(data: dict, valid_keys: set, /, *, log_invalid: bool = True) -> dict:
# filtered = {k: v for k, v in data.items() if k in valid_keys}
# if log_invalid:
# invalid = set(data.keys()) - valid_keys
# for key in invalid:
# print(f"Ignored invalid field: {key}")
# return filtered

# class MockSettings:
# database_username: str = 'admin'
# database_password: str = 'password'
# database_host: str = 'localhost'
# database_port: int = 3306
# database: str = 'awe_electronics'

# SETTINGS = MockSettings()

# Type aliases
DictRow: TypeAlias = dict[str, Any]
ID: TypeAlias = int


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
            print(
                f'Attempting to create connection pool for database \'{SETTINGS.database}\' on {SETTINGS.database_host}:{SETTINGS.database_port}')
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
            is_access_denied = 'access denied' in error_message_lower or (
                hasattr(e, 'errno') and e.errno == 1045)

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
            conn = cls.__pool.get_connection()
            return conn
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

    def __init__(self, conn: mariadb.Connection, /):
        """
        Initializes the Database instance with a MariaDB connection.

        Args:
                conn: A MariaDB connection object.
        """
        self.conn: mariadb.Connection = conn
        self.cur: mariadb.Cursor = conn.cursor()
        # Ensure autocommit is off for manual transaction control
        self.conn.autocommit = False

    def close(self):
        """Closes the database cursor and connection."""
        if hasattr(self, 'cur') and self.cur:
            self.cur.close()
        if hasattr(self, 'conn') and self.conn:
            # Rollback any pending transaction if the connection is closed
            # without explicit commit/rollback
            try:
                if self.conn.autocommit:
                    self.conn.rollback()  # Potentially rollback if not committed
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
            raise  # Re-raise the error to be handled by the caller or get_db

    def rollback(self):
        """Rolls back the current transaction."""
        try:
            self.conn.rollback()
        except mariadb.Error as e:
            print(f'Error during rollback: {e}')

    # --- Internal query helpers ---

    def _fetch_one(self, query: str, params: tuple = (), /) -> DictRow | None:
        """
        Executes a query and fetches a single row.

        Args:
                query: The SQL query string.
                params: A tuple of parameters for the query.

        Returns:
                A dictionary representing the row, or None if no row is found or an error occurs.
        """
        try:
            self.cur.execute(query, params)
            row: tuple | None = self.cur.fetchone()
            if row is None:
                return None
            columns: list[str] = [desc[0]
                                  for desc in self.cur.description or []]
            return dict(zip(columns, row))
        except mariadb.Error as e:
            print(f'DB error in _fetch_one: {e}')
            return None
        except Exception as e:
            print(f'Unexpected error in _fetch_one: {e}')
            return None

    def _fetch_all(self, query: str, params: tuple = (), /
                   ) -> list[DictRow] | None:
        """
        Executes a query and fetches all rows.

        Args:
                query: The SQL query string.
                params: A tuple of parameters for the query.

        Returns:
                A list of dictionaries representing the rows, or an empty list if no rows are found.
                Returns None if a database error occurs.
        """
        try:
            self.cur.execute(query, params)
            rows: list[tuple] | None = self.cur.fetchall()

            if not rows:
                return []

            columns: list[str] = [desc[0]
                                  for desc in self.cur.description or []]
            return [dict(zip(columns, row)) for row in rows]

        except mariadb.Error as e:
            print(f'DB error in _fetch_all: {e}')
            return None
        except Exception as e:
            print(f'Unexpected error in _fetch_all: {e}')
            return None

    def _execute(
            self,
            query: str,
            params: tuple = (),
            /,
            *,
            returnLastId: bool = False
    ) -> int | ID | None:
        """
        Executes a given SQL query (INSERT, UPDATE, DELETE) without committing or rolling back.
        The calling public method is responsible for transaction management.

        Args:
                query: The SQL query string.
                params: A tuple of parameters for the query.
                returnLastId: If True, returns the last inserted row ID. Otherwise, returns the number of affected rows.

        Returns:
                The last inserted row ID (as Id) if _returnLastId is True and insert was successful.
                The number of affected rows for other operations.
                None if _returnLastId is True and no row was inserted/affected.
                Raises mariadb.Error on database execution errors.
        """
        self.cur.execute(query, params)
        affected_rows: int = self.cur.rowcount

        if returnLastId:
            return self.cur.lastrowid if affected_rows > 0 and self.cur.lastrowid is not None else None
        return affected_rows

    # --- Account Management ---

    def get_account(
            self,
            *,
            accountId: ID | None = None,
            email: str | None = None
    ) -> DictRow | None:
        """
        Retrieves a single account by its ID or email.

        Args:
                accountId: The ID of the account to retrieve.
                email: The email of the account to retrieve.
                                Exactly one of _accountId or _email must be provided.

        Returns:
                A dictionary containing account data if found, otherwise None.

        Raises:
                ValueError: If neither or both _accountId and _email are provided.
        """
        args_num = sum(x is not None for x in [accountId, email])

        if args_num == 0:
            raise ValueError(
                'Must provide exactly one of: _accountId or _email')
        elif args_num > 1:
            raise ValueError(
                'Keyword arguments _accountId and _email are mutually exclusive')

        if accountId is not None:
            query = '''
				SELECT accountID, creationDate, role, status, email, password, firstname, lastname
				FROM Account
				WHERE accountID = %s
			'''
            params = (accountId,)
        else:  # _email is not None
            query = '''
				SELECT accountID, creationDate, role, status, email, password, firstname, lastname
				FROM Account
				WHERE email = %s
			'''
            params = (email,)

        return self._fetch_one(query, params)

    def get_accounts(
            self,
            *,
            role: Role | None = None,
            status: Status | None = None,
            olderThanDays: int | None = None
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
        params_list: list[Any] = []

        if role is not None:
            conditions.append('role = %s')
            params_list.append(role.value)

        if status is not None:
            conditions.append('status = %s')
            params_list.append(status.value)

        if olderThanDays is not None:
            conditions.append(
                'creationDate < DATE_SUB(CURDATE(), INTERVAL %s DAY)')
            params_list.append(olderThanDays)

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        return self._fetch_all(query, tuple(params_list))

    def create_account(
            self,
            role: Role = Role.GUEST,
            email: str | None = None,
            password: str | None = None,
            /,
            firstName: str | None = None,
            lastName: str | None = None,
            *,
            creationDate: datetime = datetime.now()
    ) -> ID:
        """
        Creates a new account.

        Args:
                role: The role for the new account (defaults to GUEST).
                email: The email for the new account (Optional).
                password: The hashed password for the new account (Optional).
                firstName: Optional first name.
                lastName: Optional last name.
                creationDate: Optional creation date (defaults to datetime.now()).

        Returns:
                The accountID of the newly created account.

        Raises:
                Exception: If account creation fails.
        """
        creation_date_str = creationDate.strftime('%Y-%m-%d %H:%M:%S')
        query = '''
			INSERT INTO Account (creationDate, role, email, password, firstname, lastname)
			VALUES (%s, %s, %s, %s, %s, %s)
		'''
        params = (creation_date_str, role.value,
                  email, password, firstName, lastName)
        try:
            account_id = self._execute(query, params, returnLastId=True)
            if account_id is None:
                raise Exception('Account creation failed, no ID returned.')
            self.commit()
            return account_id
        except Exception as e:
            print(f'Error in create_account: {e}')
            self.rollback()
            raise  # Re-raise the exception to be handled by the caller or get_db

    def update_account(self, accountID: ID, /, **fields: Any) -> int:
        """
        Updates specified fields for an existing account.

        Args:
                accountID: The ID of the account to update.
                fields: Keyword arguments where keys are column names and values are the new values.
                                 Allowed fields: 'email', 'password', 'firstname', 'lastname', 'role', 'status'.

        Returns:
                The number of affected rows.

        Raises:
                ValueError: If no valid fields to update are provided.
                Exception: If the update operation fails.
        """
        valid_fields = filter_dict(
            fields, {'email', 'password', 'firstname', 'lastname', 'role', 'status'})

        if not valid_fields:
            raise ValueError('No valid fields to update')

        if 'role' in valid_fields and isinstance(valid_fields['role'], Role):
            valid_fields['role'] = valid_fields['role'].value
        if 'status' in valid_fields and isinstance(
                valid_fields['status'], Status):
            valid_fields['status'] = valid_fields['status'].value

        set_clause = ', '.join(f'{key} = %s' for key in valid_fields)
        params = tuple(valid_fields.values()) + (accountID,)
        query = f'UPDATE Account SET {set_clause} WHERE accountID = %s'

        try:
            affected_rows = self._execute(query, params)
            if affected_rows is None:
                raise Exception(
                    'Update account operation failed unexpectedly.')
            self.commit()
            return affected_rows
        except Exception as e:
            print(f'Error in update_account: {e}')
            self.rollback()
            raise

    def delete_accounts(self, accountIDs: set[ID], /) -> int:
        """
        Deletes one or more accounts by their IDs.

        Args:
                accountIds: A set of account IDs to delete.

        Returns:
                The number of accounts successfully deleted. Returns 0 if _ccountIds is empty.

        Raises:
                Exception: If the delete operation fails.
        """
        if not accountIDs:
            return 0

        placeholders = ', '.join(['%s'] * len(accountIDs))
        query = f'DELETE FROM Account WHERE accountID IN ({placeholders})'
        try:
            affected_rows = self._execute(query, tuple(accountIDs))
            if affected_rows is None:
                raise Exception(
                    'Delete accounts operation failed unexpectedly.')
            self.commit()
            return affected_rows
        except Exception as e:
            print(f'Error in delete_accounts: {e}')
            self.rollback()
            raise

    # --- Address Management ---

    def create_address(self, accountID: ID, location: str, /) -> ID:
        """
        Creates a new address for a given account.

        Args:
                accountID: The ID of the account this address belongs to.
                location: The location description of the address.

        Returns:
                The addressID of the newly created address.

        Raises:
                Exception: If address creation fails.
        """
        query = 'INSERT INTO Address (accountID, location) VALUES (%s, %s)'
        try:
            address_id = self._execute(
                query, (accountID, location), returnLastId=True)
            if address_id is None:
                raise Exception('Address creation failed, no ID returned.')
            self.commit()
            return address_id
        except Exception as e:
            print(f'Error in create_address: {e}')
            self.rollback()
            raise

    def get_addresses(self, accountID: ID, /) -> list[DictRow] | None:
        """
        Retrieves all addresses associated with a given account.

        Args:
                accountID: The ID of the account.

        Returns:
                A list of dictionaries, each representing an address. Returns empty list if none.
        """
        query = '''
			SELECT addressID, accountID, location
			FROM Address
			WHERE accountID = %s
		'''
        return self._fetch_all(query, (accountID,))

    def modify_address(self, addressID: ID, location: str, /) -> int:
        """
        Modifies the location of an existing address.

        Args:
                addressID: The ID of the address to modify.
                location: The new location description.

        Returns:
                The number of affected rows.

        Raises:
                Exception: If the modify operation fails.
        """
        query = 'UPDATE Address SET location = %s WHERE addressID = %s'
        try:
            affected_rows = self._execute(query, (location, addressID))
            if affected_rows is None:
                raise Exception(
                    'Modify address operation failed unexpectedly.')
            self.commit()
            return affected_rows
        except Exception as e:
            print(f'Error in modify_address: {e}')
            self.rollback()
            raise

    def delete_address(self, addressID: ID, /) -> int:
        """
        Deletes an address by its ID.

        Args:
                addressID: The ID of the address to delete.

        Returns:
                The number of affected rows.

        Raises:
                Exception: If the delete operation fails.
        """
        query = 'DELETE FROM Address WHERE addressID = %s'
        try:
            affected_rows = self._execute(query, (addressID,))
            if affected_rows is None:
                raise Exception(
                    'Delete address operation failed unexpectedly.')
            self.commit()
            return affected_rows
        except Exception as e:
            print(f'Error in delete_address: {e}')
            self.rollback()
            raise

    # --- Product Management ---

    def add_product(
            self,
            name: str,
            description: str,
            price: float = 9999999999.0,
            /,
            stock: int = 0,
            available: int = 0,
            *,
            creationDate: datetime = datetime.now(),
            discontinued: bool = False
    ) -> ID:
        """
        Adds a new product to the database.

        Args:
                name: Name of the product.
                description: Description of the product.
                price: Price of the product.
                stock: Current quantity in stock (defaults to 0).
                available: Quantity available for purchase (defaults to 0).
                creationDate: Date of product creation (defaults to now).
                discontinued: Whether the product is discontinued (defaults to False).

        Returns:
                The productID of the newly added product.

        Raises:
                Exception: If product creation fails.
        """
        creation_date_str = creationDate.strftime('%Y-%m-%d %H:%M:%S')
        discontinued_int = 1 if discontinued else 0

        query = '''
			INSERT INTO Product (name, description, price, stock, available, creationDate, discontinued)
			VALUES (%s, %s, %s, %s, %s, %s, %s)
		'''
        params = (name, description, price, stock, available,
                  creation_date_str, discontinued_int)
        try:
            product_id = self._execute(query, params, returnLastId=True)
            if product_id is None:
                raise Exception('Product creation failed, no ID returned.')
            self.commit()
            return product_id
        except Exception as e:
            print(f'Error in add_product: {e}')
            self.rollback()
            raise

    def get_product(self, productID: ID) -> DictRow | None:
        """
        Retrieves a single product by its ID.

        Args:
                productID: The ID of the product to retrieve.

        Returns:
                A dictionary containing product data if found, otherwise None.
        """
        query = '''
			SELECT productID, name, description, price, stock, available, creationDate, discontinued
			FROM Product
			WHERE productID = %s
		'''
        return self._fetch_one(query, (productID,))

    def update_product(self, productID: ID, /, **fields: Any) -> int:
        """
        Updates specified fields for an existing product.

        Args:
                productID: The ID of the product to update.
                fields: Keyword arguments for fields to update.
                                 Allowed fields: 'name', 'description', 'price', 'stock', 'available', 'discontinued'.

        Returns:
                The number of affected rows.

        Raises:
                ValueError: If no valid fields are provided.
                Exception: If the update operation fails.
        """
        valid_fields = filter_dict(
            fields, {'name', 'description', 'price', 'stock', 'available', 'discontinued'})

        if not valid_fields:
            raise ValueError('No valid fields provided for update_product.')

        if 'discontinued' in valid_fields:
            valid_fields['discontinued'] = 1 if valid_fields['discontinued'] else 0

        set_clause = ', '.join(f'{key} = %s' for key in valid_fields)
        params = tuple(valid_fields.values()) + (productID,)
        query = f'UPDATE Product SET {set_clause} WHERE productID = %s'
        try:
            affected_rows = self._execute(query, params)
            if affected_rows is None:
                raise Exception(
                    'Update product operation failed unexpectedly.')
            self.commit()
            return affected_rows
        except Exception as e:
            print(f'Error in update_product: {e}')
            self.rollback()
            raise

    def set_product_discontinued(
            self, productID: ID, state: bool = True, /) -> int:
        """
        Sets the discontinued status of a product.

        Args:
                productID: The ID of the product.
                state: True to mark as discontinued, False to mark as not discontinued.

        Returns:
                The number of affected rows.

        Raises:
                Exception: If the operation fails.
        """
        discontinued_int = 1 if state else 0
        query = 'UPDATE Product SET discontinued = %s WHERE productID = %s'
        try:
            affected_rows = self._execute(query, (discontinued_int, productID))
            if affected_rows is None:
                raise Exception(
                    'Set product discontinued operation failed unexpectedly.')
            self.commit()
            return affected_rows
        except Exception as e:
            print(f'Error in set_product_discontinued: {e}')
            self.rollback()
            raise

    def get_product_images(self, productID: ID, /) -> list[str] | None:
        """
        Retrieves all image URLs for a given product.

        Args:
                productID: The ID of the product.

        Returns:
                A list of image URLs. Returns empty list if none. Returns None on error.
        """
        query = '''
			SELECT i.url
			FROM Image i
			JOIN `Product-Image` pi ON i.imageID = pi.imageID
			WHERE pi.productID = %s
		'''
        result = self._fetch_all(query, (productID,))
        if result is None:
            return None  # Error case from _fetch_all
        return [row['url'] for row in result]

    def get_products(self, tags: list[str] |
                     None = None, /) -> list[DictRow] | None:
        """
        Retrieves products. If tags are provided, retrieves products matching ALL specified tags.
        If no tags are provided, retrieves all products.

        Args:
                tags: A list of tag names to filter by.

        Returns:
                A list of dictionaries, each representing a product. Returns empty list if none. Returns None on error.
        """
        if not tags:
            query = '''
				SELECT productID, name, description, price, stock, available, creationDate, discontinued
				FROM Product
			'''
            params = ()
        else:
            num_tags = len(tags)
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
            params = tuple(tags) + (num_tags,)
        return self._fetch_all(query, params)

    def get_products_with_tagIDs(
            self, tagIds: set[ID] | None = None, /) -> list[DictRow] | None:
        """
        Retrieves products. If tag IDs are provided, retrieves products matching ALL specified tag IDs.
        If no tag IDs are provided (None or empty set), retrieves all products.

        Args:
                tagIDs: A set of tag IDs to filter by. Can be None or empty to get all products.

        Returns:
                A list of dictionaries, each representing a product. Returns empty list if no products match.
                Returns None if a database error occurs.
        """
        if not tagIds:
            query = '''
				SELECT productID, name, description, price, stock, available, creationDate, discontinued
				FROM Product
			'''
            params = ()
        else:
            num_tags = len(tagIds)
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
            params = tuple(tagIds) + (num_tags,)

        return self._fetch_all(query, params)

    # --- Tag Management ---

    def create_tag(self, name: str, /) -> ID:
        """
        Creates a new tag.

        Args:
                name: The name of the tag.

        Returns:
                The tagID of the newly created tag.

        Raises:
                mariadb.IntegrityError: If the tag name already exists.
                Exception: For other creation failures.
        """
        query = 'INSERT INTO Tag (name) VALUES (%s)'
        try:
            tag_id = self._execute(query, (name,), returnLastId=True)
            if tag_id is None:
                raise Exception('Tag creation failed, no ID returned.')
            self.commit()
            return tag_id
        except mariadb.IntegrityError:
            self.rollback()  # Rollback if integrity error (e.g. duplicate name)
            print(f'Tag with name \'{name}\' likely already exists.')
            raise  # Re-raise to signal failure
        except Exception as e:
            print(f'Error in create_tag: {e}')
            self.rollback()
            raise

    def get_tag_id(self, name: str, /) -> ID | None:
        """
        Retrieves the ID of a tag by its name.

        Args:
                name: The name of the tag.

        Returns:
                The tagID if found, otherwise None.
        """
        query = 'SELECT tagID FROM `Tag` WHERE name = %s'
        result = self._fetch_one(query, (name,))
        return result['tagID'] if result else None

    def get_all_tags(self) -> list[DictRow] | None:
        """
        Retrieves all tags from the database.

        Returns:
                A list of dictionaries, each representing a tag (tagID, name). Returns empty list if none. Returns None on error.
        """
        query = 'SELECT tagID, name FROM Tag'
        return self._fetch_all(query)

    def delete_tag(self, tagID: ID, /) -> int:
        """
        Deletes a tag by its ID. Associated entries in Product-Tag will be cascade deleted.

        Args:
                tagID: The ID of the tag to delete.

        Returns:
                The number of affected rows.

        Raises:
                Exception: If the delete operation fails.
        """
        query = 'DELETE FROM Tag WHERE tagID = %s'
        try:
            affected_rows = self._execute(query, (tagID,))
            if affected_rows is None:
                raise Exception('Delete tag operation failed unexpectedly.')
            self.commit()
            return affected_rows
        except Exception as e:
            print(f'Error in delete_tag: {e}')
            self.rollback()
            raise

    def add_tag_to_product(self, productId: ID, tagID: ID, /) -> int:
        """
        Associates a tag with a product.

        Args:
                productID: The ID of the product.
                tagId: The ID of the tag.

        Returns:
                The number of affected rows.

        Raises:
                mariadb.IntegrityError: If the product already has the tag or an ID is invalid.
                Exception: For other failures.
        """
        query = 'INSERT INTO `Product-Tag` (productID, tagID) VALUES (%s, %s)'
        try:
            affected_rows = self._execute(query, (productId, tagID))
            if affected_rows is None:
                raise Exception(
                    'Add tag to product operation failed unexpectedly.')
            self.commit()
            return affected_rows
        except mariadb.IntegrityError:
            self.rollback()
            print(
                f'Product {productId} already has tag {tagID} or one of the IDs is invalid.')
            raise
        except Exception as e:
            print(f'Error in add_tag_to_product: {e}')
            self.rollback()
            raise

    def remove_tag_from_product(self, productID: ID, tagID: ID, /) -> int:
        """
        Removes a tag association from a product.

        Args:
                productID: The ID of the product.
                tagID: The ID of the tag.

        Returns:
                The number of affected rows.

        Raises:
                ValueError: If the tag is not associated with the product.
                Exception: For other failures.
        """
        query = 'DELETE FROM `Product-Tag` WHERE productID = %s AND tagID = %s'
        try:
            affected_rows = self._execute(query, (productID, tagID))
            if affected_rows is None:
                raise Exception(
                    'Remove tag from product operation failed unexpectedly.')
            if affected_rows == 0:
                raise ValueError(
                    f'Tag ID {tagID} is not associated with Product ID {productID}.')
            self.commit()
            return affected_rows
        except Exception as e:
            print(f'Error in remove_tag_from_product: {e}')
            if not isinstance(e, ValueError):
                self.rollback()
            raise

    # --- Image Management ---

    def add_image_to_product(self, url: str, productID: ID, /) -> ID:
        """
        Adds an image and associates it with a product. This is an atomic operation.

        Args:
                url: The URL of the image.
                productID: The ID of the product to associate the image with.

        Returns:
                The imageID of the newly added image.

        Raises:
                Exception: If the operation fails.
        """
        try:
            image_query = 'INSERT INTO Image (url) VALUES (%s)'
            image_id = self._execute(image_query, (url,), returnLastId=True)

            if image_id is None:  # Should not happen if _execute works as expected and insert is valid
                raise Exception(
                    'Failed to create image entry, image_id is None.')

            link_query = 'INSERT INTO `Product-Image` (productID, imageID) VALUES (%s, %s)'
            link_result = self._execute(link_query, (productID, image_id))

            if link_result is None or link_result == 0:
                raise Exception(
                    f'Failed to link image {image_id} to product {productID}.')

            self.commit()
            return image_id
        except Exception as e:
            print(f'Error in add_image_to_product: {e}')
            self.rollback()
            raise

    def delete_image(self, imageID: ID, /) -> int:
        """
        Deletes an image by its ID. Associated entries in Product-Image will be cascade deleted.

        Args:
                _imageId: The ID of the image to delete.

        Returns:
                The number of affected rows.

        Raises:
                Exception: If the delete operation fails.
        """
        query = 'DELETE FROM Image WHERE imageID = %s'
        try:
            affected_rows = self._execute(query, (imageID,))
            if affected_rows is None:
                raise Exception('Delete image operation failed unexpectedly.')
            self.commit()
            return affected_rows
        except Exception as e:
            print(f'Error in delete_image: {e}')
            self.rollback()
            raise

    # --- Trolley & Line Item Management ---

    def get_trolley(self, accountID: ID, /) -> list[DictRow] | None:
        """
        Retrieves all line items in an account's trolley.

        Args:
                accountID: The ID of the account.

        Returns:
                A list of dictionaries, each representing a line item in the trolley. Empty list if none. Returns None on error.
        """
        query = '''
			SELECT li.lineItemID, li.productID, p.name as productName,
				   li.quantity, li.priceAtSale, p.price as currentPrice
			FROM Trolley t
			JOIN LineItem li ON t.lineItemID = li.lineItemID
			JOIN Product p ON li.productID = p.productID
			WHERE t.accountID = %s
		'''
        return self._fetch_all(query, (accountID,))

    def add_to_trolley(self, accountID: ID, productID: ID, /,
                       quantity: int = 1) -> ID:
        """
        Adds a product to an account's trolley. This is an atomic operation.

        Args:
                accountID: The ID of the account.
                productID: The ID of the product to add.
                quantity: The quantity of the product to add.

        Returns:
                The lineItemID of the newly created line item.

        Raises:
                ValueError: If _quantity is less than 1.
                Exception: For other failures.
        """
        if quantity < 1:
            raise ValueError('Quantity must be at least 1.')
        try:
            line_item_query = 'INSERT INTO LineItem (productID, quantity) VALUES (%s, %s)'
            line_item_id = self._execute(
                line_item_query, (productID, quantity), returnLastId=True)

            if line_item_id is None:
                raise Exception(
                    'Failed to create line item, line_item_id is None.')

            trolley_query = 'INSERT INTO Trolley (accountID, lineItemID) VALUES (%s, %s)'
            trolley_add_result = self._execute(
                trolley_query, (accountID, line_item_id))

            if trolley_add_result is None or trolley_add_result == 0:
                raise Exception(
                    f'Failed to add line item {line_item_id} to trolley for account {accountID}.')

            self.commit()
            return line_item_id
        except Exception as e:
            print(f'Error in add_to_trolley: {e}')
            self.rollback()
            raise

    def change_quantity_of_product_in_trolley(
            self,
            accountID: ID,
            productID: ID,
            newQuantity: int,
            /
    ) -> int:
        """
        Changes the quantity of a product in an account's trolley.

        Args:
                accountID: The ID of the account.
                productID: The ID of the product whose quantity is to be changed.
                newQuantity: The new quantity.

        Returns:
                The number of affected LineItem rows.

        Raises:
                ValueError: If _newQuantity is less than 1, or if the product is not found in the trolley.
                Exception: For other failures.
        """
        if newQuantity < 1:
            raise ValueError('New quantity must be at least 1.')

        try:
            find_query = '''
				SELECT t.lineItemID
				FROM Trolley t
				JOIN LineItem li ON t.lineItemID = li.lineItemID
				WHERE t.accountID = %s AND li.productID = %s
			'''
            item = self._fetch_one(find_query, (accountID, productID))

            if not item:
                raise ValueError(
                    f'Product ID {productID} not found in trolley for account ID {accountID}.')

            line_item_id: ID = item['lineItemID']

            update_query = 'UPDATE LineItem SET quantity = %s WHERE lineItemID = %s'
            affected_rows = self._execute(
                update_query, (newQuantity, line_item_id))
            if affected_rows is None:
                raise Exception(
                    'Change quantity operation failed unexpectedly.')
            self.commit()
            return affected_rows
        except Exception as e:
            print(f'Error in change_quantity_of_product_in_trolley: {e}')
            self.rollback()
            raise

    def remove_from_trolley(self, accountID: ID,
                            lineItemID: ID, /) -> tuple[int, int]:
        """
        Removes a specific line item from an account's trolley and deletes the line item itself.
        This is an atomic operation.

        Args:
                accountID: The ID of the account.
                lineItemID: The ID of the line item to remove.

        Returns:
                A tuple containing: (affected rows from Trolley deletion, affected rows from LineItem deletion).

        Raises:
                ValueError: If the line item is not found in the specified account's trolley.
                Exception: For other failures.
        """
        try:
            trolley_check_query = 'SELECT 1 FROM Trolley WHERE accountID = %s AND lineItemID = %s'
            if not self._fetch_one(trolley_check_query,
                                   (accountID, lineItemID)):
                raise ValueError(
                    f'LineItem ID {lineItemID} not found in trolley for account ID {accountID}.')

            trolley_delete_res = self._execute(
                'DELETE FROM Trolley WHERE accountID = %s AND lineItemID = %s', (accountID, lineItemID))
            if trolley_delete_res is None or trolley_delete_res == 0:
                raise Exception(
                    f'Failed to delete LineItem ID {lineItemID} from Trolley for account ID {accountID}.')

            line_item_delete_res = self._execute(
                'DELETE FROM LineItem WHERE lineItemID = %s', (lineItemID,))
            if line_item_delete_res is None or line_item_delete_res == 0:
                raise Exception(
                    f'Failed to delete LineItem ID {lineItemID} from LineItem table.')

            self.commit()
            return (trolley_delete_res, line_item_delete_res)
        except Exception as e:
            print(f'Error in remove_from_trolley: {e}')
            self.rollback()
            raise

    def clear_trolley(self, accountID: ID, /) -> int:
        """
        Clears all items from an account's trolley.
        This involves deleting entries from the Trolley table and also deleting the associated LineItems
        that are not part of any existing order. This is an atomic operation.

        Args:
                accountID: The ID of the account whose trolley is to be cleared.

        Returns:
                The number of LineItems successfully deleted from the LineItem table.

        Raises:
                Exception: If the operation fails.
        """
        try:
            trolley_items_query = 'SELECT lineItemID FROM Trolley WHERE accountID = %s'
            trolley_items_result = self._fetch_all(
                trolley_items_query, (accountID,))

            if trolley_items_result is None:
                raise Exception(
                    f'Failed to fetch trolley items for account {accountID}.')
            if not trolley_items_result:
                return 0

            line_item_ids_in_trolley = [item['lineItemID']
                                        for item in trolley_items_result]
            placeholders = ', '.join(['%s'] * len(line_item_ids_in_trolley))

            delete_trolley_query = f'DELETE FROM Trolley WHERE accountID = %s AND lineItemID IN ({placeholders})'
            params_trolley = (accountID,) + tuple(line_item_ids_in_trolley)
            trolley_deleted_count = self._execute(
                delete_trolley_query, params_trolley)

            if trolley_deleted_count is None:
                raise Exception(
                    f'Error clearing trolley entries for account {accountID}.')

            delete_line_items_query = f'''
				DELETE FROM LineItem
				WHERE lineItemID IN ({placeholders})
				AND lineItemID NOT IN (SELECT DISTINCT lineItemID FROM OrderItem)
			'''
            line_items_deleted_count = self._execute(
                delete_line_items_query, tuple(line_item_ids_in_trolley))

            if line_items_deleted_count is None:
                raise Exception(
                    f'Error deleting orphaned line items for account {accountID} after trolley clear.')

            self.commit()
            return line_items_deleted_count
        except Exception as e:
            print(f'Error in clear_trolley: {e}')
            self.rollback()
            raise

    # --- Order Management ---

    def create_order(self, accountID: ID, addressID: ID, /) -> ID:
        """
        Creates an order for an account using all items currently in their trolley.
        Sets `priceAtSale` for each line item and moves items from trolley to order.
        This is an atomic operation.

        Args:
                accountID: The ID of the account placing the order.
                addressID: The ID of the address for the order.

        Returns:
                The orderID of the newly created order.

        Raises:
                ValueError: If the specified address does not belong to the account,
                                        or if the trolley is empty.
                Exception: If any database operation fails during order creation.
        """
        try:
            address_check_query = 'SELECT 1 FROM Address WHERE addressID = %s AND accountID = %s'
            if not self._fetch_one(address_check_query,
                                   (addressID, accountID)):
                raise ValueError(
                    f'Address ID {addressID} does not belong to account ID {accountID}.')

            trolley_line_items = self.get_trolley(accountID)
            if trolley_line_items is None:
                raise Exception(
                    f'Error fetching trolley for account {accountID} during order creation.')
            if not trolley_line_items:
                raise ValueError(
                    f'Trolley is empty for account {accountID}. Cannot create order.')

            for item in trolley_line_items:
                line_item_id: ID = item['lineItemID']
                product_id: ID = item['productID']
                product_info = self.get_product(product_id)

                if not product_info or product_info['price'] is None:
                    raise Exception(
                        f'Could not fetch price for product {product_id}. Aborting order.')
                current_price = product_info['price']

                update_price_query = 'UPDATE LineItem SET priceAtSale = %s WHERE lineItemID = %s'
                update_res = self._execute(
                    update_price_query, (current_price, line_item_id))
                if update_res is None or update_res == 0:
                    raise Exception(
                        f'Failed to update priceAtSale for lineItem {line_item_id}.')

            order_query = '''
				INSERT INTO `Order` (accountID, addressID, date)
				VALUES (%s, %s, %s)
			'''
            order_id = self._execute(
                order_query, (accountID, addressID, datetime.now()), returnLastId=True)

            if order_id is None:
                raise Exception('Failed to create order entry.')

            line_item_ids_in_order: list[ID] = []
            for item in trolley_line_items:
                line_item_id: ID = item['lineItemID']
                link_query = 'INSERT INTO OrderItem (orderID, lineItemID) VALUES (%s, %s)'
                link_res = self._execute(link_query, (order_id, line_item_id))
                if link_res is None or link_res == 0:
                    raise Exception(
                        f'Failed to link lineItem {line_item_id} to order {order_id}.')
                line_item_ids_in_order.append(line_item_id)

            if line_item_ids_in_order:
                placeholders = ', '.join(['%s'] * len(line_item_ids_in_order))
                clear_trolley_query = f'DELETE FROM Trolley WHERE accountID = %s AND lineItemID IN ({placeholders})'
                params_clear = (accountID,) + tuple(line_item_ids_in_order)
                clear_res = self._execute(clear_trolley_query, params_clear)

                # Check if the number of cleared items matches expected
                if clear_res is None or clear_res != len(
                        line_item_ids_in_order):
                    raise Exception(
                        f'Failed to clear all ordered items from trolley for account {accountID}. Expected {len(line_item_ids_in_order)}, got {clear_res}.')

            self.commit()
            return order_id
        except Exception as e:
            print(f'Error in create_order: {e}')
            self.rollback()
            raise

    def get_order(self, orderID: ID, /) -> DictRow | None:
        """
        Retrieves an order by its ID.

        Args:
                orderID: The ID of the order.

        Returns:
                A dictionary containing order data, or None if not found or error.
        """
        query = '''
			SELECT orderID, accountID, addressID, date
			FROM Order
			WHERE orderID = %s
		'''
        return self._fetch_one(query, (orderID,))

    def get_orders(self) -> list[DictRow] | None:
        """
        Retrieves all orders from the database.

        Returns:
                A list containing all the orders. Returns empty list if none. Returns None on error.
        """
        query = '''
			SELECT orderID, accountID, addressID, date
			FROM Order
		'''
        return self._fetch_all(query, ())

    def get_order_from_accounts(
            self, accountID: ID, /) -> list[DictRow] | None:
        """
        Retrieves all orders made by an account.

        Args:
                accountID: The ID of the account to be sorted by.

        Returns:
                A list containing all the orders. Returns empty list if none. Returns None on error.
        """
        query = '''
			SELECT o.orderID, o.accountID, o.addressID, o.date
			FROM Order o
			JOIN `Account` a ON o.accountID = a.accountID
			WHERE o.accountID = %s
		'''
        return self._fetch_all(query, (accountID,))

    # --- Invoice Management ---

    def save_invoice(self, accountID: ID, orderID: ID, data: bytes, /) -> ID:
        """
        Saves invoice data for an order.

        Args:
                accountID: The ID of the account associated with the invoice.
                orderID: The ID of the order this invoice is for.
                data: The invoice data (e.g., PDF bytes).

        Returns:
                The invoiceID of the saved invoice.

        Raises:
                Exception: If saving fails.
        """
        query = 'INSERT INTO Invoice (accountID, orderID, creationDate, data) VALUES (%s, %s, %s, %s)'
        try:
            invoice_id = self._execute(
                query, (accountID, orderID, datetime.now(), data), returnLastId=True)
            if invoice_id is None:
                raise Exception('Save invoice failed, no ID returned.')
            self.commit()
            return invoice_id
        except Exception as e:
            print(f'Error in save_invoice: {e}')
            self.rollback()
            raise

    def get_invoice(self, invoiceID: ID, /) -> DictRow | None:
        """
        Retrieves invoice data by its ID.

        Args:
                invoiceID: The ID of the invoice.

        Returns:
                A dictionary containing invoice data, or None if not found or error.
        """
        query = '''
			SELECT invoiceID, accountID, orderID, creationDate, data
			FROM Invoice
			WHERE invoiceID = %s
		'''
        return self._fetch_one(query, (invoiceID,))

    # --- Receipt Management ---

    def save_receipt(self, accountID: ID, orderID: ID, data: bytes, /) -> ID:
        """
        Saves receipt data for an order.

        Args:
                accountID: The ID of the account associated with the receipt.
                orderID: The ID of the order this receipt is for.
                data: The receipt data (e.g., PDF bytes).

        Returns:
                The receiptID of the saved receipt.

        Raises:
                Exception: If saving fails.
        """
        query = 'INSERT INTO Receipt (accountID, orderID, creationDate, data) VALUES (%s, %s, %s, %s)'
        try:
            receipt_id = self._execute(
                query, (accountID, orderID, datetime.now(), data), returnLastId=True)
            if receipt_id is None:
                raise Exception('Save receipt failed, no ID returned.')
            self.commit()
            return receipt_id
        except Exception as e:
            print(f'Error in save_receipt: {e}')
            self.rollback()
            raise

    def get_receipt(self, receiptID: ID, /) -> DictRow | None:
        """
        Retrieves receipt data by its ID.

        Args:
                receiptID: The ID of the receipt.

        Returns:
                A dictionary containing receipt data, or None if not found or error.
        """
        query = '''
			SELECT receiptID, accountID, orderID, creationDate, data
			FROM Receipt
			WHERE receiptID = %s
		'''
        return self._fetch_one(query, (receiptID,))

    # --- Report Management ---

    def save_report(self, creatorID: ID, data: bytes, /) -> ID:
        """
        Saves report data.

        Args:
                creatorID: The accountID of the user who created the report.
                data: The report data (e.g., PDF or CSV bytes).

        Returns:
                The reportID of the saved report.

        Raises:
                Exception: If saving fails.
        """
        query = 'INSERT INTO Report (creator, creationDate, data) VALUES (%s, %s, %s)'
        try:
            report_id = self._execute(
                query, (creatorID, datetime.now(), data), returnLastId=True)
            if report_id is None:
                raise Exception('Save report failed, no ID returned.')
            self.commit()
            return report_id
        except Exception as e:
            print(f'Error in save_report: {e}')
            self.rollback()
            raise

    def get_report(self, reportID: ID, /) -> DictRow | None:
        """
        Retrieves report data by its ID.

        Args:
                reportID: The ID of the report.

        Returns:
                A dictionary containing report data, or None if not found or error.
        """
        query = '''
			SELECT reportID, creator, creationDate, data
			FROM Report
			WHERE reportID = %s
		'''
        return self._fetch_one(query, (reportID,))

    # --- Utilities ---

    def get_enum_values(self, tableName: str,
                        columnName: str, /) -> list[str] | None:
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
            print(
                f'Column \'{columnName}\' in table \'{tableName}\' not found.')
            return None

        column_type: str = result['COLUMN_TYPE']
        if not column_type.lower().startswith('enum('):
            print(
                f'Column \'{columnName}\' in table \'{tableName}\' is not an ENUM type. Type: {column_type}')
            return None

        enum_str = column_type[column_type.find(
            '(') + 1: column_type.rfind(')')]
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
    except Exception as e:  # Catch all exceptions from the route handler or db methods
        if db_instance:
            try:
                db_instance.rollback()
                print(
                    f'Transaction rolled back due to exception in get_db context: {e}')
            except Exception as rb_e:
                print(f'Error during rollback attempt in get_db: {rb_e}')
        if isinstance(e, HTTPException):  # Re-raise HTTPExceptions
            raise
        # Wrap other exceptions in HTTPException for consistent error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'An error occurred: {e}'
        )
    finally:
        if db_instance:
            db_instance.close()


class DatabaseTests:
    """
    A class to encapsulate tests for the Database class.
    """

    def __init__(self):
        print('DatabaseTests initialized. Ensure database schema is applied and server is running.')

    def _run_test_group(self, test_method_group):
        group_name = test_method_group.__name__
        print(f'\n--- Running Test Group: {group_name} ---')
        all_passed = True
        db_gen = None  # Define db_gen outside try to ensure it's available in finally
        try:
            db_gen = get_db()
            db = next(db_gen)
            try:
                test_method_group(db)
                print(f'--- Test Group {group_name} PASSED ---')
            except AssertionError as ae:
                all_passed = False
                print(
                    f'--- Test Group {group_name} FAILED (AssertionError): {ae} ---')
                import traceback
                traceback.print_exc()
            except Exception as e:
                all_passed = False
                print(
                    f'--- Test Group {group_name} FAILED (Exception): {e} ---')
                import traceback
                traceback.print_exc()
        except Exception as e:  # Catches errors from get_db() or next(db_gen)
            all_passed = False
            print(
                f'--- Test Group {group_name} FAILED (Error in get_db setup or yield): {e} ---')
            import traceback
            traceback.print_exc()
        finally:
            if db_gen:  # Ensure db_gen was initialized before trying to call next
                try:
                    next(db_gen, None)  # Ensure finally in get_db is called
                except StopIteration:
                    pass  # Expected if generator already exhausted
                except Exception as e_fin:
                    print(
                        f'Error during get_db cleanup for {group_name}: {e_fin}')
                    all_passed = False  # Mark as failed if cleanup has issues
        return all_passed

    def test_utility_functions(self, db: Database):
        print('Testing: get_enum_values')
        account_statuses = db.get_enum_values('Account', 'status')
        print(f'Account statuses: {account_statuses}')
        assert account_statuses is not None and 'active' in account_statuses, 'Failed to get active status'
        account_roles = db.get_enum_values('Account', 'role')
        print(f'Account roles: {account_roles}')
        assert account_roles is not None and 'customer' in account_roles, 'Failed to get customer role'

    def test_account_crud_operations(self, db: Database):
        print('Testing: Account CRUD')
        test_email = f'acc_test_{datetime.now().timestamp()}@example.com'
        # Create
        acc_id = db.create_account(
            Role.CUSTOMER, test_email, 'password', firstName='Acc', lastName='Test')
        assert isinstance(acc_id, int), 'create_account failed'
        # Read (single)
        acc = db.get_account(accountId=acc_id)
        assert acc is not None and acc['email'] == test_email, 'get_account failed'
        # Read (multiple)
        all_specific_accounts = db.get_accounts(
            role=Role.CUSTOMER, status=Status.UNVERIFIED)
        assert all_specific_accounts is not None and any(
            a['accountID'] == acc_id for a in all_specific_accounts), 'get_accounts failed to find new account with specific role/status'
        # Update
        db.update_account(acc_id, firstname='UpdatedAcc',
                          status=Status.ACTIVE.value)
        updated_acc = db.get_account(accountId=acc_id)
        assert updated_acc is not None and updated_acc['firstname'] == 'UpdatedAcc' and updated_acc[
            'status'] == Status.ACTIVE.value, 'update_account failed'
        # Delete
        db.delete_accounts({acc_id})
        assert db.get_account(
            accountId=acc_id) is None, 'delete_accounts failed'

    def test_address_crud_operations(self, db: Database):
        print('Testing: Address CRUD')
        acc_id = db.create_account(
            Role.GUEST, f'addr_test_{datetime.now().timestamp()}@example.com', 'pw')
        # Create
        addr_id = db.create_address(acc_id, '123 Test Lane')
        assert isinstance(addr_id, int), 'create_address failed'
        # Read
        addresses = db.get_addresses(acc_id)
        assert addresses is not None and len(
            addresses) == 1 and addresses[0]['location'] == '123 Test Lane', 'get_addresses failed'
        # Modify
        db.modify_address(addr_id, '456 New Road')
        mod_addresses = db.get_addresses(acc_id)
        assert mod_addresses is not None and mod_addresses[0][
            'location'] == '456 New Road', 'modify_address failed'
        # Delete
        db.delete_address(addr_id)
        assert not db.get_addresses(acc_id), 'delete_address failed'
        db.delete_accounts({acc_id})

    def test_product_crud_and_features(self, db: Database):
        print('Testing: Product CRUD and features')
        prod_name = f'Prod_Test_{datetime.now().timestamp()}'
        # Add
        prod_id = db.add_product(
            prod_name, 'Desc', 10.0, stock=10, available=5)
        assert isinstance(prod_id, int), 'add_product failed'
        # Get
        prod = db.get_product(prod_id)
        assert prod is not None and prod['name'] == prod_name, 'get_product failed'
        # Update
        db.update_product(prod_id, description='New Desc', price=12.50)
        updated_prod = db.get_product(prod_id)
        assert updated_prod is not None and updated_prod[
            'description'] == 'New Desc' and updated_prod['price'] == 12.50, 'update_product failed'
        # Set discontinued
        db.set_product_discontinued(prod_id, True)
        disc_prod = db.get_product(prod_id)
        assert disc_prod is not None and disc_prod[
            'discontinued'] == 1, 'set_product_discontinued failed (True)'
        db.set_product_discontinued(prod_id, False)
        not_disc_prod = db.get_product(prod_id)
        assert not_disc_prod is not None and not_disc_prod[
            'discontinued'] == 0, 'set_product_discontinued failed (False)'
        # Get all products (basic check)
        all_prods = db.get_products()
        assert all_prods is not None and any(
            p['productID'] == prod_id for p in all_prods), "Failed to get all products or find test product"

    def test_tag_crud_and_product_linking(self, db: Database):
        print('Testing: Tag CRUD and Product Linking')
        tag_name1 = f'Tag1_Test_{datetime.now().timestamp()}'
        tag_name2 = f'Tag2_Test_{datetime.now().timestamp()}'
        # Create
        tag1_id = db.create_tag(tag_name1)
        tag2_id = db.create_tag(tag_name2)
        assert isinstance(tag1_id, int) and isinstance(
            tag2_id, int), 'create_tag failed'
        # Get ID by name
        assert db.get_tag_id(
            tag_name1) == tag1_id, 'get_tag_id failed for tag1'
        assert db.get_tag_id(
            'NonExistentTag') is None, 'get_tag_id returned ID for non-existent tag'
        # Get all tags
        all_tags = db.get_all_tags()
        assert all_tags is not None and any(t['tagID'] == tag1_id for t in all_tags) and any(
            t['tagID'] == tag2_id for t in all_tags), 'get_all_tags failed'
        # Product linking
        prod_id = db.add_product(
            f'TagLinkProd_{datetime.now().timestamp()}', 'Desc')
        db.add_tag_to_product(prod_id, tag1_id)
        db.add_tag_to_product(prod_id, tag2_id)
        # Verify link with get_products and get_products_with_tagIDs
        prods_by_name = db.get_products([tag_name1, tag_name2])
        assert prods_by_name is not None and any(
            p['productID'] == prod_id for p in prods_by_name), 'get_products by name failed'
        prods_by_id = db.get_products_with_tagIDs({tag1_id, tag2_id})
        assert prods_by_id is not None and any(
            p['productID'] == prod_id for p in prods_by_id), 'get_products_with_tagIDs failed'
        # Remove link
        db.remove_tag_from_product(prod_id, tag1_id)
        prods_after_remove = db.get_products_with_tagIDs(
            {tag1_id, tag2_id})  # Should not find it now
        assert not any(p['productID'] == prod_id for p in prods_after_remove or [
        ]), 'Product still found after removing one of required tags'
        try:
            db.remove_tag_from_product(prod_id, tag1_id)  # Try removing again
            assert False, 'Should have raised ValueError for removing non-existent tag link'
        except ValueError:
            pass
        # Delete tag
        db.delete_tag(tag1_id)
        db.delete_tag(tag2_id)
        assert db.get_tag_id(tag_name1) is None and db.get_tag_id(
            tag_name2) is None, 'delete_tag failed'

    def test_image_crud_and_product_linking(self, db: Database):
        print('Testing: Image CRUD and Product Linking')
        prod_id = db.add_product(
            f'ImageLinkProd_{datetime.now().timestamp()}', 'Desc')
        img_url = f'http://example.com/img_{datetime.now().timestamp()}.jpg'
        # Add image to product
        img_id = db.add_image_to_product(img_url, prod_id)
        assert isinstance(img_id, int), 'add_image_to_product failed'
        # Get product images
        prod_images = db.get_product_images(prod_id)
        assert prod_images is not None and img_url in prod_images, 'get_product_images failed'
        # Delete image
        db.delete_image(img_id)
        # Check if image is gone from Image table
        img_check = db._fetch_one(
            'SELECT 1 FROM Image WHERE imageID = %s', (img_id,))
        assert img_check is None, 'Image not deleted from Image table'
        # Check if association is gone from Product-Image (due to cascade)
        img_assoc_check = db._fetch_one(
            'SELECT 1 FROM `Product-Image` WHERE imageID = %s', (img_id,))
        assert img_assoc_check is None, 'Product-Image association not cascade deleted'
        assert not db.get_product_images(
            prod_id), 'get_product_images still finds images after delete_image'

    def test_trolley_lineitem_order_workflow(self, db: Database):
        print('Testing: Full Trolley-Order Workflow')
        acc_id = db.create_account(
            Role.GUEST, f'workflow_user_{datetime.now().timestamp()}@example.com', 'pw')
        addr_id = db.create_address(acc_id, '1 Workflow St')
        prod1_id = db.add_product(
            'WorkflowProd1', 'P1', 10.0, stock=10, available=10)
        prod2_id = db.add_product(
            'WorkflowProd2', 'P2', 20.0, stock=10, available=10)

        li1_id = db.add_to_trolley(acc_id, prod1_id, quantity=2)
        db.add_to_trolley(acc_id, prod2_id, quantity=1)
        trolley = db.get_trolley(acc_id)
        assert trolley is not None and len(
            trolley) == 2, 'Trolley setup incorrect'

        db.change_quantity_of_product_in_trolley(acc_id, prod1_id, 3)
        changed_trolley = db.get_trolley(acc_id)
        assert changed_trolley is not None and any(
            item['productID'] == prod1_id and item['quantity'] == 3 for item in changed_trolley), 'change_quantity failed'

        order_id = db.create_order(acc_id, addr_id)
        assert isinstance(order_id, int), 'create_order failed'
        assert not db.get_trolley(acc_id), 'Trolley not cleared after order'

        order_items_check = db._fetch_all(
            'SELECT li.productID, li.quantity, li.priceAtSale FROM OrderItem oi JOIN LineItem li ON oi.lineItemID = li.lineItemID WHERE oi.orderID = %s ORDER BY li.productID', (order_id,))
        assert order_items_check is not None and len(
            order_items_check) == 2, 'Incorrect number of items in order'
        assert order_items_check[0]['productID'] == prod1_id and order_items_check[
            0]['quantity'] == 3 and order_items_check[0]['priceAtSale'] == 10.0
        assert order_items_check[1]['productID'] == prod2_id and order_items_check[
            1]['quantity'] == 1 and order_items_check[1]['priceAtSale'] == 20.0

        li3_id = db.add_to_trolley(acc_id, prod1_id, quantity=1)
        db.remove_from_trolley(acc_id, li3_id)
        assert not db.get_trolley(acc_id), 'remove_from_trolley failed'

        db.add_to_trolley(acc_id, prod1_id, quantity=1)
        db.add_to_trolley(acc_id, prod2_id, quantity=1)
        assert len(db.get_trolley(acc_id) or []) == 2
        cleared_count = db.clear_trolley(acc_id)
        assert cleared_count == 2, 'clear_trolley returned incorrect count'
        assert not db.get_trolley(
            acc_id), 'clear_trolley did not empty trolley'

    def test_financial_document_management(self, db: Database):
        print('Testing: Invoice, Receipt, Report Management')
        acc_id = db.create_account(
            Role.GUEST, f'docs_user_{datetime.now().timestamp()}@example.com', 'pw')
        addr_id = db.create_address(acc_id, '1 Docs St')
        prod_id = db.add_product('DocsProd', 'P', 1.0, stock=1, available=1)
        db.add_to_trolley(acc_id, prod_id, quantity=1)
        order_id = db.create_order(acc_id, addr_id)

        invoice_data = b'Test Invoice Data'
        inv_id = db.save_invoice(acc_id, order_id, invoice_data)
        assert isinstance(inv_id, int), 'save_invoice failed'
        inv = db.get_invoice(inv_id)
        assert inv is not None and inv['data'] == invoice_data, 'get_invoice failed'

        receipt_data = b'Test Receipt Data'
        rec_id = db.save_receipt(acc_id, order_id, receipt_data)
        assert isinstance(rec_id, int), 'save_receipt failed'
        rec = db.get_receipt(rec_id)
        assert rec is not None and rec['data'] == receipt_data, 'get_receipt failed'

        report_data = b'Test Report Data'
        rep_id = db.save_report(acc_id, report_data)
        assert isinstance(rep_id, int), 'save_report failed'
        rep = db.get_report(rep_id)
        assert rep is not None and rep['data'] == report_data and rep['creator'] == acc_id, 'get_report failed'

    def run_all_tests(self):
        """Runs all defined test methods."""
        tests_to_run = [
            self.test_utility_functions,
            self.test_account_crud_operations,
            self.test_address_crud_operations,
            self.test_product_crud_and_features,
            self.test_tag_crud_and_product_linking,
            self.test_image_crud_and_product_linking,
            self.test_trolley_lineitem_order_workflow,
            self.test_financial_document_management,
        ]
        overall_success = True
        for test_method_group in tests_to_run:
            if not self._run_test_group(test_method_group):
                overall_success = False

        if overall_success:
            print('\n--- ALL TESTS PASSED SUCCESSFULLY ---')
        else:
            print('\n--- !!! SOME TESTS FAILED !!! ---')


if __name__ == '__main__':
    Database.initialize_pool()
    test_runner = DatabaseTests()
    test_runner.run_all_tests()
