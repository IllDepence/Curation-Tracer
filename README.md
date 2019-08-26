##### Draft

* set up PostGIS DB
* create virtual environment: `$ python3 -m venv venv`
* activate virtual environment: `$ source venv/bin/activate`
* install requirements: `$ pip install -r requirements.txt`
* create file `config.ini` (see example file `config.ini.dist`)
* run `$ python3 crawler.py`

##### PostGIS setup notes

```
# apt install postgresql-10
# apt install postgresql-10-postgis-2.4
# apt install postgresql-10-postgis-scripts
# apt install postgresql-server-dev-10
# su postgres
$ psql
=# create role <username> superuser with login;
=# create role curba with login;
=# alter user curba with password 'curbacurba';
$ createdb curba
$ psql curba
=# create extension postgis;
```
