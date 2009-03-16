import logging
import os.path
import sys

from humbak import bak, dav


def main():
    logging.basicConfig(level=logging.INFO)
    url = sys.argv[1]
    filenames = sys.argv[2:]
    dav_server = dav.DAV.from_url(url)
    for filename in filenames:
        filename = os.path.abspath(filename)
        if os.path.isdir(filename):
            bak.put_dir(dav_server, filename)
        else:
            bak.put_file(dav_server, filename)


if __name__ == '__main__':
    main()

