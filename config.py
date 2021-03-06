""" Class to comfortably get config values.
"""

import configparser
import os
import sys


class Cfg():

    def __init__(self, path='config.ini'):
        cp = configparser.ConfigParser()
        if os.path.exists(path):
            cp.read(path)
        else:
            msg = 'Config file "{}" not found. Using defaults.'.format(path)
            print(msg)
            self.log_cfg(None, msg)
        fail, cfg = self._parse_config(cp)
        if fail:
            msg = '{} Exiting.'.format(fail)
            print(msg)
            sys.exit(1)
        self.cfg = cfg

    def _get_default_config(self):
        cfg = {}
        cfg['port'] = 5000
        cfg['db_uri'] = 'postgresql+psycopg2://tracer:tracertracer@localhost:5432/tracer'
        cfg['log_file'] = 'log.txt'
        cfg['crawl_interval'] = 6
        cfg['activity_stream_list'] = ['http://localhost:5000/as/collection.json']
        cfg['curation_link_prefix'] = ''
        cfg['marker_settings'] = {}
        cfg['marker_settings']['border-color'] = '#0f0'
        return cfg


    def _parse_config(self, cp):
        """ Prase a configparser.ConfigParser instance and return
                - a fail message in case of an invalid config (False otherwise)
                - a config dict
        """

        cfg = self._get_default_config()
        fails = []

        # Environment
        if 'environment' in cp.sections():
            for (key, val) in cp.items('environment'):
                if key == 'port':
                    cfg['port'] = int(val)
                elif key == 'db_uri':
                    cfg['db_uri'] = val
                elif key == 'log_file':
                    cfg['log_file'] = val
                elif key == 'curation_link_prefix':
                    cfg['curation_link_prefix'] = val
                elif key == 'crawl_interval':
                    cfg['crawl_interval'] = int(val)
                elif key == 'activity_stream_list':
                    urls = val.split(',')
                    cfg['activity_stream_list'] = [url.strip() for url in urls]
                else:
                    print('WARNING: unexpected config entry "{}" i'
                          'n section [environment]'.format(key))
        # Marker
        if 'marker' in cp.sections():
            for (key, val) in cp.items('marker'):
                cfg['marker_settings'][key] = val

        if fails:
            fail = '\n'.join(fails)
        else:
            fail = False

        return fail, cfg
