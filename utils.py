from os import path
import random

try:
    from sys import _MEIPASS
    tblpath = path.join(_MEIPASS, "tables")
except ImportError:
    tblpath = "tables"


TABLE_SPECS = {}
for table_type in ["unit", "job_reqs"]:
    TABLE_SPECS[table_type] = path.join(tblpath, "%s_table.txt" % table_type)


def int2bytes(value, length=2, reverse=True):
    # reverse=True means high-order byte first
    bs = []
    while value:
        bs.append(value & 255)
        value = value >> 8

    while len(bs) < length:
        bs.append(0)

    if not reverse:
        bs = reversed(bs)

    return bs[:length]


def read_multi(f, length=2, reverse=True):
    vals = map(ord, f.read(length))
    if reverse:
        vals = list(reversed(vals))
    value = 0
    for val in vals:
        value = value << 8
        value = value | val
    return value


def write_multi(f, value, length=2, reverse=True):
    vals = []
    while value:
        vals.append(value & 0xFF)
        value = value >> 8
    if len(vals) > length:
        raise Exception("Value length mismatch.")

    while len(vals) < length:
        vals.append(0x00)

    if not reverse:
        vals = reversed(vals)

    f.write(''.join(map(chr, vals)))


utilrandom = random.Random()
utran = utilrandom
random = utilrandom


def mutate_index(index, length, continuation=None,
                 basic_range=None, extended_range=None):
    if length == 0:
        return None

    highest = length - 1
    continuation = continuation or [True, False]
    basic_range = basic_range or (-3, 3)
    extended_range = extended_range or (-1, 1)

    index += utran.randint(*basic_range)
    index = max(0, min(index, highest))
    while utran.choice(continuation):
        index += utran.randint(*extended_range)
        index = max(0, min(index, highest))

    return index


def line_wrap(things, width=16):
    newthings = []
    while things:
        newthings.append(things[:width])
        things = things[width:]
    return newthings
