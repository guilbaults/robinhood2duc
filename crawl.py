import MySQLdb
import argparse
import re
import lustreapi
from buf import buf
import sqlite3
import os


class RobinhoodCrawler(object):
    def __init__(self, config, db_path, device):
        self.config = config
        self.device = device

        # Get the database connection info from Robinhood's config file
        with open(config) as c:
            content = c.read()
            self.server = re.findall(r'server = (.*);', content)[0]
            self.db_name = re.findall(r'db = (.*);', content)[0]
            self.user = re.findall(r'user = (.*);', content)[0]
            password_file = re.findall(r'password_file = (.*);', content)[0]
            with open(password_file) as pf:
                self.password = pf.read().strip()

        # Connect to the MySQL used by robinhood
        self.db = MySQLdb.connect(
            host=self.server,
            port=3306,
            user=self.user,
            password=self.password,
            db=self.db_name)

        # Create a new sqlite database, remove the old one first
        try:
            os.remove(args.db_path)
        except FileNotFoundError:
            pass
        self.conn = sqlite3.connect(args.db_path)
        self.cursor = self.conn.cursor()
        # Using sqlite as a key value database compatible with duc format
        self.cursor.execute(
            "CREATE TABLE blobs(key unique primary key, value);")
        self.cursor.execute("CREATE INDEX keys on blobs(key);")

    def type_mapping(self, rbh_type):
        types = {
            'blk': 0,
            'chr': 1,
            'dir': 2,
            'fifo': 3,
            'symlink': 4,
            'file': 5,
            'sock': 6,
        }
        return types[rbh_type]

    def fid2inode(self, fid):
        if type(fid) is str:
            components = fid.split(':')
        else:
            components = fid.decode('utf-8').split(':')
        inode = (int(components[0], 16) << 24) + (int(components[1], 16))
        return inode

    def crawl(self, fid):
        count = 0
        size = 0
        blocks = 0
        cursor = self.db.cursor(MySQLdb.cursors.DictCursor)
        # get the directory inode info
        cursor.execute("select last_mod from ENTRIES where id=%s", (fid,))
        mtime = cursor.fetchone()['last_mod']
        # get all the entries in the directory
        cursor.execute("select ENTRIES.id,name,type,size,blocks,last_mod \
from NAMES join ENTRIES on NAMES.id=ENTRIES.id \
where NAMES.parent_id=%s", (fid,))
        entries = cursor.fetchall()
        cursor.close()

        # Encode the information into duc binary format
        b = buf()
        b.int_encode(self.device)  # device
        b.int_encode(self.fid2inode(fid))  # inode
        b.int_encode(mtime)  # mtime
        # need to crawl depth first, so lets call ourself in each sub dirs
        for row in filter(lambda x: (x['type'] == 'dir'), entries):
            # need to recursive crawl in it
            recurse = self.crawl(row['id'])
            count += recurse['count'] + 1
            size += recurse['size']
            blocks += recurse['blocks'] + 8

            b.string_encode(row['name'])
            b.int_encode(recurse['size'])
            b.int_encode(recurse['blocks'] * 512)  # empty dir takes 4096 bytes
            b.int_encode(recurse['count'] + 1)
            b.int_encode(self.type_mapping(row['type']))  # = directory
            b.int_encode(self.device)  # device number
            b.int_encode(self.fid2inode(row['id']))

        # only files are left in the directory, sum them up
        for row in filter(lambda x: (x['type'] != 'dir'), entries):
            count += 1
            size += row['size']
            blocks += row['blocks']

            # Add en entry in the directory
            b.string_encode(row['name'])
            b.int_encode(row['size'])
            b.int_encode(row['blocks'] * 512)
            b.int_encode(1)  # count of 1 file per file...
            b.int_encode(self.type_mapping(row['type']))  # file type

        devino = '{0:x}/{1:x}'.format(self.device, self.fid2inode(fid))
        # Add the binary information to the k/v store
        self.cursor.execute('INSERT OR REPLACE INTO blobs VALUES(?, ?)',
                            (devino, b.tmp_buf))
        # This is a recursive function
        # return the sum of everything underneath us
        return {'count': count, 'size': size, 'blocks': blocks}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='This tool is used to create a `duc` compatible \
database. The content is generated from the MySQL database managed by \
Robinhood.')
    parser.add_argument(
        'config',
        type=str,
        help='Robinhood config path')
    parser.add_argument(
        'path',
        type=str,
        help='Path where to start the crawl')
    parser.add_argument(
        'db_path',
        type=str,
        help='Path to the output sqlite database file')

    args = parser.parse_args()
    device = os.stat(args.path).st_dev

    path = os.path.realpath(args.path)

    start_fid = str(lustreapi.path2fid(path)).strip('[]')
    rbh = RobinhoodCrawler(args.config, args.db_path, device)

    c = rbh.crawl(start_fid)

    # The first directory to be scanned is used by `duc` to find the initials
    # inodes numbers. Other directories are represented with their inode
    # number, not their full path.
    root = buf()
    # path + devino
    root.string_encode(args.path.rstrip('/').encode())
    root.int_encode(device)  # device number
    root.int_encode(rbh.fid2inode(start_fid))  # inode number

    rbh.cursor.execute('INSERT INTO blobs VALUES(?, ?)',
                       (args.path.rstrip('/'), root.tmp_buf))

    rbh.conn.commit()
    rbh.conn.close()
