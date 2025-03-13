# Server

1. Install postgresql
sudo -u postgres psql
sudo systemctl restart postgresql
2. cmake, build-essential
3. conda
4. conda env
5. requirements.txt
6. magic, opencv-headless

# Local
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

Exit database edit mode

`\q`

Make database support uuid

`CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`