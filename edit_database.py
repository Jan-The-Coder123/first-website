from werkzeug.security import generate_password_hash
import sqlite3
connection = sqlite3.connect('sqlite.db', check_same_thread=False)
cursor = connection.cursor()

cursor.execute('create table likes (id integer primary key autoincrement, post_id integer not null, user_id integer not null);')

connection.commit()
