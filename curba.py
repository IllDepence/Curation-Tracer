import atexit
import copy
import json
import time
import urllib.parse
import uuid
from config import Cfg
from crawler import crawl
from collections import OrderedDict
from flask import Flask, request, abort, jsonify
from sqlalchemy import text as sqla_text
from sqlalchemy import create_engine
from apscheduler.schedulers.background import BackgroundScheduler

crawl()  # once at startup
cfg = Cfg()
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=crawl,
    trigger='interval',
    hours=cfg.cfg['crawl_interval'])  # then at given interval
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

app = Flask(__name__)


def build_curba_curation(canvas_uri, containing_manifest_uri, backlinks):
    """ Build a curation containing a single canvas that is annotated with
        curation backlinks.
    """

    backlink_prefix = ('http://codh.rois.ac.jp/software/iiif-curation-viewer/'
                       'demo/?curation=')
    use_prefix = False

    cur = OrderedDict()
    cur['@context'] = ['http://iiif.io/api/presentation/2/context.json',
                       ('http://codh.rois.ac.jp/iiif/curation/1/context.js'
                        'on')]
    cur['@type'] = 'cr:Curation'
    cur['@id'] = 'http://example.org/iiif/curation/{}'.format(uuid.uuid1())
    cur['viewingHint'] = 'annotation'
    cur['label'] = 'Curation Backlinks for {}'.format(canvas_uri)
    cur['selections'] = []
    sel = OrderedDict()
    sel['@id'] = 'http://example.org/iiif/range/{}'.format(uuid.uuid1())
    sel['@type'] = 'sc:Range'
    sel['label'] = 'Temporary range for displaying a canvas'
    sel['members'] = []
    mem = OrderedDict()
    mem['@id'] = canvas_uri
    mem['@type'] = 'sc:Canvas'
    mem['label'] = 'Temporary canvas for displaying annotations'
    mem['metadata'] = []
    for xywh, uris in backlinks.items():
        # For every area
        mtd = OrderedDict()
        mtd['label'] = 'Annotation'
        mtd['value'] = []
        for uri in uris:
            # For every backlink to a curation
            ann = OrderedDict()
            ann['@id'] = 'http://example.org/iiif/annotation/{}'.format(uuid.uuid1())
            ann['@type'] = 'oa:Annotation'
            ann['motivation'] = 'sc:painting'
            ann['on'] = '{}#xywh={}'.format(canvas_uri, xywh)
            ann['resource'] = OrderedDict()
            ann['resource']['@type'] = 'cnt:ContentAsText'
            ann['resource']['format'] = 'text/html'
            backlink_uri = uri
            if use_prefix:
                backlink_uri = '{}{}'.format(
                    backlink_prefix,
                    urllib.parse.quote(uri)
                    )
            ann['resource']['chars'] = '<a href="{}">Curation</a>'.format(backlink_uri)
            ann['resource']['marker'] = OrderedDict()
            ann['resource']['marker']['border-color'] = '#0f0'
            mtd['value'].append(copy.deepcopy(ann))
        mem['metadata'].append(copy.deepcopy(mtd))
    sel['members'].append(copy.deepcopy(mem))
    sel['within'] = OrderedDict()
    sel['within']['@id'] = containing_manifest_uri
    sel['within']['@type'] = 'sc:Manifest'
    sel['within']['label'] = 'Temporary manifest for displaying a canvas'
    cur['selections'].append(copy.deepcopy(sel))
    return cur


@app.route('/', methods=['GET'])
def index():
    canvas_uri_raw = request.args.get('canvas')
    area_xywh = request.args.get('area_xywh')
    if not canvas_uri_raw:
        return abort(400)
    canvas_uri = urllib.parse.unquote(canvas_uri_raw)

    cfg = Cfg()
    db_engine = create_engine(cfg.cfg['db_uri'])

    q_can = sqla_text('''
        SELECT id, manifest_jsonld_id
        FROM canvases
        WHERE jsonld_id=:can_uri
        ''')
    print(canvas_uri)
    can_db_tpls = db_engine.execute(
        q_can,
        can_uri=canvas_uri
        ).fetchall()
    if not can_db_tpls:
        return abort(404)  # FIXME not there, respond accordingly
    else:
        if len(can_db_tpls) == 1:
            can_db_id = int(can_db_tpls[0]['id'])
            can_db_man_jsonld_id = can_db_tpls[0]['manifest_jsonld_id']
        else:
            print('multiple canvases w/ same ID (!!!)')  # FIXME problem

    area_query_insert = ''
    if area_xywh:
        x, y, w, h = [int(elem) for elem in area_xywh.split(',')]
        poly = ('ST_GeomFromText('
            '\'POLYGON(({} {}, {} {}, {} {}, {} {}, {} {}))\')').format(
            x, y,
            x+w, y,
            x+w, y+h,
            x, y+h,
            x, y
            )
        area_query_insert = 'ST_Within(area, {}) and '.format(poly)
    q_area = '''SELECT curations.jsonld_id as uri, areajson
        FROM curations
        JOIN
            (SELECT curation_id, ST_AsGeoJSON(area) as areajson
            FROM curation_elements
            WHERE {} canvas_id = {}) as cue
        ON curations.id = cue.curation_id;
        '''.format(area_query_insert, can_db_id)
    cur_uris = db_engine.execute(q_area).fetchall()

    backlinks_flat = []
    for row in cur_uris:
        uri = row['uri']
        area = json.loads(row['areajson'])
        backlinks_flat.append([uri, area])
    # backlinks_by_uri = {}
    # for bl in backlinks_flat:
    #     uri, area = bl
    #     if uri not in backlinks_by_uri:
    #         backlinks_by_uri[uri] = {'areas':[]}
    #     backlinks_by_uri[uri]['areas'].append(area)
    backlinks_by_area = {}
    for bl in backlinks_flat:
        uri, area = bl
        coords = area['coordinates'][0]
        if not len(coords) == 5:
            print('unexpected polygon shape (!!!)')  # FIXME problem
        p1, p2, p3, p4, p5 = coords
        xywh = '{},{},{},{}'.format(p1[0], p1[1], p2[0]-p1[0], p3[1]-p1[1])
        if xywh not in backlinks_by_area:
            backlinks_by_area[xywh] = []
        backlinks_by_area[xywh].append(uri)
    display_curation = build_curba_curation(canvas_uri, can_db_man_jsonld_id, backlinks_by_area)

    # ret = {
    #     'canvas': canvas_uri,
    #     'curations_backlinks': backlinks_by_area
    #     }

    return jsonify(display_curation)

if __name__ == '__main__':
    app.run(port=cfg.cfg['port'])
