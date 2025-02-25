stop database
`pg_ctl -D "D:\ProgramFiles\PostgreSQL\17\data" stop`

start database
`pg_ctl -D "D:\ProgramFiles\PostgreSQL\17\data" start`

Login as super user `postgres`
`psql -U postgres`

list databases
`\l`

use a database
`\c <DATABASE_NAME>`

show tables in this database
`\dt`

exit database edit mode
`\q`