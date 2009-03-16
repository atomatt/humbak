import base64
import httplib
import logging
import sys
import time
import os
import os.path
import urlparse
import urllib
from xml.etree import ElementTree as etree


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
            request = self.request('PUT', path, [('Content-Length', str(content_length))])
            blocks_sent = 0
            bytes_sent = 0
            start_time = time.time()
            message_clear = ''
            while True:
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
                message = "written: %d of %d (%d bytes/s)" % (bytes_sent, content_length, bandwidth) 
                sys.stdout.write(message)
                extra_chars = len(message_clear)-len(message)
                if extra_chars > 0:
                    sys.stdout.write(' '*extra_chars)
                    sys.stdout.write('\b'*extra_chars)
                message_clear = "\b"*len(message)
                sys.stdout.flush()
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


def put_dir(dav, dir):
    log.info('DIR: %s'%(dir,))
    for root, dirs, files in os.walk(dir):
        try:
            dir_list = list(dav.list_dir(urllib.quote(root)))
        except Exception, e:
            if e.message != 404:
                raise
            mkdir(dav, root)
            dir_list = list(dav.list_dir(urllib.quote(root)))
        info_by_filename = dict((i['path'], i) for i in dir_list)
        for file in files:
            fullfile = os.path.join(root, file)
            log.info('FILE: %s', fullfile)
            info = info_by_filename.get(urllib.quote(file))
            if info:
                mtime = os.path.getmtime(fullfile)
                size = os.path.getsize(fullfile)
                if size == info['size']:
                    log.info("Skipping file: %s", fullfile)
                    continue
            log.info("Sending file: %s", fullfile)
            dav.put_file(urllib.quote(fullfile), fullfile)


def mkdir(dav, root):
    root = root.split('/')
    for i in range(len(root), 0, -1):
        request = dav.request('HEAD', urllib.quote('/'.join(root[:i])))
        response = request.getresponse()
        response.read()
        if response.status == 200:
            break
    i += 1
    while i <= len(root):
        dav.mkdir(urllib.quote('/'.join(root[:i])))
        i += 1


def put_file(dav, filename):
    log.info('FILE: %s'%(filename,))
    dav.put_file(urllib.quote(filename), filename)


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)
    url = sys.argv[1]
    filenames = sys.argv[2:]
    dav = DAV.from_url(url)
    for filename in filenames:
        filename = os.path.abspath(filename)
        if os.path.isdir(filename):
            put_dir(dav, filename)
        else:
            put_file(dav, filename)

