import base64
import httplib
import logging
import sys
import time
import os
import os.path
import urlparse
import urllib


CONN_FACTORY = {'http': httplib.HTTPConnection,
                'https': httplib.HTTPSConnection}


BLOCK_SIZE = 1024*100


log = logging.getLogger(__name__)


class DAV(object):

    def __init__(self, connargs):
        self.connargs = connargs
        self.conn = CONN_FACTORY[self.connargs['scheme']](self.connargs['hostname'], self.connargs.get('port'))

    @classmethod
    def from_url(cls, url):
        return cls(parse_url(url))

    def put_file(self, path, filename):
        content_length = os.path.getsize(filename)
        f = open(filename, 'rb')
        try:
            request = self._request('PUT', path, [('Content-Length', str(content_length))])
            blocks_sent = 0
            bytes_sent = 0
            start_time = time.time()
            while True:
                data = f.read(BLOCK_SIZE)
                if not data:
                    break
                request.send(data)
                end_time = time.time()
                blocks_sent += 1
                bytes_sent += len(data)
                bandwidth = float(bytes_sent) / (end_time-start_time)
                print "written: %d of %d (%f bytes/s)" % (bytes_sent, content_length, bandwidth)
            response = request.getresponse()
            if 400 <= response.status <= 600:
                response.read()
                raise Exception(response.status)
            return response
        finally:
            f.close()

    def list_dir(self, path):
        log.debug("DAV.list_dir: %s", path)
        request = self._request('PROPFIND', path, [('Depth', '1')])
        response = request.getresponse()
        response.read()
        if 400 <= response.status <= 600:
            raise Exception(response.status)
        return response

    def mkdir(self, path):
        log.debug("DAV.mkdir: %s", path)
        request = self._request('MKCOL', path)
        response = request.getresponse()
        response.read()
        if 400 <= response.status <= 600:
            raise Exception(response.status)

    def _request(self, method, path, headers=None):
        fullpath = os.path.join(self.connargs['path'], path.strip('/'))
        self.conn.putrequest(method, fullpath)
        request = Request(self.conn)
        auth = base64.b64encode(':'.join([self.connargs['username'],
                                          self.connargs['password']]))
        request.putheader('Authorization', 'Basic %s'%auth)
        if headers:
            for name, value in headers:
                request.putheader(name, value)
        request.endheaders()
        return request


class Request(object):

    def __init__(self, conn):
        self.conn = conn

    def putheader(self, name, value):
        log.debug("Request.putheader: %s, %s", name, value)
        self.conn.putheader(name, value)

    def endheaders(self):
        log.debug("Request.endheaders")
        self.conn.endheaders()

    def send(self, data):
        log.debug("Request.send %d bytes", len(data))
        self.conn.send(data)

    def getresponse(self):
        return self.conn.getresponse()


def parse_url(url):
    spliturl = urlparse.urlsplit(url)
    return {'scheme': spliturl.scheme,
            'hostname': spliturl.hostname,
            'port': spliturl.port,
            'path': spliturl.path or '/',
            'username': urllib.unquote(spliturl.username) if spliturl.username else None,
            'password': urllib.unquote(spliturl.password) if spliturl.password else None}


def put_dir(dav, filename):
    log.info('DIR: %s'%(filename,))
    try:
        dav.list_dir(filename)
    except Exception, e:
        if e.message != 404:
            raise
        dav.mkdir(filename)
    for root, dirs, files in os.walk(filename):
        for file in files:
            put_file(dav, os.path.join(root, file))
        for dir in dirs:
            put_dir(dav, os.path.join(root, dir))


def put_file(dav, filename):
    log.info('FILE: %s'%(filename,))
    response = dav.put_file(urllib.quote_plus(filename, safe='/'), filename)
    response.read()
    if response.status == 501:
        print response.status
        print response.getheaders()


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)
    url = sys.argv[1]
    filenames = sys.argv[2:]
    dav = DAV.from_url(url)
    for filename in filenames:
        if os.path.isdir(filename):
            put_dir(dav, filename)
        else:
            put_file(dav, filename)

