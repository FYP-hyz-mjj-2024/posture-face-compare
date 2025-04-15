# Smart Device Usage Detection - Storage Backend

<img src="https://s2.loli.net/2025/04/15/YNdVMxebcvH1DtU.png" >

> [!NOTE]
> You don't need to build the storage backend in order to run the project. The storage backend is already configured into the remote Ubuntu server in [DigitalOcean](https://cloud.digitalocean.com/).
> The following instructions records the building process.

**Deployment Info**
- Reversed proxied with Nginx
- Configured SSL certificate with Certbot
- Deployed on Ubuntu, DigitalOcean
- Domain: www.youfocusyourwalk.com

## 1. Install PostgreSQL
1.1 Install `postgresql` with `apt`.
```sh
sudo apt install postgresql
```

1.2 Create superuser.
```sh
sudo -u <USER_NAME> psql template1
```

```sh
ALTER USER <USER_NAME> with encrpted password '<PASSWORD>'
```

1.3 Restart PostgreSQL

```sh
sudo systemctl restart postgresql.service
```

Similarly, you can replace the `restart` tag with `start` or `stop`.

## 2. Install `cmake` and `build-essential`.
```sh
sudo apt-get install build-essential && apt-get install cmake
```
They are installed to compile opencv and dlib. 

## 3. Conda
3.1 Use `wget` to download the installer. The installer file will be stored in the root file.
```sh
wget https://repo.anaconda.com/archive/Anaconda3-2024.10-1-Linux-x86_64.sh
```

3.2 Run the installer to install conda.
```sh
bash <conda-installer-name>-latest-Linux-x86_64.sh
```
After installation, restart your console.

## 4. Virtual Environment

4.1 Create virtual environment.
```sh
conda create --prefix <PATH_TO_YOUR_VENV>/<VENV_NAME> python=3.12
```

4.2 Clone this repository.
```sh
git clone https://github.com/FYP-hyz-mjj-2024/posture-face-compare.git
```

4.3 Setup environment variables. 
Add a file called `.env` and fill in this structure in the file:
```
# Secret key
SECRET_KEY=XXXX     # to generate jwt
SUPER_USER_TOKEN=XXXX       # reserved

# Server Domain
SERVER_DOMAIN=http://XXXX:8001
SERVER_HOST=0.0.0.0     # Expose to internet
DATABASE_URL=postgresql://<USER_NAME>:<PASSWORD>@localhost:5432/<DATABASE_NAME>

# Email Confirmation
SMTP_SERVER=smtp.xxx.com
SMTP_PORT=587       # Example value, can change
SMTP_USERNAME=xxx@xxx.com
SMTP_PASSWORD=xxxxxxxxxx
EMAIL_FROM=xxx@xxx.com
```

4.2 Install packages.
```sh
<PATH_TO_YOUR_VENV>/<VENV_NAME>/bin/pip install -r requirements.txt
```

This process should be done after the *1. Install PostgreSQL* and *2. cmake and build-essential*, 
as a python package will always require PostgreSQL and some building tools.

4.3 Additional packages.
Some packages are required to be installed manually.
```sh
<PATH_TO_YOUR_VENV>/<VENV_NAME>/bin/pip install magic
<PATH_TO_YOUR_VENV>/<VENV_NAME>/bin/pip install opencv-python-headerless
```

## 5. Run & Maintain
### 5.1 Screen
5.1.1 Install [screen](https://www.gnu.org/software/screen/) - A multiplex tool for terminal UI.
```sh
sudo apt install screen
```

5.1.2 Create `screen` session.
```sh
screen -S <SCREEN_NAME>
```
Then, a terminal session is started. (Like a windows on GUI.)

5.1.3 Detatch `screen` session. 
```
CTRL+A
d
```
Then, the cuirrent session is detatched. (Like minimizing a window in GUI.)

5.1.4 Re-attach `screen` session.
```sh
screen -r <SCREEN_NAME>
```
Then, you go back to a screen session. (Like re-opening a window in GUI.)

5.1.5 See all opened `screen` session.
```sh
screen -ls
```

### 5.2 Setup
5.2.1 (In the database screen) Setup database.
```sh
sudo -u <USER_NAME> psql
```
```sh
CREATE DATABASE fastapi_db;
\c fastapi_db
```

5.2.2 (In the python backend screen)
```sh
cd <PROJECT_ROOT>
```

Initialize all tables using python.
```sh
<PATH_TO_YOUR_VENV>/<VENV_NAME>/bin/python -m CRUD.user.__reset__
<PATH_TO_YOUR_VENV>/<VENV_NAME>/bin/python -m CRUD.face.__reset__
```

Run
```sh
<PATH_TO_YOUR_VENV>/<VENV_NAME>/bin/python -m main
```

Then, detach to maintain running by pressing `CTRL+A` then `d`.


# Local Tips
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

Make database support uuid (after `\c` this database)

`CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`

Update user info
`UPDATE users SET <COLUMN_NAME>=<VALUE> WHERE <CONDITION>`
