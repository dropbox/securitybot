#!/usr/bin/env python
import MySQLdb
import sys

# DB CONFIG GOES HERE
host = 'localhost'
user = 'root'
passwd= ''

db = MySQLdb.connect(host=host,
                     user=user,
                     passwd=passwd,
                     db='securitybot')

cur = db.cursor()

# Start fresh
print 'Removing all tables'
cur.execute('SHOW TABLES')
tables = cur.fetchall()
for table in tables:
    table = table[0]
    print 'Dropping {0}'.format(table)
    cur.execute('DROP TABLE {0}'.format(MySQLdb.escape_string(table)))

# Create tables
print 'Creating tables...'

cur.execute(
'''
CREATE TABLE blacklist (
   ldap VARCHAR(255) NOT NULL,
   PRIMARY KEY ( ldap )
)
'''
)

cur.execute(
'''
CREATE TABLE ignored (
    ldap VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    reason VARCHAR(255) NOT NULL,
    until DATETIME NOT NULL,
    CONSTRAINT ignored_ID PRIMARY KEY ( ldap, title )
)
'''
)

cur.execute(
'''
CREATE TABLE alerts (
    hash BINARY(32) NOT NULL,
    ldap VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description VARCHAR(255) NOT NULL,
    reason TEXT NOT NULL,
    url VARCHAR(511) NOT NULL,
    event_time DATETIME NOT NULL,
    PRIMARY KEY ( hash )
)
'''
)

cur.execute(
'''
CREATE TABLE alert_status (
    hash BINARY(32) NOT NULL,
    status TINYINT UNSIGNED NOT NULL,
    PRIMARY KEY ( hash )
)
'''
)

cur.execute(
'''
CREATE TABLE user_responses(
    hash BINARY(32) NOT NULL,
    comment TEXT,
    performed BOOL,
    authenticated BOOL,
    PRIMARY KEY ( hash )
)
'''
)

print 'Done!'
