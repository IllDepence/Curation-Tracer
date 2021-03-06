import datetime
import dateutil.parser
import json
import requests
import os
from sqlalchemy import text as sqla_text
from sqlalchemy import create_engine
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from config import Cfg


def requests_retry_session(retries=5, backoff_factor=0.2,
                           status_forcelist=(500, 502, 504),
                           session=None):
    """ Method to use instead of requests.get to allow for retries during the
        crawling process. Ideally the crawler should, outside of this method,
        keep track of resources that could not be dereferenced, and offer some
        kind of way to retry for those resources at a later point in time (e.g.
        the next crawling run.

        Code from and discussion at:
        https://www.peterbe.com/plog/best-practice-with-retries-with-requests
    """

    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def get_attrib_uri(json_dict, attrib):
    """ Get the URI for an attribute.
    """

    url = None
    if type(json_dict[attrib]) == str:
        url = json_dict[attrib]
    elif type(json_dict[attrib]) == dict:
        if json_dict[attrib].get('id', False):
            url = json_dict[attrib]['id']
        elif json_dict[attrib].get('@id', False):
            url = json_dict[attrib]['@id']
    return url


def get_referenced(json_dict, attrib):
    """ Get a value (of an attribute in a dict) that is not included in its
        entirety but just referenced by a URI or an object with a URI as its
        id.
    """

    url = get_attrib_uri(json_dict, attrib)

    try:
        resp = requests_retry_session().get(url)
    except Exception as e:
        log('Could not dereference resource at {}. Error {}.'.format(
            url,
            e.__class__.__name__
            )
        )
        return '{}'

    return resp.json()


def process_curation_create(activity, db_engine):
    """ Process a create activity that has a cr:Curation as its object.
    """

    new_canvases = 0
    log('Retrieving curation {}'.format(activity['object']['@id']))
    cur_dict = get_referenced(activity, 'object')
    cur_id = cur_dict['@id']
    index_curation(cur_id, db_engine)
    log('Entering ranges')
    for ran in cur_dict.get('selections', []):
        manifest_id = get_attrib_uri(ran, 'within')
        canvases = ran.get('members', []) + ran.get('canvases', [])
        canvas_id_region_tups = [can['@id'].split('#') for can in canvases]
        # DB entries
        for can_id_region_tup in canvas_id_region_tups:
            can_id = can_id_region_tup[0]
            xywh = can_id_region_tup[1].replace('xywh=', '')
            index_canvas(can_id, manifest_id, db_engine)
            index_curation_element(cur_id, can_id, manifest_id, xywh, db_engine)
        log('done')
    return len(canvas_id_region_tups)


def index_canvas(uri, manifest_uri, db_engine):
    q = sqla_text('''
        INSERT INTO canvases(jsonld_id, manifest_jsonld_id)
        VALUES (:cid, :mid)
        ON CONFLICT (jsonld_id, manifest_jsonld_id)
        DO NOTHING''')
    db_engine.execute(q, cid=uri, mid=manifest_uri)


def index_curation(uri, db_engine):
    q = sqla_text('''
        INSERT INTO curations(jsonld_id)
        VALUES (:cid)
        ON CONFLICT (jsonld_id)
        DO NOTHING''')
    db_engine.execute(q, cid=uri)


def index_curation_element(cur_id, can_id, manifest_id, xywh, db_engine):
    s_cur = sqla_text('''
        SELECT id
        FROM curations
        WHERE jsonld_id=:cid''')
    cur_db_id = db_engine.execute(s_cur, cid=cur_id).fetchone()[0]
    s_can = sqla_text('''
        SELECT id
        FROM canvases
        WHERE jsonld_id=:cid AND manifest_jsonld_id=:mid''')
    can_db_id = db_engine.execute(s_can, cid=can_id, mid=manifest_id).fetchone()[0]
    x, y, w, h = [int(elem) for elem in xywh.split(',')]
    poly = ('ST_GeomFromText('
        '\'POLYGON(({} {}, {} {}, {} {}, {} {}, {} {}))\')').format(
        x, y,
        x+w, y,
        x+w, y+h,
        x, y+h,
        x, y
        )
    # because the IDs are only numbers and the PostGIS polygon won't go
    # through sqla_text we use format here ¯\_(ツ)_/¯
    q = '''INSERT INTO curation_elements(canvas_id, curation_id, area)
        VALUES ({}, {}, {})'''.format(can_db_id, cur_db_id, poly)
    db_engine.execute(q)


