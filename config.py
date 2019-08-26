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
        cfg['db_uri'] = 'postgresql+psycopg2://curba:curbacurba@localhost:5432/curba'
        cfg['log_file'] = 'log.txt'
        cfg['activity_stream_list'] = ['http://localhost:5000/as/collection.json']
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
                if key == 'db_uri':
                    cfg['db_uri'] = val
                elif key == 'log_file':
                    cfg['log_file'] = val
                elif key == 'activity_stream_list':
                    urls = val.split(',')
                    cfg['activity_stream_list'] = [url.strip() for url in urls]
                else:
                    print('WARNING: unexpected config entry "{}" i'
                          'n section [environment]'.format(key))

        if fails:
            fail = '\n'.join(fails)
        else:
            fail = False

        return fail, cfg
