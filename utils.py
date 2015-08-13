import random


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


def mutate_bits(value, size=8, odds_multiplier=2.0):
    bits_set = bin(value).count('1')
    bits_unset = size - bits_set
    assert bits_unset >= 0
    lowvalue = min(bits_set, bits_unset)
    lowvalue = max(lowvalue, 1)
    multiplied = int(round(size * odds_multiplier))
    for i in range(size):
        if random.randint(1, multiplied) <= lowvalue:
            value ^= (1 << i)
    return value


BOOST_AMOUNT = 2.0


def mutate_normal(value, minimum=0, maximum=0xFF,
                  reverse=False, smart=True, chain=True):
    value = max(minimum, min(value, maximum))
    rev = reverse
    if smart:
        if value > (minimum + maximum) / 2:
            rev = True
        else:
            rev = False

    if rev:
        value = maximum - value
    else:
        value = value - minimum

    BOOST_FLAG = False
    if value < BOOST_AMOUNT:
        value += BOOST_AMOUNT
        if value > 0:
            BOOST_FLAG = True
        else:
            value = 0

    if value > 0:
        half = value / 2.0
        a, b = random.random(), random.random()
        value = half + (half * a) + (half * b)

    if BOOST_FLAG:
        value -= BOOST_AMOUNT

    if rev:
        value = maximum - value
    else:
        value = value + minimum

    if chain and random.randint(1, 10) == 10:
        return mutate_normal(value, minimum=minimum, maximum=maximum,
                             reverse=reverse, smart=smart, chain=True)
    else:
        value = max(minimum, min(value, maximum))
        value = int(round(value))
        return value


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


def hexstring(value):
    if type(value) is str:
        value = "".join(["{0:0>2}".format("%x" % ord(c)) for c in value])
    elif type(value) is int:
        value = "{0:0>2}".format("%x" % value)
    return value


class classproperty(property):
    def __get__(self, inst, cls):
        return self.fget(cls)
