![Curation Tracer](logo_500px.png)

A flask web application for IIIF resource usage analytics with regard to IIIF Curations.

## Setup

* set up PostGIS DB (see [PostGIS Setup](#postgis-setup))
* create virtual environment: `$ python3 -m venv venv`
* activate virtual environment: `$ source venv/bin/activate`
* install requirements: `$ pip install -r requirements.txt`
* create file `config.ini` (see example file `config.ini.dist`)
* run `$ python3 tracer.py`

#### PostGIS Setup

Example for Ubuntu 18.04

```
# apt install postgresql-10
# apt install postgresql-10-postgis-2.4
# apt install postgresql-10-postgis-scripts
# apt install postgresql-server-dev-10
# su postgres
$ psql
=# create role <username> superuser with login;
=# create role tracer with login;
=# alter user tracer with password 'tracertracer';
$ createdb tracer
$ psql tracer
=# create extension postgis;
```

## Config

section | key | default | explanation
------- | --- | ------- | -----------
environment | port | 5000 | port on which the endpoint is served
&zwnj; | db\_uri | postgresql+psycopg2://tracer:<br>tracertracer@localhost:5432/tracer | a [SQLAlchemy database URI](http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls) to the [PostGIS DB](#postgis-setup)
&zwnj; | log\_file | log.txt | file in which crawler logs are written
&zwnj; | crawl\_interval | 6 | crawl interval in hours
&zwnj; | activity\_stream\_list | http://localhost:5000/as/collection.json | comma seperated list of links to [Activity Streams](https://www.w3.org/TR/activitystreams-core/), as provided by e.g. [JSONkeeper](https://github.com/IllDepence/JSONkeeper)
marker | &lt;key&gt; | &lt;value&gt; | key value pairs that will be set for the [markers](http://codh.rois.ac.jp/software/iiif-curation-viewer/annotation.html#%E3%83%9E%E3%83%BC%E3%82%AB%E3%83%BC%E3%81%AE%E7%A8%AE%E9%A1%9E) used in annotations (the only thing set by default is `border-color` with the value `#0f0`)

## Usage

* run `$ python3 tracer.py`
    * Curation Tracer will then crawl the Activity Streams given in `config.ini` (once on startup and then according to the `crawl_interval` setting) for Curations.
* perform a search
    ```
    <your_host>:<your_port>/?canvas=<url_encoded_canvas_uri>&xywh=<x>,<y>,<w>,<h>
    ```
    * where you provide a canvas URI (and optionally a region with the canvas)
* example
    ```
    $ curl -X GET 'http://127.0.0.1:5000/?canvas=http%3A%2F%2Fdcollections.lib.keio.ac.jp%2Fsites%2Fdefault%2Ffiles%2Fiiif%2FNRE%2F132X-136-1%2Fpage2&xywh=0,0,10000,10000'
    ```
* response format
    * a [IIIF Curation](http://codh.rois.ac.jp/iiif/curation/) that
        * contains the queried canvas
        * [annotated](http://codh.rois.ac.jp/software/iiif-curation-viewer/annotation.html#%E3%82%A2%E3%83%8E%E3%83%86%E3%83%BC%E3%82%B7%E3%83%A7%E3%83%B3%E3%81%A8%E3%82%A2%E3%83%8E%E3%83%86%E3%83%BC%E3%82%B7%E3%83%A7%E3%83%B3%E3%83%93%E3%83%A5%E3%83%BC%E3%83%A2%E3%83%BC%E3%83%89) with the backlinks that resulted from the query

#### Using gunicorn

* activate virtual environment: `$ source venv/bin/activate`
* install gunicorn: `$ pip install gunicorn`
* start Curation Tracer: `$ gunicorn --bind localhost:5002 tracer:app`

To serve Curation Tracer under a specific path, add argument `-e SCRIPT_NAME='/<path>'` to the gunicorn command.  
*Example*

* start as: `$ gunicorn --bind localhost:5000 -e SCRIPT_NAME='/curation/tracer' tracer:app`
* access as: `<your_host>:5000/curation/tracer?canvas=...`

## Logo
The Curation Tracer logo uses image content from [源氏香之図](http://codh.rois.ac.jp/pmjt/book/200014999/) in the [日本古典籍データセット（国文研所蔵）](http://codh.rois.ac.jp/pmjt/book/) provided by the [Center for Open Data in the Humanities](http://codh.rois.ac.jp/), used under [CC-BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/).
The Curation Tracer logo itself is licensed under [CC-BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/) by Tarek Saier. A high resolution version (2870×1125 px) can be downloaded [here](http://moc.sirtetris.com/curation_tracer_logo_full.png).

## Support
Sponsored by the National Institute of Informatics.  
Supported by the Center for Open Data in the Humanities, Joint Support-Center for Data Science Research, Research Organization of Information and Systems.
