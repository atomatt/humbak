import logging
import os.path
import sys

from humbak import bak, dav


log = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO)
    url = sys.argv[1]
    filenames = (i.decode('utf-8') for i in sys.argv[2:])
    dav_server = dav.DAV.from_url(url)
    for filename in filenames:
        filename = os.path.abspath(filename)
        log.info("Backing up %s ...", filename)
        if os.path.isdir(filename):
            bak.put_dir(dav_server, filename)
        else:
            bak.put_file(dav_server, filename)
        log.info("Backup of %s complete", filename)
    log.info("All backups complete, exiting.")


if __name__ == '__main__':
    main()

