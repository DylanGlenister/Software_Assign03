# Module Imports
import os

import mariadb

class Database:
	initialised = False
	__conn: mariadb.Connection
	__cur: mariadb.Cursor

	@classmethod
	def connect(cls):
		try:
			cls.__conn = mariadb.connect(
				user="admin",
				password="password",
				host="localhost",
				port=3306,
				database="awe_electronics"
			)
			cls.__cur = cls.__conn.cursor()
			cls.initialised = True
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")

	@classmethod
	def disconnect(cls):
		if not cls.initialised:
			return
		cls.__conn.close()

	@classmethod
	def commit(cls):
		if not cls.initialised:
			return
		cls.__conn.commit()

	@classmethod
	def rollback(cls):
		if not cls.initialised:
			return
		cls.__conn.rollback()

	@classmethod
	def execute_from_file(cls, _path: str, _debug = False):
		'''Should not be used for commands that retrive information.'''
		if not cls.initialised:
			return
		with open(os.path.abspath(_path), 'r') as file:
			commands = file.read().split(';')
			for comm in commands:
				comm = comm.strip()
				if (comm == ''):
					continue
				if (_debug):
					print(comm)
				cls.__cur.execute(comm)

	@classmethod
	def test_insert(cls):
		if not cls.initialised:
			return
		for i in range(10):
			cls.__cur.execute('INSERT INTO test (value) VALUES (?)', (i,))

	@classmethod
	def test_select(cls):
		result: list[tuple[int, int]] = []
		if not cls.initialised:
			return result
		try:
			cls.__cur.execute('SELECT * FROM test')
			for (id, value) in Database.__cur:
				result.append((id, value))
		except mariadb.Error as e:
			print(e)
		return result

	# === BRAINSTORMING IDEAS ===

	@classmethod
	def get_trolley(cls, _user):
		'''Will return trolley data from the database.'''
		return { 'Result': True }

	@classmethod
	def save_trolley(cls, _user):
		'''Will save data from the trolley to the database.'''
		return { 'Result': True }

	@classmethod
	def query_products(cls, **args):
		'''Given some filtering options, will return a list of products.'''
		return { 'Result': True }

	@classmethod
	def get_price(cls, _product):
		'''Will return the price of a specific product.'''
		return { 'Result': True }

	@classmethod
	def save_order(cls, _order):
		'''Will save an order to the database.'''
		return { 'Result': True }

	@classmethod
	def load_order(cls, _order):
		'''Will load an order from the database.'''
		return { 'Result': True }

	@classmethod
	def add_account(cls, _accountInfo):
		'''Will add an account to the database.'''
		return { 'Result': True }

	@classmethod
	def get_account(cls, _account):
		'''Will retrieve account information from the database.'''
		return { 'Result': True }

	@classmethod
	def save_invoice(cls, _invoice):
		'''Will save an invoice to the database.'''
		return { 'Result': True }

	@classmethod
	def save_receipt(cls, _receipt):
		'''Will save a receipt to the database.'''
		return { 'Result': True }

	@classmethod
	def get_invoice(cls, _invoice):
		'''Will retrieve an invoice from the database.'''
		return { 'Result': True }

	@classmethod
	def get_receipt(cls, _receipt):
		'''Will retrieve a receipt from the database.'''
		return { 'Result': True }

	@classmethod
	def save_report(cls, _receipt):
		'''Will save a report to the database.'''
		return { 'Result': True }

	@classmethod
	def get_report(cls, _receipt):
		'''Will retrieve a report from the database.'''
		return { 'Result': True }

	@classmethod
	def get_sales_data(cls):
		'''Will retrieve sales data from the database.'''
		return { 'Result': True }

def test():
	Database.connect()
	Database.execute_from_file('./app/sql/test.sql')
	Database.test_insert()
	# Make the changes permanent
	Database.commit()
	result = Database.test_select()
	for (id, value) in result:
		print(f'id: {id}, value: {value}')
	## Rollback in case of error
	#Database.rollback()
	Database.disconnect()

if __name__ == '__main__':
	test()
