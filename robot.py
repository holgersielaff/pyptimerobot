#!/usr/bin/env python3

import asyncio
import datetime
import gzip
import json
import os
import sys
from glob import glob
from os import path
from pathlib import Path
from time import sleep, time

import aiohttp

basedir = str(Path(__file__).parent.absolute())

try:
    with open(path.join(basedir, 'config.json')) as jcfgf:
        jobconfig = json.load(jcfgf)
except:
    with open(path.join(basedir, 'config.default.json')) as jcfgf:
        jobconfig = json.load(jcfgf)

request_timeout = int(jobconfig.get('request_timeout', 15))
sleeptime = int(jobconfig.get('sleeptime', 15))
logrotate_delta = int(jobconfig.get('logrotate_delta', 3600 * 24))  # gzip log each day
logrotate_delta_keep = int(jobconfig.get('logrotate_delta_keep', 3600 * 24 * 14))  # keep gzipped logs for 2 weeks
lockfile = jobconfig.get('lockfile', '/tmp/uptimerobot.lock')
configdir = jobconfig('configdir', path.join(basedir, 'configs'))
errordir = jobconfig.get('errordir', path.join(basedir, 'errors'))
logdir = jobconfig.get('logdir', path.join(basedir, 'logs'))


def load_configs():
    my_configs = []
    for c in glob(configdir + '/*.json'):
        with open(c, 'r') as f:
            my_configs.append(json.load(f))
    return my_configs


def now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def lock():
    with open(lockfile, 'w+') as lockf:
        lockf.write(now())


def unlock():
    if path.isfile(lockfile):
        os.unlink(lockfile)


def has_lock():
    if path.isfile(lockfile):
        with open(lockfile, 'r') as lockf:
            print("Uptimerobot runs since %s" % lockf.read(), file=sys.stderr)
            sys.exit(1)


class ErrorHandler:

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.url = cfg['url']
        self.name = self.url.replace('http://', '').replace('https://', '').replace('/', '.').replace('#', '.')
        self.logfile = path.join(logdir, '%s.log' % self.name)
        self.errorfile = path.join(errordir, self.name)

    def logrotate(self):
        for l in glob(self.logfile + '.*.gz'):
            if time() - path.getctime(l) > logrotate_delta_keep:
                os.unlink(l)
        if path.isfile(self.logfile):
            filetime = int(path.getctime(self.logfile))
            if time() - filetime > logrotate_delta:
                with open(self.logfile, 'rb') as lf_in:
                    gzipname = self.logfile \
                               + '.' \
                               + datetime.datetime.fromtimestamp(filetime).strftime('%Y-%m-%d') \
                               + '_' \
                               + datetime.datetime.now().strftime('%Y-%m-%d') \
                               + '.gz'
                    
                    with gzip.open(gzipname, 'wb') as lf_out:
                        lf_out.writelines(lf_in)
                    
                    os.unlink(self.logfile)

                    with open(self.logfile, 'w+') as lf_in:
                        lf_in.write('')

    def write_log(self, text: str, status: int):
        with open(self.logfile, 'a+') as lf:
            lf.write(now() + ' - ' + str(status) + ' - ' + text.replace('\n', '') + '\n')

    def delete_error(self):
        if self.has_error():
            print("Delete error for %s" % self.name)
            os.unlink(self.errorfile)

    def write_error(self):
        print("Write error for %s" % self.name)
        with open(self.errorfile, 'w+') as ef:
            ef.write(now())

    def has_error(self) -> bool:
        return path.isfile(self.errorfile)

    def on_error(self, text: str, status: int):
        if not self.has_error():
            # noch irgendetwas machen, weil noch nicht getan
            pass
        self.write_error()
        self.write_log(text, status)

    def on_success(self):
        if self.has_error():
            # Wenn ein error für cfg da ist, dann noch was machen (!on_error), ansonsten nicht
            pass
        self.delete_error()


async def fetch(session: aiohttp.ClientSession, cfg: dict):
    try:
        async with session.get(cfg['url']) as resp:
            print(cfg['url'], resp.status, file=sys.stderr)
            if not resp.ok:
                txt = await resp.text()
                cfg['errorhandler'].on_error(text=txt, status=resp.status)
            else:
                cfg['errorhandler'].on_success()
    except Exception as e:
        cfg['errorhandler'].on_error(text=str(e), status=9000)


async def fetch_all(configs: list, loop: asyncio.AbstractEventLoop):
    async with aiohttp.ClientSession(
            loop=loop,
            timeout=aiohttp.ClientTimeout(request_timeout),
            connector=aiohttp.TCPConnector(ssl=False)
    ) as session:
        return await asyncio.gather(*[fetch(session, cfg) for cfg in configs])


if __name__ == '__main__':
    has_lock()
    lock()

    # TODO - chunk 
    configs = load_configs()

    for cfg in configs:
        cfg['errorhandler'] = ErrorHandler(cfg)

    loop = asyncio.get_event_loop()

    try:
        while True:
            for cfg in configs:
                cfg['errorhandler'].logrotate()
            loop.run_until_complete(fetch_all(configs, loop))
            sleep(sleeptime)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e, file=sys.stderr)
        pass
    finally:
        unlock()
