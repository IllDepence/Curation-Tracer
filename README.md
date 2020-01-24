### Setup

* set up PostGIS DB (see [PostGIS Setup](#postgis-setup))
* create virtual environment: `$ python3 -m venv venv`
* activate virtual environment: `$ source venv/bin/activate`
* install requirements: `$ pip install -r requirements.txt`
* create file `config.ini` (see example file `config.ini.dist`)
* run `$ python3 curba.py`

### Usage

* run `$ python3 curba.py`
* access as
    ```
    <your_host>:<your_port>/?canvas=<url_encoded_canvas_uri>&area_xywh=<x>,<y>,<w>,<h>
    ```
* example
    ```
    $ curl -X GET 'http://127.0.0.1:5000/?canvas=http%3A%2F%2Fdcollections.lib.keio.ac.jp%2Fsites%2Fdefault%2Ffiles%2Fiiif%2FNRE%2F132X-136-1%2Fpage2&area_xywh=0,0,10000,10000'
    ```
* response format
    * a [IIIF Curation](http://codh.rois.ac.jp/iiif/curation/) that
        * contains the queried canvas
        * annotated with the backlinks that resulted from the query

##### PostGIS Setup

Example for Ubuntu 18.04

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
