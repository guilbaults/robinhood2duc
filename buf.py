class buf:
    def __init__(self, input_buf=None):
        self.buf = input_buf
        self.offset = 0
        self.tmp_buf = bytearray()

    def output(self):
        return self.tmp_buf

    def int_encode(self, z):
        if z <= 240:
            self.tmp_buf.append(z)
        elif z <= 2287:
            self.tmp_buf.append((z-240)//256 + 241)
            self.tmp_buf.append((z-240) % 256)
        elif z <= 67823:
            self.tmp_buf.append(249)
            self.tmp_buf.append((z-2288)//256)
            self.tmp_buf.append((z-2288) % 256)
        elif z <= 16777215:
            self.tmp_buf.append(250)
            self.tmp_buf.extend(z.to_bytes(3, 'big'))
        elif z <= 4294967295:
            self.tmp_buf.append(251)
            self.tmp_buf.extend(z.to_bytes(4, 'big'))
        elif z <= 1099511627775:
            self.tmp_buf.append(252)
            self.tmp_buf.extend(z.to_bytes(5, 'big'))
        elif z <= 281474976710655:
            self.tmp_buf.append(253)
            self.tmp_buf.extend(z.to_bytes(6, 'big'))
        elif z <= 72057594037927935:
            self.tmp_buf.append(254)
            self.tmp_buf.extend(z.to_bytes(7, 'big'))
        else:
            self.tmp_buf.append(255)
            self.tmp_buf.extend(z.to_bytes(8, 'big'))

    def int_decode(self):
        # decode and move the read offset
        d = self._int_decode(self.buf[self.offset:self.offset + 9])
#        print('decoded', self.buf[self.offset:self.offset + d[1]])
        self.offset += d[1]
#        print('new offset', self.offset)
        return d[0]

    def _int_decode(self, z):
        # return the int and the number of bytes read
        if z[0] <= 240:
            return (z[0], 1)
        elif z[0] >= 241 and z[0] <= 248:
            return (240+256*(z[0]-241)+z[1], 2)
        elif z[0] == 249:
            return (2288+256*z[1]+z[2], 3)
        elif z[0] == 250:
            return((z[1] << 16) + (z[2] << 8) + z[3], 4)
        elif z[0] == 251:
            return ((z[1] << 24) + (z[2] << 16) + (z[3] << 8) + z[4], 5)
        elif z[0] == 252:
            return ((z[1] << 32) + (z[2] << 24) + (z[3] << 16) +
                    (z[4] << 8) + z[5], 6)
        elif z[0] == 253:
            return ((z[1] << 40) + (z[2] << 32) + (z[3] << 24) +
                    (z[4] << 16) + (z[5] << 8) + z[6], 7)
        elif z[0] == 254:
            return ((z[1] << 48) + (z[2] << 40) + (z[3] << 32) +
                    (z[4] << 24) + (z[5] << 16) + (z[6] << 8) + z[7], 8)
        elif z[0] == 255:
            return ((z[1] << 56) + (z[2] << 48) + (z[3] << 40) +
                    (z[4] << 32) + (z[5] << 24) + (z[6] << 16) +
                    (z[7] << 8) + z[8], 9)

    def string_encode(self, string):
        self.int_encode(len(string))  # add the string length to the buffer
        self.tmp_buf.extend(string)

    def string_decode(self):
        # strings have their length before the ascii
        length = self.int_decode()
        return self._string_decode(length)

    def _string_decode(self, length):
        s = self.buf[self.offset:self.offset + length]
        self.offset += length
        return s

    def dir_ent(self):
        out = {
            'filename': self.string_decode(),
            'actual size': self.int_decode(),
            'apparent size': self.int_decode(),
            'count': self.int_decode(),
            'type': self.int_decode()
        }
        if out['type'] == 2:
            # directory
            out['device'] = self.int_decode()
            out['inode'] = self.int_decode()
        return out


def t_encode_decode_int(i):
    a = buf()
    a.int_encode(i)
    return buf(a.output()).int_decode()


def test_int_128():
    assert t_encode_decode_int(128) == 128


def test_int_400():
    assert t_encode_decode_int(400) == 400


def test_int_67700():
    assert t_encode_decode_int(67700) == 67700


def test_int_16777210():
    assert t_encode_decode_int(16777210) == 16777210


def test_int_4294967290():
    assert t_encode_decode_int(4294967290) == 4294967290


def test_int_1099511627770():
    assert t_encode_decode_int(1099511627770) == 1099511627770


def test_int_281474976710650():
    assert t_encode_decode_int(281474976710650) == 281474976710650


def test_int_72057594037927930():
    assert t_encode_decode_int(72057594037927930) == 72057594037927930


def test_int_72057594037927939():
    assert t_encode_decode_int(72057594037927939) == 72057594037927939


def test_string():
    a = buf()
    a.string_encode('Hello world!'.encode())
    assert buf(a.output()).string_decode() == 'Hello world!'.encode()


def test_multiple_int():
    a = buf()
    a.int_encode(42)
    a.int_encode(401)
    a.int_encode(1099511627706)
    b = buf(a.output())
    assert b.int_decode() == 42
    assert b.int_decode() == 401
    assert b.int_decode() == 1099511627706


if __name__ == '__main__':
    import sqlite3
#    conn = sqlite3.connect('/home/centos/.duc.db')
    conn = sqlite3.connect('database.sqlite')

    c = conn.cursor()

    print('everything in the DB, except the index report')
    for row in c.execute("SELECT * FROM blobs where key!='duc_index_reports'"):
        b = buf(row[1])
        print('device', b.int_decode())
        print('inode', b.int_decode())
        print('mtime', b.int_decode())

        got_dirs = True
        while got_dirs:
            try:
                print(b.dir_ent())
            except IndexError:
                got_dirs = False

    print('getting the initial path')
    for row in c.execute("SELECT * FROM blobs where key='/mnt/demo/env'"):
        b = buf(row[1])
        print('path', b.string_decode())
        print('device', hex(b.int_decode()))
        print('inode', hex(b.int_decode()))

    print('getting a directory, using previous devino')
    for row in c.execute("SELECT * FROM blobs \
where key='9cdf5d4a/200000402000003'"):
        b = buf(row[1])
        print('device', hex(b.int_decode()))
        print('inode', hex(b.int_decode()))
        print('mtime', hex(b.int_decode()))

        got_dirs = True
        while got_dirs:
            try:
                print(b.dir_ent())
            except IndexError:
                got_dirs = False

    print('index report')
    for row in c.execute("SELECT * FROM blobs where key='duc_index_reports'"):
        b = buf(row[1])
        print('path', row[1])
#        print('device', b.int_decode())
#        print('inode', b.int_decode())
#        print('start time', b.int_decode())
#        print('start utime', b.int_decode())
#        print('stop time', b.int_decode())
#        print('stop utime', b.int_decode())
#        print('file count', b.int_decode())
#        print('dir count', b.int_decode())
#        print('actual size', b.int_decode())
#        print('apparant size', b.int_decode())
