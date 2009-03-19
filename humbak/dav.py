import base64
import httplib
import logging
import sys
import time
import os.path
import urlparse
import urllib
from xml.etree import ElementTree as etree


CONN_FACTORY = {'http': httplib.HTTPConnection,
                'https': httplib.HTTPSConnection}


BLOCK_SIZE = 1024
MAX_BANDWIDTH = 1024*22.5


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
            request = self.request('PUT', path, [('Content-Length', str(content_length))])
            blocks_sent = 0
            bytes_sent = 0
            start_time = time.time()
            sys.stdout.write(filename)
            sys.stdout.write(': ')
            message_clear = ''
            while True:
                block_start_time = time.time()
                data = f.read(BLOCK_SIZE)
                if not data:
                    break
                request.send(data)
                end_time = time.time()
                blocks_sent += 1
                bytes_sent += len(data)
                bandwidth = float(bytes_sent) / (end_time-start_time)
                if message_clear:
                    sys.stdout.write(message_clear)
                message = "%0.1f%% (%.1f kb/s)" % (100.0*bytes_sent/content_length, bandwidth/1024) 
                sys.stdout.write(message)
                extra_chars = len(message_clear)-len(message)
                if extra_chars > 0:
                    sys.stdout.write(' '*extra_chars)
                    sys.stdout.write('\b'*extra_chars)
                message_clear = "\b"*len(message)
                sys.stdout.flush()
                if bandwidth >= MAX_BANDWIDTH:
                    if end_time - block_start_time < 1:
                        time.sleep(1-(end_time-block_start_time))
            # Clear the line.
            sys.stdout.write('\n')
            sys.stdout.flush()
            # Read the response and check the status.
            response = request.getresponse()
            response.read()
            if 400 <= response.status <= 600:
                response.read()
                raise Exception(response.status)
        finally:
            f.close()

    def list_dir(self, path):
        log.debug("DAV.list_dir: %s", path)
        path = path.rstrip('/')
        request = self.request('PROPFIND', path, [('Depth', '1')])
        response = request.getresponse()
        data = response.read()
        if 400 <= response.status <= 600:
            raise Exception(response.status)
        doc = etree.fromstring(data)
        for e in doc.findall('{DAV:}response'):
            href = urllib.quote(urllib.unquote(e.find('{DAV:}href').text))
            e_path = href[len(os.path.join(self.connargs['path'], path[1:]))+1:]
            if e_path == '':
                continue
            if e.find('{DAV:}propstat/{DAV:}prop/{DAV:}resourcetype/{DAV:}collection') is not None:
                yield {'path': e_path,
                       'type': 'dir'}
            else:
                yield {'path': e_path,
                       'type': 'file',
                       'size': int(e.find('{DAV:}propstat/{DAV:}prop/{DAV:}getcontentlength').text),
                       'etag': e.find('{DAV:}propstat/{DAV:}prop/{DAV:}getetag').text,
                       'ctime': e.find('{DAV:}propstat/{DAV:}prop/{DAV:}creationdate').text,
                       'mtime': e.find('{DAV:}propstat/{DAV:}prop/{DAV:}lastmodifieddate').text}

    def mkdir(self, path):
        log.debug("DAV.mkdir: %s", path)
        request = self.request('MKCOL', path)
        response = request.getresponse()
        response.read()
        if 400 <= response.status <= 600:
            raise Exception(response.status)

    def request(self, method, path, headers=None):
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
            'path': spliturl.path.rstrip('/'),
            'username': urllib.unquote(spliturl.username) if spliturl.username else None,
            'password': urllib.unquote(spliturl.password) if spliturl.password else None}

