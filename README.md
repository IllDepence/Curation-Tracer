##### Draft

* set up PostGIS DB
* create virtual environment: `$ python3 -m venv venv`
* activate virtual environment: `$ source venv/bin/activate`
* install requirements: `$ pip install -r requirements.txt`
* create file `activity_streams.list` (see example)
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
=# create role cures superuser with login;
=# alter user cures with password 'curescures';
$ createdb CuReS
$ psql CuReS
=# create extension postgis;
```
