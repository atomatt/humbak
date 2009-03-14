import base64
import httplib
import sys

username, password = sys.argv[1:]
auth = base64.b64encode(':'.join([username, password]))

conn = httplib.HTTPSConnection('dav.humyo.com')

conn.connect()
try:
    conn.putrequest('PROPFIND', '/')
    conn.putheader('Depth', '1')
    conn.putheader('Authorization', 'Basic %s'%auth)
    conn.endheaders()
    response = conn.getresponse()
    print response.status, response.getheaders()
    print response.read()
    print
    conn.putrequest('PROPFIND', '/')
    conn.putheader('Depth', '1')
    conn.putheader('Authorization', 'Basic %s'%auth)
    conn.endheaders()
    response = conn.getresponse()
    print response.status, response.getheaders()
    print response.read()
finally:
    conn.close()