def deintex_curation(cur_uri, db_engine):
    # get Curation DB ID
    s_cur = sqla_text('''
        SELECT id
        FROM curations
        WHERE jsonld_id=:cid''')
    cur_db_id = db_engine.execute(s_cur, cid=cur_uri).fetchone()
    if cur_db_id:
        cur_db_id = cur_db_id[0]
        # delete Curation elements ("cutouts")
        d_cel = sqla_text('''
            DELETE FROM curation_elements
            WHERE curation_id=:cdbid''')
        db_engine.execute(d_cel, cdbid=cur_db_id)
        # delete Curation
        d_cur = sqla_text('''
            DELETE FROM curations
            WHERE jsonld_id=:jid''')
        db_engine.execute(d_cur, jid=cur_uri)
        # TODO delete orphaned Canvases


def process_curation_delete(activity, db_engine):
    """ Process a delete activity that has a cr:Curation as its object.
    """

    log(('Deletion triggered through activity {}').format(activity['id']))
    cur_uri = get_attrib_uri(activity, 'object')
    deintex_curation(cur_uri, db_engine)


def crawl_single(as_url, db_engine):
    """ Crawl, given a URL to an Activity Stream
    """

    last_activity_query = sqla_text('''
        SELECT last_activity
        FROM last_activity_times
        WHERE acticity_stream_url=:as_url
        ''')

    last_activity_db = db_engine.execute(
        last_activity_query,
        as_url=as_url
        ).fetchone()

    if not last_activity_db:
        last_activity_time_db = datetime.datetime.fromtimestamp(0)
        log('First time crawling this Activity Stream.')
    else:
        last_activity_time_db = dateutil.parser.parse(last_activity_db[0])
        log('Last cralwed activity at {}.'.format(last_activity_time_db))

    log('Retrieving Activity Stream ({})'.format(as_url))
    try:
        resp = requests.get(as_url)
    except requests.exceptions.RequestException as e:
        msg = 'Could not access Activity Stream. ({})'.format(e)
        log(msg)
        print(msg)
        return
    if resp.status_code != 200:
        msg = ('Could not access Activity Stream. (HTTP {})'
              ).format(resp.status_code)
        log(msg)
        print(msg)
        return

    as_oc = resp.json()
    log('Start iterating over Activity Stream pages')
    as_ocp = get_referenced(as_oc, 'last')

    new_canvases = 0
    new_activity = False
    # NOTE: seen_activity_objs is used to prevent processing obsolete
    #       activities. Since we go through the Activity Stream backwards, we
    #       only process the most recent Activity per IIIF doc.
    #       (Not doing so might lead to for example trying to process a Create
    #       for a document for which a Delete was processed just before.)
    seen_activity_objs = []
    last_activity_time_as = None
    # for all AS pages
    while True:
        # for all AC items
        log('going through AS page {}'.format(as_ocp['id']))
        for activity in as_ocp['orderedItems']:
            if activity['type'] in ['Create', 'Update', 'Delete']:
                # Reduce noise
                log('going through {} item {}'.format(activity['type'],
                                                      activity['id']))
            activity_end_time = dateutil.parser.parse(activity['endTime'])
            # if we haven't seen it yet and it's about a Curation
            if activity_end_time > last_activity_time_db and \
                    activity['object']['@type'] == 'cr:Curation' and \
                    activity['object'] not in seen_activity_objs:
                if last_activity_time_as == None:
                    # b/c we're going backwards (i.e. from new to old)
                    last_activity_time_as = activity_end_time
                new_activity = True
                if activity['type'] == 'Create':
                    log('Create')
                    new_canvases += process_curation_create(activity, db_engine)
                elif activity['type'] == 'Update':
                    log('Update')
                    log(' ≈Delete')
                    process_curation_delete(activity, db_engine)
                    log(' +Create')
                    new_canvases += process_curation_create(activity, db_engine)
                elif activity['type'] == 'Delete':
                    log('Delete')
                    process_curation_delete(activity, db_engine)
                seen_activity_objs.append(activity['object'])
            else:
                if activity['type'] in ['Create', 'Update', 'Delete']:
                    # Reduce noise
                    log('skipping')

        if not as_ocp.get('prev', False):
            break
        as_ocp = get_referenced(as_ocp, 'prev')

    if last_activity_time_as == None:
        last_activity_time_as = last_activity_time_db
    # persist crawl log
    if not last_activity_db:
        last_activity_update = sqla_text('''
            INSERT INTO last_activity_times(acticity_stream_url, last_activity)
            VALUES (:as_url, :new_time)''')
    else:
        last_activity_update = sqla_text('''
            UPDATE last_activity_times
            SET last_activity=:new_time
            WHERE acticity_stream_url=:as_url
            ''')

    last_activity_db = db_engine.execute(
        last_activity_update,
        new_time=last_activity_time_as.isoformat(),
        as_url=as_url)

    if new_activity:
        pass
        # foo
    else:
        pass
        # bar


