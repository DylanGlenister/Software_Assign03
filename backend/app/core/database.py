# Module Imports
import os

import mariadb

class Database:
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
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")

	@classmethod
	def disconnect(cls):
		cls.__conn.close()

	@classmethod
	def commit(cls):
		cls.__conn.commit()

	@classmethod
	def rollback(cls):
		cls.__conn.rollback()

	@classmethod
	def execute_from_file(cls, _path: str, _debug = False):
		'''Should not be used for commands that retrive information.'''
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
		for i in range(10):
			cls.__cur.execute('INSERT INTO test (value) VALUES (?)', (i,))

	@classmethod
	def test_select(cls):
		result: list[tuple[int, int]] = []
		try:
			cls.__cur.execute('SELECT * FROM test')
			for (id, value) in Database.__cur:
				result.append((id, value))
		except mariadb.Error as e:
			print(e)
		return result

def test():
	Database.connect()

	Database.execute_from_file('./app/sql/test.sql')

	Database.test_insert()

	# Make the changes permanent
	Database.commit()

	result = Database.test_select()

	for (id, value) in result:
		print(f'id: {id}, value: {value}')

	# Rollback in case of error
	Database.rollback()

	Database.disconnect()

if __name__ == '__main__':
	test()
