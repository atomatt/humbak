import base64
import httplib
import sys
import time
import os.path
import urlparse
import urllib


CONN_FACTORY = {'http': httplib.HTTPConnection,
                'https': httplib.HTTPSConnection}


BLOCK_SIZE = 1024*100


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
                print "written: %d (%f bytes/s)" % (bytes_sent, bandwidth)
            return request.getresponse()
        finally:
            f.close()

    def _request(self, method, path, headers=None):
        fullpath = os.path.join(self.connargs['path'], path)
        self.conn.putrequest(method, fullpath)
        request = Request(self.conn)
        auth = base64.b64encode(':'.join([self.connargs['username'],
                                          self.connargs['password']]))
        request.putheader('Authorization', 'Basic %s'%auth)
        for name, value in headers:
            request.putheader(name, value)
        request.endheaders()
        return request


class Request(object):

    def __init__(self, conn):
        self.conn = conn

    def putheader(self, name, value):
        self.conn.putheader(name, value)

    def endheaders(self):
        self.conn.endheaders()

    def send(self, data):
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


def list_collection(conn, path):
    conn.putrequest('PROPFIND', path)
    conn.putheader('Depth', '1')
    conn.putheader('Authorization', 'Basic %s'%auth)
    conn.endheaders()
    response = conn.getresponse()
    print response.status, response.getheaders()
    print response.read()


if __name__ == '__main__':
    import sys
    url = sys.argv[1]
    filenames = sys.argv[2:]
    dav = DAV.from_url(url)
    for filename in filenames:
        print "Putting", filename, "..."
        response = dav.put_file(os.path.join('/test', urllib.quote_plus(os.path.basename(filename), safe='/')), filename)
        if response.status == 501:
            print response.status
            print response.getheaders()
            print response.read()
        else:
            response.read()