def db_setup(uri):
    """ Setup DB
    """

    db_engine = create_engine(uri)

    create_canvases_table = '''
        CREATE TABLE IF NOT EXISTS canvases (
          id SERIAL UNIQUE,
          jsonld_id TEXT,
          manifest_jsonld_id TEXT,
          PRIMARY KEY(jsonld_id, manifest_jsonld_id)
        );'''
    create_curations_table = '''
        CREATE TABLE IF NOT EXISTS curations (
          id SERIAL UNIQUE,
          jsonld_id TEXT PRIMARY KEY
        );'''
    create_curation_elements_table = '''
        CREATE TABLE IF NOT EXISTS curation_elements (
          id SERIAL PRIMARY KEY,
          canvas_id INTEGER REFERENCES canvases(id),
          curation_id INTEGER REFERENCES curations(id),
          area GEOMETRY(Polygon)
        );'''
    create_last_activities_table = '''
        CREATE TABLE IF NOT EXISTS last_activity_times (
          acticity_stream_url TEXT PRIMARY KEY,
          last_activity TEXT -- ISO format UTC time
        );'''

    db_engine.execute(create_canvases_table)
    db_engine.execute(create_curations_table)
    db_engine.execute(create_curation_elements_table)
    db_engine.execute(create_last_activities_table)
    return db_engine


def log(msg):
    """ Write a log message.
    """

    cfg = Cfg()
    timestamp = str(datetime.datetime.now()).split('.')[0]
    fn = cfg.cfg['log_file']
    # make /dev/stdout usable as log file
    # https://www.bugs.python.org/issue27805
    # side note: stat.S_ISCHR(os.stat(fn).st_mode) doesn't seem to work in an
    #            alpine linux docker container running canvas indexer with
    #            gunicorn although manually executing it on a python shell in
    #            the container works
    if fn == '/dev/stdout':
        mode = 'w'
    else:
        mode = 'a'
    with open(fn, mode) as f:
        f.write('[{}]   {}\n'.format(timestamp, msg))


def crawl():
    """ Crawl all the Activity Streams.
    """

    cfg = Cfg()
    activity_stream_urls = cfg.cfg['activity_stream_list']
    db_engine = db_setup(cfg.cfg['db_uri'])

    log('- - - - - - - - - - START - - - - - - - - - -')
    log('Going through {} activity stream(s).'.format(len(activity_stream_urls)))

    # crawl
    for url in activity_stream_urls:
        crawl_single(url, db_engine)

    log('- - - - - - - - - - END - - - - - - - - - -')


if __name__ == '__main__':
    crawl()
