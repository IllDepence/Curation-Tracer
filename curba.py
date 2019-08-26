import atexit
import json
import time
import urllib.parse
from config import Cfg
from crawler import crawl
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

@app.route('/', methods=['GET'])
def index():
    canvas_uri_raw = request.args.get('canvas')
    area_xywh = request.args.get('area_xywh')
    if not (canvas_uri_raw and area_xywh):
        return abort(400)
    canvas_uri = urllib.parse.unquote(canvas_uri_raw)
    x, y, w, h = [int(elem) for elem in area_xywh.split(',')]

    cfg = Cfg()
    db_engine = create_engine(cfg.cfg['db_uri'])

    q_can = sqla_text('''
        SELECT id
        FROM canvases
        WHERE jsonld_id=:can_uri
        ''')
    print(canvas_uri)
    can_db_id = db_engine.execute(
        q_can,
        can_uri=canvas_uri
        ).fetchall()
    if not can_db_id:
        return abort(404)  # FIXME not there, respond accordingly
    else:
        if len(can_db_id) == 1:
            can_db_id = int(can_db_id[0]['id'])
        else:
            print('multiple canvases w/ same ID (!!!)')  # FIXME problem

    poly = ('ST_GeomFromText('
        '\'POLYGON(({} {}, {} {}, {} {}, {} {}, {} {}))\')').format(
        x, y,
        x+w, y,
        x+w, y+h,
        x, y+h,
        x, y
        )
    q_area = '''SELECT curations.jsonld_id as uri, areajson
        FROM curations
        JOIN
            (SELECT curation_id, ST_AsGeoJSON(area) as areajson
            FROM curation_elements
            WHERE ST_Within(area, {}) and canvas_id = {}) as cue
        ON curations.id = cue.curation_id;
        '''.format(poly, can_db_id)
    cur_uris = db_engine.execute(
        q_area,
        can_uri=canvas_uri
        ).fetchall()

    backlinks = {}
    for row in cur_uris:
        uri = row['uri']
        area = json.loads(row['areajson'])
        if uri not in backlinks:
            backlinks[uri] = {'areas':[]}
        backlinks[uri]['areas'].append(area)

    ret = {
        'canvas': canvas_uri,
        'curations_backlinks': backlinks
        }

    return jsonify(ret)

if __name__ == '__main__':
    app.run(port=cfg.cfg['port'])
