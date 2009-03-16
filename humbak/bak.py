import logging
import os.path
import urllib


log = logging.getLogger(__name__)


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


