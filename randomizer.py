from shutil import copyfile
import os
from os import remove, path
import sys
from sys import argv, stdout
from time import time
import string
from string import lowercase
from collections import Counter, defaultdict
from itertools import product

from randomtools.utils import (
    mutate_index, mutate_normal, mutate_bits, read_multi, write_multi,
    classproperty, utilrandom as random)
from randomtools.tablereader import (
    TableObject, set_global_table_filename, set_table_specs)
from randomtools.uniso import remove_sector_metadata, inject_logical_sectors


try:
    from sys import _MEIPASS
    tblpath = path.join(_MEIPASS, "tables")
except ImportError:
    tblpath = "tables"


NAMESFILE = path.join(tblpath, "generic_names.txt")
MESSAGESFILE = path.join(tblpath, "message_pointers.txt")
MESHESFILE = path.join(tblpath, "mesh_pointers.txt")
MAPMOVESFILE = path.join(tblpath, "map_movements.txt")
CONDITIONALSFILE = path.join(tblpath, "conditionals.dat")


def randint(a, b):
    return random.randint(min(a, b), max(a, b))


def slice_array_2d(data, x=0, width=0, y=0, length=0):
    newdata = [row[x:x+width] for row in data][y:y+length]
    try:
        assert len(newdata) == length
        assert len(newdata[0]) == width
    except AssertionError:
        raise Exception("Array slice out of bounds.")
    return newdata


progress_length = None


def set_progress_counter(length):
    global progress_length
    progress_length = length


def check_progress_counter(index):
    n = (index * 10) / progress_length
    if n != ((index-1) * 10) / progress_length:
        stdout.write("%s " % (10-n))
        if n == 9:
            stdout.write("\n")
    stdout.flush()


VERSION = "21"
MD5HASHES = ["b156ba386436d20fd5ed8d37bab6b624",
             "aefdf27f1cd541ad46b5df794f635f50",
             ]
JPMD5HASHES = ["3bd1deebc5c5f08d036dc8651021affb"]
JAPANESE_MODE = False
RAWMD5HASHES = ["55a8e2ad81ee308b573a2cdfb0c3c270",
                "4851a6f32d6546eed65319c319ea8b55",
                ]
ISO_SIZES = [541310448, 541315152]
RAW_SIZES = [471345152]
DAYS_IN_MONTH = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
                 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}

X_FORMULAS = [0x9, 0xA, 0xB, 0xD, 0xE, 0xF, 0x10, 0x12, 0x14, 0x15, 0x16, 0x17,
              0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F, 0x25, 0x26, 0x27, 0x28, 0x29,
              0x2A, 0x2B, 0x2C, 0x32, 0x33, 0x35, 0x3B, 0x3D, 0x3F, 0x40, 0x41,
              0x42, 0x4D, 0x4F, 0x50, 0x51, 0x53, 0x55, 0x56, 0x58, 0x59, 0x5C,
              0x5E, 0x61, 0x62
              ]
Y_FORMULAS = [0x8, 0x9, 0xC, 0xD, 0xE, 0xF, 0x10, 0x1A, 0x1B, 0x1E, 0x1F, 0x20,
              0x21, 0x23, 0x24, 0x28, 0x2A, 0x2C, 0x2D, 0x31, 0x32, 0x34, 0x35,
              0x36, 0x37, 0x39, 0x3A, 0x3B, 0x42, 0x47, 0x4C, 0x4D, 0x4E, 0x54,
              0x55, 0x56, 0x5B, 0x5C, 0x5E, 0x5F, 0x60, 0x61, 0x62
              ]

VALID_INNATE_STATUSES = 0xCAFCE12A10
VALID_START_STATUSES = (VALID_INNATE_STATUSES |
                        0x1402100000)
BENEFICIAL_STATUSES =   0xC278600000
RERAISE_STATUS =        0x0000200000
REGEN_STATUS =          0x0040000000
FAITH_STATUS =          0x8000000000
INNOCENT_STATUS =       0x4000000000
INVITE_STATUS =         0x0000004000
BANNED_SKILLS = range(0x165, 0x16F)
BANNED_SKILLSET_SHUFFLE = [0, 1, 2, 3, 6, 8, 0x11, 0x12, 0x13, 0x14, 0x15,
                           0x18, 0x34, 0x38, 0x39, 0x3B, 0x3E, 0x9C, 0xA1]
MATH_SKILLSETS = [0xA, 0xB, 0xC, 0x10]
BANNED_RSMS = [0x1BB, 0x1D7, 0x1E1, 0x1E4, 0x1E5, 0x1F1]
BANNED_ANYTHING = [0x18]
BANNED_ITEMS = [0x49]
MP_RESTORE_INNATES = [0x1EE, 0x1B6, 0x1B0]
LUCAVI_INNATES = (range(0x1A6, 0x1A9) + [0x1AA] + range(0x1AC, 0x1B0)
                  + range(0x1B1, 0x1B4) + [0x1B5, 0x1BA, 0x1BD, 0x1BE]
                  + range(0x1C0, 0x1C6)
                  + range(0x1D1, 0x1D6) + [0x1D8, 0x1DD, 0x1E3]
                  + [0x1E7, 0x1E8]
                  + range(0x1EB, 0x1EE) + [0x1F2, 0x1F3, 0x1FA, 0x1FB]
                  ) + MP_RESTORE_INNATES


LUCAVI_JOBS = [0x3C, 0x3E, 0x40, 0x41, 0x43, 0x45, 0x49, 0x97]
LUCAVI_ORDER = [0x43, 0x3C, 0x3E, 0x45, 0x40, 0x41, 0x97, 0x49]
BASIC_JOBS = range(0x4A, 0x5E)
MONSTER_JOBS = range(0x5E, 0x8E) + [0x90, 0x91, 0x96, 0x97, 0x99, 0x9A]
STORYLINE_RECRUITABLE_JOBS = [0xD, 0xF, 0x16, 0x1A, 0x1E, 0x1F,
                              0x29, 0x2A, 0x90, 0x91]
USED_MAPS = range(0, 0x14B) + range(0x180, 0x1d6)
FIXED_WEATHER = [0x1b5, 0x1c2]

jobreq_namedict = {}
jobreq_indexdict = {}
JOBNAMES = ["squire", "chemist", "knight", "archer", "monk", "priest",
            "wizard", "timemage", "summoner", "thief", "mediator", "oracle",
            "geomancer", "lancer", "samurai", "ninja", "calculator", "bard",
            "dancer", "mime"]
JOBLEVEL_JP = [100, 200, 350, 550, 800, 1150, 1550, 2100]

# Ry Edit: List of formulas that should be able to inflict status
STATUS_FORMULAS = [1, 8, 9, 0xA, 0xB, 0xD, 0xE, 0x1E, 0x1F, 0x20, 0x21,
                   0x22, 0x24, 0x26, 0x28, 0x29, 0x2D, 0x31, 0x33, 0x35,
                   0x38, 0x3D, 0x3F, 0x40, 0x41, 0x47, 0x4E, 0x50, 0x51,
                   0x52, 0x53, 0x57, 0x5A, 0x5B, 0x5E, 0x5F, 0x60]


mapsprite_restrictions = {}
mapsprite_selection = {}
monster_selection = {}
mapunits = {}
mapsprites = {}
named_jobs = {}
named_map_jobs = {}
backup_jobreqs = None
rankdict = None
ranked_skills_dict = {}
g_monster_skills = None
g_ranked_monster_jobs = None
g_ranked_secondaries = None
birthday_dict = {}
boostd = {}
rng_report_counter = 0

SUPER_LEVEL_BOOSTED = []
SUPER_SPECIAL = []


chartable = enumerate(string.digits + string.uppercase + string.lowercase)
chartable = list(chartable) + [(0xFA, " "), (0xD9, '~'),
                               (0xB6, '.'), (0xC1, "'")]
chartable += [(v, k) for (k, v) in chartable]
chartable = dict(chartable)


def name_to_bytes(name):
    name = "".join([chr(chartable[c]) for c in name])
    return name


def bytes_to_name(data):
    name = "".join([chartable[i] for i in data])
    return name


def set_difficulty_factors(value):
    value = max(value, 0)
    try:
        boostd["difficulty_factor"] = value
        boostd["common_item"] = max(2.0 - (0.5 * value), 0.5)
        boostd["trophy"] = max(1.5 - (0.5 * value), 0.25)
        boostd["default_stat"] = 1.2 ** value
        boostd["level_stat"] = 0.6 * value
        boostd["lucavi_stat"] = 0.75 * value
        boostd["equipment"] = 1.1 ** value
        boostd["special_equipment"] = 1.5 ** value
        boostd["jp"] = 1.5 ** value
        boostd["random_special_unit"] = 0.5 + (1.0 * value)
        boostd["story_special_unit"] = 0.0 + (1.0 * value)
    except OverflowError:
        print "Max chaos multiplier exceeded. Using a multiplier of 500."
        set_difficulty_factors(500.0)


def get_rng_state():
    global rng_report_counter
    rng_report_counter += 1
    return rng_report_counter, sum(random.getstate()[1]) % (10**20)


def get_md5_hash(filename):
    from hashlib import md5
    m = md5()
    f = open(filename, 'r+b')
    while True:
        data = f.read(128)
        if data:
            m.update(data)
        else:
            break
    f.close()
    return m.hexdigest()


def calculate_jp_total(joblevels):
    total = 0
    for j in joblevels:
        if j == 0:
            continue
        total += JOBLEVEL_JP[j-1]
    return total


def rewrite_header(filename, message):
    if len(message) > 0x20:
        print "WARNING: Cannot write full seed info to rom."
        message = message[:0x1F] + "~"
    while len(message) < 0x20:
        message += " "
    assert len(message) == 0x20
    f = open(filename, 'r+b')
    # pointer OK for both NA and JP
    f.seek(0x8028)
    f.write(message)
    f.close()


TEMPFILE = "_fftrandom.tmp"


class TileObject:
    def __init__(self, bytestring):
        bytestring = [ord(c) for c in bytestring]
        self.terrain_type = bytestring[0] & 0x3F
        self.height = bytestring[2]
        self.depth = bytestring[3] >> 5
        self.slope_height = bytestring[3] & 0x1F
        self.slope_type = bytestring[4]
        self.impassable = (bytestring[6] >> 1) & 1
        self.uncursorable = bytestring[6] & 1
        self.occupied = 0
        self.party = 0
        self.upper = 0
        self.unreachable = 0

    @property
    def bad(self):
        if self.occupied or self.unreachable:
            return 1
        return self.bad_regardless

    @property
    def bad_regardless(self):
        if self.impassable | self.uncursorable:
            return 1
        if self.slope_height > 2:
            return 1
        if self.depth > 2:
            return 1
        return 0

    def set_unreachable(self, unreachable=1):
        self.unreachable = unreachable

    def set_occupied(self, occupied=1):
        self.occupied = occupied

    def set_party(self, party=1):
        assert not self.occupied
        self.party = party
        self.set_occupied()


class MapObject:
    map_objects = []
    all_move_units = defaultdict(list)
    all_map_movements = defaultdict(list)

    def __init__(self, map_id, p):
        if not self.all_map_movements:
            MapObject.populate_map_movements()

        self.index = len(self.map_objects)
        self.map_id = map_id
        f = open(TEMPFILE, 'r+b')
        f.seek(p + 0x68)
        terrain_addr = read_multi(f, 4)
        if terrain_addr < 0xb4:
            return
        offset = p + terrain_addr
        f.seek(offset)
        self.width = ord(f.read(1))
        f.seek(offset + 1)
        self.length = ord(f.read(1))
        self.tiles, self.upper = [], []
        for i in xrange(256):
            f.seek(offset + 2 + (i*8))
            self.tiles.append(TileObject(f.read(8)))
        for i in xrange(256, 512):
            f.seek(offset + 2 + (i*8))
            self.upper.append(TileObject(f.read(8)))
        f.close()
        for t, u in zip(self.tiles, self.upper):
            if u.height and not u.bad:
                t.upper = 1
        for unit, x, y in self.map_movements:
            self.set_occupied(x, y)
        self.set_entd_occupied_movers()
        self.set_unreachable_zones()
        self.map_objects.append(self)

    def set_unreachable_zones(self):
        zones = []
        values_grid = self.get_values_grid("bad_regardless")
        for y in xrange(self.length):
            for x in xrange(self.width):
                if values_grid[y][x] == 1:
                    continue
                zone_found = False
                for zone in zones:
                    for (b, a) in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        i, j = x+a, y+b
                        if (i, j) in zone:
                            zone_found = True
                            zone.append((x, y))
                            break
                if not zone_found:
                    zones.append([(x, y)])
        zones = [set(z) for z in zones]
        num_zones = len(zones)
        while True:
            for z1 in list(zones):
                for z2 in list(zones):
                    if z1 is z2:
                        continue
                    if z1 & z2:
                        zones.remove(z1)
                        zones.remove(z2)
                        zones.append(z1 | z2)
                        break
                if len(zones) != num_zones:
                    break
            if len(zones) == num_zones:
                break
            num_zones = len(zones)
        largesize = max([len(z) for z in zones])
        candidates = [z for z in zones if len(z) == largesize]
        chosen = random.choice(candidates)
        for zone in zones:
            if zone == chosen:
                continue
            for (x, y) in zone:
                self.set_unreachable(x, y)
        self.zones = zones

    def set_unreachable(self, x, y):
        index = (y * self.width) + x
        self.tiles[index].set_unreachable()

    def set_occupied(self, x, y, party=False):
        index = (y * self.width) + x
        if party:
            self.tiles[index].set_party()
        else:
            self.tiles[index].set_occupied()

    @property
    def encounter(self):
        es = [e for e in EncounterObject if
              e.event and e.entd and e.grid and e.map_id == self.map_id]
        if es:
            return es[0]
        return None

    @property
    def unused_units(self):
        if not self.encounter:
            return []
        return sorted([u for u in mapunits[self.encounter.entd]
                       if u.graphic == 0 and u.job == 0],
                      key=lambda u2: u2.index)

    @property
    def units(self):
        if not self.encounter:
            return []
        return sorted([u for u in mapunits[self.encounter.entd]
                       if u.graphic > 0], key=lambda u2: u2.index)

    @property
    def nonmoving_units(self):
        units = self.units
        if any([v & 0x80 for v in self.move_units]):
            units = [u for u in units if u.graphic <= 0x7F]
        units = [u for u in units if u.graphic not in self.move_units]
        return units

    @property
    def moving_units(self):
        units = self.units
        return [u for u in units if u not in self.nonmoving_units]

    def set_entd_occupied_movers(self):
        for u in self.moving_units:
            self.set_occupied(u.x, u.y)

    @property
    def map_movements(self):
        return self.all_map_movements[self.map_id]

    @property
    def move_units(self):
        return self.all_move_units[self.map_id]

    @staticmethod
    def populate_map_movements():
        for line in open(MAPMOVESFILE):
            line = line.strip()
            if not line or line[0] == "#":
                continue
            map_id, data = line.split()
            map_id = int(map_id, 0x10)
            unit, x, y = data.split(",")
            unit = int(unit, 0x10)
            MapObject.all_map_movements[map_id].append((unit, int(x), int(y)))
            MapObject.all_move_units[map_id].append(unit)
            MapObject.all_map_movements[map_id] = sorted(set(
                MapObject.all_map_movements[map_id]))
            MapObject.all_move_units[map_id] = sorted(set(
                MapObject.all_move_units[map_id]))

    @staticmethod
    def get_certain_values_map_id(map_id, attribute):
        maps = MapObject.get_by_map_id(map_id)
        width = min([m.width for m in maps])
        length = min([m.length for m in maps])
        grid = []
        for y in range(length):
            grid.append([])
            for x in range(width):
                values = [m.get_tile_value(x, y, attribute) for m in maps]
                values = sorted(set(values))
                if len(values) == 1:
                    grid[y].append(values[0])
                else:
                    grid[y].append(None)
        return grid

    def get_pretty_values_grid(self, attribute):
        tile_values = [getattr(t, attribute) for t in self.tiles]
        maxval = max(tile_values)
        hexify, pad = False, False
        if maxval >= 16:
            hexify = True
            pad = True
        elif maxval >= 10:
            hexify = True
        values_grid = self.get_values_grid(attribute)
        s = ""
        for row in values_grid:
            for value in row:
                if hexify:
                    value = "%x" % value
                if pad:
                    value = "{0:2}".format(value)
                value = str(value)
                s += value + " "
            s = s.strip() + "\n"
        return s.strip()

    def get_values_grid(self, attribute):
        grid = []
        for row in self.tile_grid:
            grid.append([getattr(t, attribute) for t in row])
        return grid

    def get_tile(self, x, y):
        return self.tiles[x + (self.width * y)]

    def get_tile_value(self, x, y, attribute):
        return getattr(self.get_tile(x, y), attribute)

    def get_tile_values(self, attribute):
        return [getattr(t, attribute) for t in self.tiles]

    def tile_count(self, attribute, f=None):
        if f is None:
            f = lambda v: v
        values = self.get_tile_values(attribute)
        values = values[:self.length * self.width]
        return len([v for v in values if f(v)])

    @property
    def tile_count_good(self):
        return self.tile_count("bad_regardless", f=lambda v: v == 0)

    @property
    def tile_grid(self):
        grid = []
        for z in xrange(self.length):
            tiles = self.tiles[z*self.width:(z+1)*self.width]
            grid.append(tiles)
        return grid

    @staticmethod
    def get_by_map_id(map_id):
        return [m for m in MapObject.every if m.map_id == map_id]

    @staticmethod
    def get_map(map_id, index=0):
        return MapObject.get_by_map_id(map_id)[index]

    @staticmethod
    def get_most_good(map_id):
        maps = MapObject.get_by_map_id(map_id)
        maps = sorted(maps, key=lambda m:
                      (m.tile_count_good, -m.index))
        return maps[-1]

    @classproperty
    def every(cls):
        if len(cls.map_objects) > 0:
            return cls.map_objects
        for line in open(MESHESFILE):
            line = line.strip()
            map_id, pointers = line.split()
            map_id = int(map_id)
            pointers = pointers.split(",")
            for p in pointers:
                p = int(p, 0x10)
                MapObject(map_id, p)
        return cls.every


class EncounterObject(TableObject):
    used_music = set([])
    _candidate_maps = None

    @property
    def next_enc(self):
        if self.following != 0x81:
            return None
        if self.next_scene == 0:
            return None
        else:
            return [e for e in EncounterObject
                    if e.scenario == self.next_scene][0]

    @property
    def is_event(self):
        return (0x100 <= self.entd <= 0x1d5
                and (self.event != 0 or self.entd == 0x100))

    @property
    def is_fake_event(self):
        fake = (0x101 <= self.entd <= 0x1d5 and self.event == 0)
        return fake

    @property
    def grids(self):
        return [FormationObject.get(g) for g in [self.grid, self.grid2]
                if g or g == self.grid]

    @property
    def num_characters(self):
        return min(sum([g.num_characters for g in self.grids]), 5)

    @staticmethod
    def get_by_entd(entd):
        candidates = [e for e in EncounterObject.every if e.entd == entd]
        if len(candidates) > 1:
            candidates = [c for c in candidates if c.event]
        if len(candidates) > 1:
            candidates = [c for c in candidates if c.ramza]
        if len(candidates) > 1:
            raise Exception("More than one with that ENTD.")
        return candidates[0]

    @staticmethod
    def get_unused():
        encs = [e for e in EncounterObject.every if
                e.map_id == 0 and e.event == 0 and e.entd == 0
                and e.next_scene == 0 and e.following == 0]
        if not encs:
            return None
        unused = encs[0]
        unused.scenario = max([e.scenario for e in EncounterObject]) + 1
        return unused

    @staticmethod
    def get_replaceable_maps():
        banned = [0x184, 0x185, 0x1c2]
        encs = [e for e in EncounterObject.every if e.event and e.entd
                and not MapObject.get_map(e.map_id).move_units
                and 0x180 <= e.entd <= 0x1d5 and e.entd not in banned]
        return sorted(encs, key=lambda e: e.entd)

    @staticmethod
    def get_candidate_maps():
        if EncounterObject._candidate_maps is not None:
            return EncounterObject._candidate_maps

        maps = [
            1, 4, 8, 9, 11, 14, 15, 18, 20, 21, 23, 24, 26, 37, 38,
            41, 43, 46, 48, 51, 53, 62, 65, 68, 71, 72, 73, 75,
            76, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 104,
            115, 116, 117, 118, 119, 125]
        maps = [MapObject.get_most_good(m) for m in maps]
        EncounterObject._candidate_maps = maps
        return EncounterObject.get_candidate_maps()

    @staticmethod
    def remove_candidate_map(m):
        EncounterObject._candidate_maps.remove(m)

    @property
    def mutated(self):
        if hasattr(self, "_mutated") and self._mutated:
            return True
        return False

    def mutate_map(self):
        candidates = self.get_candidate_maps()
        c = random.choice(candidates)
        self.map_id = c.map_id
        self.remove_candidate_map(c)
        self._mutated = True

    def generate_formations(self, corner=False, numchar_override=None):
        m = MapObject.get_map(self.map_id)
        num_generic_moves = len([u for u in m.move_units if u & 0x80])
        if randint(1, num_generic_moves) > 2:
            return None
        heights = MapObject.get_certain_values_map_id(self.map_id, "height")
        depths = MapObject.get_certain_values_map_id(self.map_id, "depth")
        bads = MapObject.get_certain_values_map_id(self.map_id, "bad")
        occupieds = MapObject.get_certain_values_map_id(self.map_id,
                                                        "occupied")
        length = len(heights)
        width = len(heights[0])
        if length * width == 0:
            return None

        if numchar_override:
            num_characters = numchar_override
        else:
            num_characters = self.num_characters

        if num_characters < 2 or corner or numchar_override:
            num_formations = 1
        else:
            num_formations = random.choice([1, 1, 1, 2])

        # begin generate function
        def gen():
            winwidth = min(5, width)
            winlength = min(5, length)
            placewidth = width - 4
            placelength = length - 4
            halfwidth, halflength = placewidth/2, placelength/2
            if not corner:
                if placewidth == 0:
                    x = 0
                else:
                    x = randint(0, halfwidth) + randint(0, halfwidth)
                    x = (x + halfwidth) % placewidth
                if placelength == 0:
                    y = 0
                else:
                    y = randint(0, halflength) + randint(0, halflength)
                    y = (y + halflength) % placelength
            else:
                x = random.choice([0, placewidth-1])
                y = random.choice([0, placelength-1])
            assert 0 <= x <= placewidth
            assert 0 <= y <= placelength
            lines_deleted = 0
            while True:
                xmargin = min(x, width - (x+winwidth+1))
                ymargin = min(y, length - (y+winlength+1))
                if randint(0, min(xmargin, ymargin)) != 0:
                    return None
                xpoints, ypoints = winwidth, winlength
                if xmargin > ymargin:
                    xpoints *= 2
                elif ymargin > xmargin:
                    ypoints *= 2
                value = randint(0, xpoints + ypoints)
                if value < xpoints:
                    winwidth -= 1
                    if x > halfwidth:
                        x += 1
                else:
                    winlength -= 1
                    if y > halflength:
                        y += 1

                if winwidth == 1 or winlength == 1:
                    break
                if lines_deleted >= 6:
                    break
                if random.choice([True, False, False, False]):
                    break
            height_tolerance = 0
            while random.choice([True, False]):
                height_tolerance += 1
            try:
                winheights = slice_array_2d(heights, x, winwidth, y, winlength)
            except:
                import pdb; pdb.set_trace()
            winbads = slice_array_2d(bads, x, winwidth, y, winlength)
            windepths = slice_array_2d(depths, x, winwidth, y, winlength)
            winoccs = slice_array_2d(occupieds, x, winwidth, y, winlength)
            if [v for row in winoccs for v in row if v == 1]:
                if randint(1, 5) != 5:
                    return None
            heightlist = sorted(set([h for row in winheights for h in row]))
            heightlist = [h for h in heightlist if h is not None]
            if not heightlist:
                return None
            if len(heightlist) > 1:
                heightlist = heightlist[:randint(1, len(heightlist))]
            base_height = random.choice(heightlist)
            if height_tolerance and base_height - height_tolerance <= 0:
                allow_depths = random.choice([True, False])
            else:
                allow_depths = False

            winvalid = []
            for j in range(winlength):
                winvalid.append([])
                for i in range(winwidth):
                    height = winheights[j][i]
                    bad = winbads[j][i]
                    if height is None or bad is None:
                        winvalid[j].append(0)
                        continue
                    valid = 1
                    if bad:
                        valid = 0
                    if not (base_height <= height <=
                            base_height + height_tolerance):
                        depth = windepths[j][i]
                        if depth == 0:
                            valid = 0
                        if height <= base_height - height_tolerance:
                            valid = 0
                        if not allow_depths:
                            valid = 0
                    winvalid[j].append(valid)
            try:
                while not any(winvalid[0]):
                    winvalid = winvalid[1:]
                    y += 1
                    winlength -= 1
                while not any(winvalid[-1]):
                    winvalid = winvalid[:-1]
                    winlength -= 1
                while not any(zip(*winvalid)[0]):
                    winvalid = zip(*zip(*(winvalid))[1:])
                    x += 1
                    winwidth -= 1
                while not any(zip(*winvalid)[-1]):
                    winvalid = zip(*zip(*(winvalid))[:-1])
                    winwidth -= 1
            except IndexError:
                return None
            winvalid = [list(row) for row in winvalid]
            xmargin = min(x, width - (x+winwidth+1))
            ymargin = min(y, length - (y+winlength+1))
            if ((winlength > winwidth and xmargin > ymargin) or
                    (winwidth > winlength and ymargin > xmargin)):
                if randint(1, 10) != 10:
                    return None
            assert 0 <= x <= width - winwidth
            assert 0 <= y <= length - winlength
            if winwidth * winlength <= 2:
                return None
            return x, y, winvalid
        # end generate function

        chars = []
        if num_formations > 1:
            half = num_characters / 2
            first = randint(1, half) + randint(0, half)
            first = min(first, num_characters-1)
            chars.append(first)
            chars.append(num_characters-first)
            chars = sorted(chars, reverse=True)
            assert sum(chars) == num_characters
        else:
            chars = [num_characters]

        saved = None
        for k, subchars in enumerate(chars):
            while True:
                result = gen()
                if result is None:
                    continue
                x, y, window = result
                numvalid = len([v for row in window for v in row if v])
                if (numvalid == subchars and
                        random.choice([True, True, False])):
                    continue
                elif subchars <= 2 and numvalid > 12:
                    continue
                if numvalid >= subchars:
                    if saved is None:
                        saved = (x, y, [list(row) for row in window])
                    else:
                        # collision detection
                        saved_x, saved_y, saved_window = saved
                        if abs(x - saved_x) < 5 and abs(y - saved_y) < 5:
                            continue
                        if (max(abs(x - saved_x), abs(y - saved_y)) == 5 and
                                random.choice([True, True, False])):
                            continue
                    break
            for row in window:
                while len(row) < 5:
                    row.append(0)
            while len(window) < 5:
                window.append([0, 0, 0, 0, 0])

            '''
            if self.entd == 0x193:
                    print MapObject.get_map(self.map_id).get_pretty_values_grid("height")
                    print
                    print "%x %x" % (x, y), "%s/%s" % (subchars, numvalid)
                    for row in window:
                        print " ".join([str(v) for v in row])
                    print
                    import pdb; pdb.set_trace()
            '''

            for j, row in enumerate(window):
                for i, v in enumerate(row):
                    if v:
                        m = MapObject.get_map(self.map_id)
                        m.set_occupied(x+i, y+j, party=True)

            bitmap = 0
            valids = [v for row in zip(*window) for v in row]
            for l, v in enumerate(valids):
                bitmap |= (v << l)
            f = FormationObject.get_unused()
            f.map_number = self.map_id
            f.bitmap = bitmap
            f.x = x + 2  # Center tile! D'oh!
            f.z = y + 2
            f.orientation = 0
            f.pick_correct_orientation()
            f.num_characters = subchars
            if k == 0:
                self.grid = f.id_number
                self.grid2 = 0
            elif k == 1:
                self.grid2 = f.id_number

        if self.grid2 and subchars > 1 and random.choice([True, False]):
            self.grid, self.grid2 = self.grid2, self.grid
        return True

    def randomize_weather(self):
        oldnight, oldweather = self.night, self.weather
        if self.weather <= 4:
            if randint(1, 7) == 7:
                self.night = 1
            else:
                self.night = 0
            if randint(1, 4) == 4:
                self.weather = random.choice([1, 2, 3, 4])
            else:
                self.weather = 0
        if self.entd in FIXED_WEATHER:
            self.weather = oldweather
            self.night = oldnight

    def randomize_music(self, prefer_unused=False, force_battle=False):
        sneaky_events = [0x186, 0x187, 0x188, 0x189, 0x18a, 0x18c, 0x18d,
                         0x18e, 0x196, 0x198, 0x19c, 0x1a2, 0x1a5, 0x1a9,
                         0x1ab, 0x1ad, 0x1b2, 0x1b5, 0x1be, 0x1c3, 0x1c7,
                         0x1ca, 0x1d3, 0x1d5]
        if 0xFC < self.entd < 0x180 or self.entd in sneaky_events:
            if not (force_battle and self.index == 0x12b):
                return
        banned = [0, 17, 18, 19, 20, 21, 22, 23, 24,
                  41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
                  51, 52, 53, 54, 55, 56, 57, 59, 63, 64, 65,
                  69, 70, 72, 73, 74, 75, 79, 98]
        if force_battle:
            banned += (range(25, 39) + range(40, 68) + range(69, 73) +
                       [78, 80] + range(83, 93) + range(93, 97))
            banned.remove(73)
            banned.remove(17)
            banned.remove(18)
            banned.remove(19)
        allowed = [s for s in range(100) if s not in banned]
        temp = [s for s in allowed if s not in self.used_music]
        if not temp:
            self.used_music = set([])
            temp = allowed
        if prefer_unused:
            temp2 = [s for s in temp if 81 <= s <= 96]
            if temp2:
                temp = temp2
        self.music = [m if m in banned else random.choice(temp)
                      for m in self.music]
        self.used_music |= set(self.music)


class FormationObject(TableObject):
    @staticmethod
    def get_unused():
        return [f for f in FormationObject.every if f.bitmap == 0
                and f.index != 0][-1]

    @property
    def pretty_facing(self):
        value = self.rotation + self.facing
        value = value % 4
        return {0: "west", 1: "south", 2: "east", 3: "north"}[value]

    @property
    def facing(self):
        # values with 0 rotation
        # rotate counterclockwise with rotation
        # 0: west
        # 1: south
        # 2: east
        # 3: north
        return self.orientation >> 4

    @property
    def rotation(self):
        # North is greater Z, East is greater X
        # first == least significant
        # 0: first bit in SW corner
        # 1: first bit in SE corner
        # 2: first bit in NE corner
        # 3: first bit in NW corner
        return self.orientation & 0xf

    def pick_correct_orientation(self):
        margin_x = min(self.x, self.my_map.width - (self.x + 1))
        margin_z = min(self.z, self.my_map.length - (self.z + 1))
        if (margin_x > margin_z or
                (margin_x == margin_z and random.choice([True, False]))):
            if self.z < (self.my_map.length / 2):
                # face north
                value = 3
            else:
                # south
                value = 1
        else:
            if self.x < (self.my_map.width / 2):
                # east
                value = 2
            else:
                # west
                value = 0
        self.orientation = value

    @property
    def my_map(self):
        return MapObject.get_map(self.map_number)

    def mutate(self):
        if self.num_characters == 0 or self.bitmap == 0:
            return
        if self.index == 0x100:
            # gariland formation
            return
        if boostd["difficulty_factor"] > 1.0:
            dings = 1.0 / (boostd["difficulty_factor"] ** 4)
            while self.num_characters > 1:
                prob = self.num_characters ** 4
                prob = prob * (0.5 ** dings)
                if randint(1, 1875) <= prob:
                    self.num_characters -= 1
                    dings += 1
                    continue
                break

            while True:
                bits = bin(self.bitmap).count("1")
                if bits <= self.num_characters:
                    break
                prob = (bits - self.num_characters) ** 2
                if randint(1, 20) <= prob:
                    while bin(self.bitmap).count("1") >= bits:
                        mask = 1 << randint(0, 31)
                        if self.bitmap & mask:
                            self.bitmap ^= mask
                else:
                    break


class MonsterSkillsObject(TableObject):
    def get_actual_attacks(self):
        actuals = []
        for i, attack in enumerate(self.attackbytes):
            highbit = (self.highbits >> (7-i)) & 1
            if highbit:
                attack |= 0x100
            actuals.append(attack)
        return actuals

    def read_data(self, filename=None, pointer=None):
        super(MonsterSkillsObject, self).read_data(filename, pointer=pointer)
        self.attacks = self.get_actual_attacks()

    def write_data(self, filename=None, pointer=None):
        self.attackbytes = [a & 0xFF for a in self.attacks]
        self.highbits = 0
        for i, attack in enumerate(self.attacks):
            if attack & 0x100:
                self.highbits |= (1 << (7-i))
        super(MonsterSkillsObject, self).write_data(filename, pointer=pointer)

    def mutate(self):
        if randint(1, 12) == 12:
            candidates = get_ranked_skills()
        else:
            candidates = get_ranked_skills("monster")

        new_attacks = []
        for action in self.attacks:
            if action == 0:
                if random.choice([True, False]):
                    continue
                else:
                    action = random.choice(self.attacks)
                if action == 0:
                    continue
            elif random.choice([True, False]):
                new_attacks.append(action)
                continue
            index = candidates.index(get_ability(action))
            index = mutate_normal(index, maximum=len(candidates)-1)
            new_attacks.append(candidates[index].index)

        new_attacks, beastmaster = new_attacks[:-1], new_attacks[-1]
        new_attacks = [n for n in new_attacks if n != beastmaster]
        if len(new_attacks) == 0:
            new_attacks = [beastmaster]
            beastmaster = random.choice(candidates).index
        new_attacks = sorted(set(new_attacks))
        assert len(new_attacks) >= 1
        assert 0 not in new_attacks
        while len(new_attacks) < 3:
            new_attacks.append(0)
        self.attacks = new_attacks + [beastmaster]


class MoveFindObject(TableObject):
    @property
    def x(self):
        return self.coordinates >> 4

    @property
    def y(self):
        return self.coordinates & 0xF

    @property
    def map_id(self):
        return self.index / 4

    @property
    def my_map(self):
        return MapObject.get_map(self.map_id)

    def set_coordinates(self, x, y):
        self.coordinates = (x << 4) | y

    def mutate(self):
        special = random.choice([True, False])
        if special:
            try:
                length = self.my_map.length
                width = self.my_map.width
            except IndexError:
                return
            while True:
                x = randint(0, width-1)
                y = randint(0, length-1)
                try:
                    bad = (MapObject.get_certain_values_map_id(
                           self.map_id, "bad")[y][x])
                    lava = (MapObject.get_certain_values_map_id(
                            self.map_id, "terrain_type")[y][x])
                    lava = (lava == 0x12)
                    deep = (MapObject.get_certain_values_map_id(
                            self.map_id, "depth")[y][x])
                    deep = (deep >= 3)
                except IndexError:
                    continue
                if bad or lava or deep:
                    continue
                break
            self.set_coordinates(x, y)

        if self.common != 0:
            if special:
                self.common = random.choice(ItemObject.every).index
            else:
                self.common = get_similar_item(
                    self.common, boost_factor=boostd["common_item"]).index

        if self.rare != 0:
            if special and random.choice([True, False]):
                self.rare = self.common
            else:
                common = ItemObject.get(self.common)
                candidates = [i for i in ItemObject.every
                              if i.rank >= common.rank]
                self.rare = random.choice(candidates).index

        if self.common or self.rare:
            trapvalue = random.choice([True, False, False])
            self.set_bit("disable_trap", not trapvalue)
            if trapvalue:
                self.set_bit("always_trap", randint(1, 5) == 5)
                traptypes = ["sleeping_gas", "steel_needle",
                             "deathtrap", "degenerator"]
                for traptype in traptypes:
                    self.set_bit(traptype, False)
                self.set_bit(random.choice(traptypes), True)
            if randint(1, 10) == 10:
                self.common, self.rare = self.rare, self.common


class PoachObject(TableObject):
    donerare = set([])

    def mutate(self):
        self.common = get_similar_item(
            self.common, boost_factor=boostd["common_item"]).index
        common = ItemObject.get(self.common)
        candidates = [i for i in ItemObject.every if i.rank > common.rank]
        temp = [i for i in candidates if i.index not in self.donerare]
        if temp:
            candidates = temp
        self.rare = random.choice(candidates).index
        self.donerare.add(self.rare)


# Ry Edit: Objects for Weapon, Shield, Armor, Accessory, Chemist Item, Inflict Status, and Item Attribute Data
class WeaponObject(TableObject):
    def mutate(self):
        for attr in ["range", "weapon_power", "evade"]:
            value = getattr(self, attr)
            if random.choice([True, False]) and 0 <= value <= 0xFD:
                newvalue = mutate_normal(value, minimum=0, maximum=0xFD)
                if attr == "range" and value > 0 and newvalue == 0:
                    continue
                setattr(self, attr, newvalue)

        #if random.choice([True, False]):
        #    self.element = mutate_bits(self.element)
        value = self.inflict_status
        if self.formula == 1 and value == 0 and randint(1, 5) == 1:
            # 20% chance to turn a non-status Formula 1 move into Formula 2
            self.formula = 2
            self.inflict_status = 0

        if self.formula == 2:
            # Formula 2 calls the "inflict status" value as a spell to cast 25% of the time
            if (value == 0) or (randint(1, 10) == 1):
                # 10% chance for pre-existing spell casts to be randomized
                # Value is capped at FF internally, so no abilities past Holy Bracelet
                newvalue = randint(1, 0xFF)
                if newvalue in [0x28, 0x2D, 0xB8, 0xDB, 0xDC]:
                    # Empty abilities
                    newvalue = randint(1, 0x1F)
                self.inflict_status = newvalue

    def mutate_status(self):
        if (not (self.formula == 2)) and randint(1, 10) == 1:
            value = self.inflict_status
            if value > 0 and randint(1, 10) != 1:
                # 1% Chance for a pre-existing Inflict Status to be randomized; 10% otherwise
                return
            newvalue = randint(0, 0x79)
            if newvalue == 0x60:
                # Banning Crystal (since it's more likely to appear on weapons)
                return
            self.inflict_status = newvalue


class ShieldObject(TableObject):
    def mutate(self):
        for attr in ["physical_evade", "magic_evade"]:
            value = getattr(self, attr)
            if random.choice([True, False]) and 0 <= value <= 0x50:
                    newvalue = mutate_normal(value, minimum=0, maximum=0x50) # Max 80
                    setattr(self, attr, newvalue)


class ArmorObject(TableObject):
    def mutate(self):
        for attr in ["hp_bonus", "mp_bonus"]:
            value = getattr(self, attr)
            if random.choice([True, False]) and 0 <= value <= 0xFD:
                    newvalue = mutate_normal(value, minimum=0, maximum=0xFD)
                    setattr(self, attr, newvalue)


class AccessoryObject(TableObject):
    def mutate(self):
        for attr in ["physical_evade", "magic_evade"]:
            value = getattr(self, attr)
            if random.choice([True, False]) and 0 <= value <= 0x3C:
                    newvalue = mutate_normal(value, minimum=0, maximum=0x3C) # Max 60
                    setattr(self, attr, newvalue)


class ChemistItemObject(TableObject):
    def mutate(self):
        value = self.zval
        if 1 <= value <= 0xFD:
            newvalue = mutate_normal(value, minimum=1, maximum=0xFD)
            self.zval = newvalue


class InflictStatusObject(TableObject):
    def randomize_empty(self):
        if (0x1D <= self.index <= 0x1F) or  (0x7A <= self.index <= 0x7F):
            toinflict = 0
            while True:
                bit = (1 << randint(0, 39))
                if not bit & VALID_START_STATUSES:
                    continue
                toinflict |= bit
                if (toinflict and
                        randint(1, 2**(bin(toinflict).count("1"))) != 1):
                    break
            self.statuses_to_inflict = toinflict
            if not (self.statuses_to_inflict == 0x0000000000):
                choice = randint(1, 9)
                if choice <= 3: # 33%
                    self.set_bit("random", True)
                elif choice <= 6: # 33%
                    self.set_bit("separate", True)
                elif choice <= 8: # 22%
                    self.set_bit("cancel", True)
                else: # 11%
                    self.set_bit("all_or_nothing", True)


class ItemAttributesObject(TableObject):
    def mutate(self):
        if not self.index:
            return
        if self.index <= 49:
            for attr in ["pa", "ma", "speed", "move", "jump"]:
                value = getattr(self, attr)
                if random.choice([True, False]) and 0 <= value <= 0xFD:
                        newvalue = mutate_normal(value, minimum=0, maximum=0xFD)
                        setattr(self, attr, newvalue)

            '''
            # Mutating status/elements on items seems like an all-around bad idea until tooltips are implemented
            if randint(1, 3) == 1:
              immune = mutate_bits(self.status_immune, 40, odds_multiplier=4.0)
              changed = immune ^ self.status_immune
              for i in range(40):
                  mask = (1 << i)
                  if mask & changed:
                      if mask & BENEFICIAL_STATUSES or randint(1, 50) == 50:
                          self.status_immune ^= mask
                      else:
                          self.status_immune |= mask

              not_innate = ((2**40)-1) ^ self.status_innate
              not_start = ((2**40)-1) ^ self.status_start
              self.status_immune &= not_innate
              self.status_immune &= not_start

              vulnerable = ((2**40)-1) ^ self.status_immune
              innate = mutate_bits(self.status_innate, 40, odds_multiplier=4.0)
              innate &= vulnerable
              innate &= VALID_INNATE_STATUSES
              not_innate2 = ((2**40)-1) ^ innate
              start = mutate_bits(self.status_start, 40, odds_multiplier=4.0)
              start &= vulnerable
              start &= (not_innate & not_innate2)
              start &= VALID_START_STATUSES
              self.status_innate |= innate
              self.status_start |= start

            if randint(1, 2) == 1:
                self.elem_null = mutate_bits(self.elem_null)
                vulnerable = 0xFF ^ self.elem_null
                self.elem_abs = mutate_bits(self.elem_abs) & vulnerable
                self.elem_strengthen = mutate_bits(self.elem_strengthen) & vulnerable
                self.elem_halve = mutate_bits(self.elem_halve) & vulnerable
                vulnerable = 0xFF ^ (self.elem_null | self.elem_strengthen | self.elem_halve)
                self.elem_weak = mutate_bits(self.elem_weak) & vulnerable
            '''
        elif self.index == 0x4A:
            # Static Item Attributes to be used to "mutate" weapons that don't have Attributes normally
            self.pa = 1
        elif self.index == 0x4B:
            self.ma = 1
        elif self.index == 0x4C:
            self.speed = 1
        elif self.index == 0x4D:
            self.move = 1
        elif self.index == 0x4E:
            self.jump = 1


class AbilityAttributesObject(TableObject):
    def mutate(self):
        for attr in ["ct", "mp"]:
            value = getattr(self, attr)
            if 1 <= value <= 0xFD:
                value = mutate_normal(value)
                setattr(self, attr, value)

        if 1 <= self.xval <= 0xFD:
            self.xval = mutate_normal(self.xval, minimum=1, maximum=0xFD)

        if 1 <= self.yval <= 0xFD:
            self.yval = mutate_normal(self.yval, minimum=1, maximum=0xFD)

        for attr in ["range", "effect", "vertical"]:
            value = getattr(self, attr)
            if random.choice([True, False]) and 0 <= value <= 0xFD:
                    newvalue = mutate_normal(value, minimum=0, maximum=0xFD)
                    if attr == "range" and value > 0 and newvalue == 0:
                        continue
                    setattr(self, attr, newvalue)

    def mutate_status(self):
        # Ry Edit: Ability Inflict Status randomizer
        if self.index == 0x1D:
            # Excluding Frog, because I feel like there's some hardcoding for the AI's usage of it
            return

        formula = self.formula
        value = self.inflict_status
        if (value > 0) or (formula in STATUS_FORMULAS):
            if randint(1, 5) == 1:
                if value > 0 and randint(1, 10) != 1:
                    # 2% Chance for a pre-existing Inflict Status to be randomized; 20% otherwise
                    return
                newvalue = randint(1, 0x7F)
                if newvalue == 0x60:
                    # Banning Crystal if it'd hit more than 1 unit
                    effectarea = self.effect
                    if effectarea > 0 or self.get_bit("math_skill") or self.get_bit("3_directions"):
                        return
                    # Add code here to ensure that all Ramza classes and Rafa are immune to Crystal?

                self.inflict_status = newvalue
                ability = get_ability(self.index)
                if ability.get_bit("add_status") or ability.get_bit("cancel_status"):
                    # Correcting the AI flags if the ability normally does status
                    inflictstatus = InflictStatusObject.get(newvalue)
                    if inflictstatus.get_bit("cancel"):
                        ability.set_bit("add_status", False)
                        ability.set_bit("cancel_status", True)
                    elif (inflictstatus.get_bit("separate") or
                            inflictstatus.get_bit("random") or
                            inflictstatus.get_bit("all_or_nothing")):
                        ability.set_bit("add_status", True)
                        ability.set_bit("cancel_status", False)

            '''
            # Alternate version that bans only status-focused spells from being randomized (untested)
            ability = get_ability(self.index)
            if value == 0 or not (ability.get_bit("add_status") or ability.get_bit("cancel_status")):
                if randint(1, 10) <= 3:
                    newvalue = randint(1, 0x7F)
                    if newvalue == 0x60:
                        effectarea = self.effect
                        if effectarea > 0 or self.get_bit("math_skill") or self.get_bit("3_directions"):
                            return
                    self.inflict_status = newvalue
            '''


class AbilityObject(TableObject):
    @property
    def ability_type(self):
        return self.misc_type & 0xF

    @property
    def is_reaction(self):
        return self.ability_type == 7

    @property
    def is_support(self):
        return self.ability_type == 8

    @property
    def is_movement(self):
        return self.ability_type == 9


class ItemObject(TableObject):
    @property
    def rank(self):
        if self.index == 0:
            return -1

        rank = self.price
        if self.priceless:
            rank += 65000
            rank += (self.enemy_level * 100)
        return rank

    @property
    def priceless(self):
        if self.price <= 10:
            return True
        elif self.index in [0x6A, 0x8F]:
            return True

    def mutate_shop(self):
        self.price = mutate_normal(self.price, maximum=65000)
        self.price = int(round(self.price, -1))
        if self.price > 500:
            self.price = int(round(self.price, -2))
        if 1 <= self.time_available <= 16:
            self.time_available = mutate_normal(self.time_available,
                                                maximum=16)

        if self.get_bit("rare") and randint(1, 4) != 4:
            if self.index in BANNED_ITEMS and randint(1, 3) != 3:
                pass
            else:
                if self.enemy_level <= 5:
                    self.enemy_level = 50
                self.set_bit("rare", False)

        if self.enemy_level >= 1:
            self.enemy_level = int(round(
                self.enemy_level / boostd["equipment"]))
            self.enemy_level = mutate_normal(self.enemy_level, minimum=1,
                                             maximum=99)

    def mutate_attributes(self):
        # Ry Edit: Item Attribute Randomizer
        if self.index > 0 and self.attributes == 0 and randint(1, 10) == 1:
            newvalue = randint(0x4A, 0x4E)
            # Only selects from predefined single-stat Item Attributes
            self.attributes = newvalue


class SkillsetObject(TableObject):
    @classproperty
    def math_menuable_skills(self):
        math_skills = set([])
        for skillset in MATH_SKILLSETS:
            skillset = SkillsetObject.get(skillset)
            for action in skillset.actions:
                math_skills.add(action)
        return sorted(math_skills)

    @property
    def is_generic(self):
        return 5 <= self.index <= 0x18

    @property
    def num_free_actions(self):
        return len([a for a in self.actions if get_ability(a).jp_cost == 0])

    @property
    def num_actions(self):
        return len([a for a in self.actions if a > 0])

    @property
    def num_rsms(self):
        return len([a for a in self.rsms if a > 0])

    @property
    def has_learnable_actions(self):
        for action in self.actions:
            if get_ability(action).jp_cost > 0:
                return True
        else:
            return False

    @property
    def has_learnable_rsms(self):
        for action in self.rsms:
            if get_ability(action).jp_cost > 0:
                return True
        else:
            return False

    @property
    def has_swordskills(self):
        for action in self.actions:
            if not AbilityAttributesObject.has(action):
                continue
            aa = AbilityAttributesObject.get(action)
            if aa.get_bit("require_sword"):
                return True
        return False

    @property
    def has_limitskills(self):
        for action in self.actions:
            if not AbilityAttributesObject.has(action):
                continue
            aa = AbilityAttributesObject.get(action)
            if aa.get_bit("require_materia_blade"):
                return True
        return False

    @property
    def not_just_swordskills(self):
        for action in self.actions:
            if not AbilityAttributesObject.has(action):
                continue
            aa = AbilityAttributesObject.get(action)
            if not (aa.get_bit("require_sword")
                    or aa.get_bit("require_materia_blade")):
                return True
        return False

    @property
    def no_randoms(self):
        for action in self.actions:
            if not AbilityAttributesObject.has(action):
                continue
            aa = AbilityAttributesObject.get(action)
            if aa.get_bit("random_hits"):
                return False
        return True

    def get_actual_actions(self):
        actuals = []
        actionbits = (self.actionbits1 << 8) | self.actionbits2
        for i, action in enumerate(self.actionbytes):
            highbit = (actionbits >> (15-i)) & 1
            if highbit:
                action |= 0x100
            actuals.append(action)
        return actuals

    def get_actual_rsms(self):
        actuals = []
        for i, rsm in enumerate(self.rsmbytes):
            highbit = (self.rsmbits >> (7-i)) & 1
            if highbit:
                rsm |= 0x100
            actuals.append(rsm)
        return actuals

    def read_data(self, filename=None, pointer=None):
        super(SkillsetObject, self).read_data(filename, pointer=pointer)
        self.actions = self.get_actual_actions()
        self.rsms = self.get_actual_rsms()
        self.actions = [a for a in self.actions if a > 0]
        self.rsms = [a for a in self.rsms if a > 0]

    def write_data(self, filename=None, pointer=None):
        actions, rsms = list(self.actions), list(self.rsms)
        while len(actions) < 16:
            actions.append(0)
        while len(rsms) < 6:
            rsms.append(0)
        self.actionbytes = [a & 0xFF for a in actions]
        self.rsmbytes = [a & 0xFF for a in rsms]
        assert len(self.actionbytes) == 16
        assert len(self.rsmbytes) == 6
        actionbits, self.rsmbits = 0, 0
        for (i, a) in enumerate(actions):
            if a & 0x100:
                actionbits |= (1 << (15-i))
        self.actionbits1 = actionbits >> 8
        self.actionbits2 = actionbits & 0xFF
        for (i, a) in enumerate(rsms):
            if a & 0x100:
                self.rsmbits |= (1 << (7-i))
        super(SkillsetObject, self).write_data(filename, pointer=pointer)

    def mutate_abilities(self):
        if self.index in BANNED_ANYTHING:
            return

        if self.index not in BANNED_SKILLSET_SHUFFLE:
            candidates = [a for a in get_abilities() if a.ability_type == 1]
            for i, a in enumerate(self.actions):
                if get_ability(a).ability_type == 1:
                    if randint(1, 100) == 100:
                        a = random.choice(candidates)
                        if a.jp_cost == 0:
                            a.jp_cost = 100 + randint(0, 700) + randint(0, 700)
                            a.jp_cost = int(round(a.jp_cost*2, -2) / 2)
                        self.actions[i] = a.index
        for a in self.actions:
            assert a not in BANNED_SKILLS

        candidates = [a for a in get_abilities() if 7 <= a.ability_type <= 9]
        for i, a in enumerate(self.rsms):
            if randint(1, 100) == 100:
                a = random.choice(candidates)
                if a.jp_cost == 0:
                    a.jp_cost = 100 + randint(0, 700) + randint(0, 700)
                    a.jp_cost = int(round(a.jp_cost*2, -2) / 2)
                self.rsms[i] = a.index


class JobObject(TableObject):
    def get_most_common(self, attribute):
        units = [u for u in UnitObject
                 if u.job == self.index and u.map_id <= 0x1d5]
        if not units:
            return None
        attr_count = Counter([getattr(u, attribute) for u in units])
        maxval = max(attr_count.values())
        choices = sorted([k for (k, v) in attr_count.items() if v == maxval])
        if choices:
            return random.choice(choices)
        return None

    @property
    def jobreq(self):
        return JobReqObject.get(self.index)

    @property
    def guaranteed_female(self):
        units = [u for u in UnitObject.every
                 if u.job == self.index
                 and 0x180 <= u.map_id <= 0x1d5]
        if not units:
            return False
        if (any([u.get_bit("female") for u in units])
                and not any([u.get_bit("male") for u in units])):
            return True
        return False

    @property
    def crippled(self):
        status = self.innate_status | self.start_status
        bad_start = 0xFFFFFFFFFF ^ VALID_START_STATUSES
        return bool(status & bad_start)

    @property
    def can_invite(self):
        return not bool(self.immune_status & 0x4000)

    @property
    def is_generic(self):
        return 0x4A <= self.index <= 0x5D

    @property
    def generic_rank(self):
        assert self.index in range(0x4A, 0x5E)
        generics = [j for j in JobObject.every if j.is_generic]
        ranked = sorted(generics, key=lambda j: (
            j.jobreq.required_unlock_jp, j.index))
        index = ranked.index(self)
        rank = float(index) / (len(ranked) - 1)
        assert 0 <= rank <= 1
        return rank

    @property
    def is_monster_job(self):
        return self.index >= 0x5E and self.index != 0x97

    @property
    def is_lucavi(self):
        return self.index in LUCAVI_JOBS

    @property
    def is_altima(self):
        return self.index in [0x41, 0x49]

    @property
    def innates(self):
        innate_attrs = ["innate1", "innate2", "innate3", "innate4"]
        innates = [getattr(self, attr) for attr in innate_attrs]
        return innates

    def set_all_units(self, attr, value):
        units = [u for u in UnitObject if u.job == self.index]
        for u in units:
            setattr(u, attr, value)

    def get_appropriate_boost(self):
        if self.index in [1, 2, 3, 0xD]:
            return 1.0

        if self.is_lucavi:
            boost = boostd["lucavi_stat"]
        else:
            boost = boostd["level_stat"]
        if self.index in range(0x4A, 0x5E):
            average_level = (self.generic_rank * 50) - 25
        else:
            units = [u for u in get_units() if u.job == self.index
                     and u.get_bit("enemy_team") and not u.level_normalized
                     and 0x180 <= u.map_id <= 0x1D5]
            if not units:
                return boostd["default_stat"]
            units = sorted(units, key=lambda u: u.level)
            units = units[-2:]
            average_level = sum([u.level for u in units]) / float(len(units))
        boost = (1.0 + (average_level / 100.0)) ** boost
        return boost

    def mutate_stats(self, boost_factor=None):
        if boost_factor is None:
            boost_factor = self.get_appropriate_boost()
        for attr in ["hpgrowth", "hpmult", "mpgrowth", "mpmult", "spdgrowth",
                     "spdmult", "pagrowth", "pamult", "magrowth", "mamult",
                     "move", "jump", "evade"]:
            value = getattr(self, attr)
            if "growth" in attr or "mult" in attr:
                attrfactor = boost_factor ** 0.5
            else:
                attrfactor = boost_factor
            if "growth" in attr:
                newvalue = value / attrfactor
            else:
                newvalue = value * attrfactor
            newvalue = max(1, min(newvalue, 0xFD))
            if 1 <= newvalue <= 0xFD:
                newvalue = mutate_normal(newvalue, minimum=1, maximum=0xFD)
                if self.is_lucavi and newvalue > value and "growth" in attr:
                    newvalue = value - abs(value - newvalue)
                elif (self.is_lucavi and newvalue < value
                        and "growth" not in attr):
                    newvalue = value + abs(value - newvalue)
                setattr(self, attr, newvalue)

        return True

    def mutate_innate(self):
        self.equips = mutate_bits(self.equips, 32, odds_multiplier=4.0)

        if random.choice([True, False]):
            self.nullify_elem = mutate_bits(self.nullify_elem)
            vulnerable = 0xFF ^ self.nullify_elem
            self.absorb_elem = mutate_bits(self.absorb_elem) & vulnerable
            self.resist_elem = mutate_bits(self.resist_elem) & vulnerable
            vulnerable = 0xFF ^ (self.nullify_elem | self.resist_elem)
            self.weak_elem = mutate_bits(self.weak_elem) & vulnerable

        if self.index in [0x4A]:
            return True

        self.mutate_statuses()
        if self.is_lucavi:
            self.unset_positive_immunities()
            if random.choice([True, False]):
                self.immune_status |= FAITH_STATUS
            if random.choice([True, False]):
                self.immune_status |= INNOCENT_STATUS
            if random.choice([True, False]):
                self.mutate_statuses()
            if randint(1, 30) != 30:
                self.unset_negative_statuses()

        if not self.is_lucavi:
            innate_cands = [a for a in get_abilities()
                            if a.ability_type in [7, 8, 9]]
            innate_cands = sorted(innate_cands, key=lambda a: a.jp_cost)
            innate_attrs = ["innate1", "innate2", "innate3", "innate4"]
            innates = []
            for attr in innate_attrs:
                value = getattr(self, attr)
                chance = randint(1, 20)
                if chance == 20 or (self.is_monster_job and chance > 10):
                    index = None
                    if value:
                        old_inn = AbilityObject.get(value)
                        assert old_inn in innate_cands
                        attr_cands = [a.index for a in innate_cands if
                                      a.ability_type == old_inn.ability_type]
                        index = attr_cands.index(value)
                    else:
                        attr_cands = [a.index for a in innate_cands
                                      if a.is_support]

                    if not value and randint(1, 2) == 2:
                        attr_cands = [a.index for a in innate_cands
                                      if a.is_support]
                        index = len(attr_cands)/2

                    if attr_cands and index is not None:
                        index = mutate_normal(index, maximum=len(attr_cands)-1)
                        value = attr_cands[index]

                innates.append(value)
            innates = reversed(sorted(innates))
            for attr, innate in zip(innate_attrs, innates):
                setattr(self, attr, innate)

        if self.is_lucavi:
            innate_attrs = ["innate1", "innate2", "innate3", "innate4"]
            innates = [getattr(self, attr) for attr in innate_attrs]
            innates = [AbilityObject.get(i) for i in innates if i > 0]
            innate_cands = [AbilityObject.get(i) for i in LUCAVI_INNATES]
            innate_cands += innates
            lucavi_supports = [i for i in innate_cands if i.is_support
                               and not i.index == 0x1E2]
            lucavi_reactions = [i for i in innate_cands if i.is_reaction]
            lucavi_movements = [i for i in innate_cands if i.is_movement]
            num_reactions = 1 + randint(0, 1) + randint(0, 1)
            num_supports = 6 - num_reactions
            while True:
                reactions = random.sample(lucavi_reactions, num_reactions)
                reactions = [i.index for i in reactions]
                if (0x1bd not in reactions and
                        set(reactions) & set(MP_RESTORE_INNATES)):
                    continue
                if len(set(reactions)) == num_reactions:
                    break
            while True:
                supports = random.sample(lucavi_supports, num_supports)
                supports = [i.index for i in supports]
                if len(set(supports)) == num_supports:
                    break
            if 0x1E3 not in supports and 0x1E2 not in supports:
                supports[-1] = 0x1E2
            abilities = reactions + sorted(supports)
            assert len(set(abilities)) == len(abilities) == 6
            for attr, ability in zip(innate_attrs, abilities):
                setattr(self, attr, ability)
            self.set_all_units("reaction", abilities[4])
            self.set_all_units("support", abilities[5])
            if self.is_altima:
                self.set_all_units("movement", 0x1F3)
            else:
                if 0x1bd not in reactions:
                    lucavi_movements = [i for i in lucavi_movements
                                        if i.index not in MP_RESTORE_INNATES]
                movement = random.choice(lucavi_movements).index
                self.set_all_units("movement", movement)

        return True

    def mutate_statuses(self):
        immune = mutate_bits(self.immune_status, 40, odds_multiplier=4.0)
        changed = immune ^ self.immune_status
        for i in range(40):
            mask = (1 << i)
            if mask & changed:
                if mask & BENEFICIAL_STATUSES or randint(1, 50) == 50:
                    self.immune_status ^= mask
                else:
                    self.immune_status |= mask
        not_innate = ((2**40)-1) ^ self.innate_status
        not_start = ((2**40)-1) ^ self.start_status
        self.immune_status &= not_innate
        self.immune_status &= not_start

        vulnerable = ((2**40)-1) ^ self.immune_status
        innate = mutate_bits(self.innate_status, 40, odds_multiplier=4.0)
        innate &= vulnerable
        innate &= VALID_INNATE_STATUSES
        not_innate2 = ((2**40)-1) ^ innate
        start = mutate_bits(self.start_status, 40, odds_multiplier=4.0)
        start &= vulnerable
        start &= (not_innate & not_innate2)
        start &= VALID_START_STATUSES
        if (self.index in range(0x4A, 0x5E) and innate & RERAISE_STATUS
                and randint(1, 100) != 100):
            innate ^= RERAISE_STATUS
            start |= RERAISE_STATUS
        self.innate_status |= innate
        self.start_status |= start

    def unset_positive_immunities(self):
        self.immune_status &= (((2**40)-1) ^ BENEFICIAL_STATUSES)

    def unset_negative_statuses(self):
        self.innate_status &= BENEFICIAL_STATUSES
        self.start_status &= BENEFICIAL_STATUSES


class UnitObject(TableObject):
    @property
    def map_id(self):
        return self.index >> 4

    @property
    def has_special_graphic(self):
        return self.graphic not in [0x80, 0x81, 0x82]

    @property
    def has_monster_job(self):
        return self.job >= 0x5E and self.job != 0x97

    @property
    def monster_portrait(self):
        job = JobObject.get(self.job)
        return job.monster_portrait

    @property
    def is_lucavi(self):
        return self.job in LUCAVI_JOBS

    @property
    def is_altima(self):
        return self.job in [0x41, 0x49]

    @property
    def has_swordskills(self):
        job = get_job(self.job)
        ss = get_skillset(job.skillset)
        ss2 = get_skillset(self.secondary)
        for s in [ss, ss2]:
            if s is None:
                continue
            if s.has_swordskills:
                return True
        return False

    @property
    def has_limitskills(self):
        job = get_job(self.job)
        ss = get_skillset(job.skillset)
        ss2 = get_skillset(self.secondary)
        for s in [ss, ss2]:
            if s is None:
                continue
            if s.has_limitskills:
                return True
        return False

    def fix_facing(self, m):
        # 0: south, 1: west, 2: north, 3: east
        dirdict = {
            "west": self.x, "south": self.y,
            "east": m.width - self.x, "north": m.length - self.y}
        facedict = {
            "west": 3, "south": 2, "east": 1, "north": 0}
        lowest = min(dirdict.values())
        candidates = sorted([v for (k, v) in facedict.items()
                             if dirdict[k] == lowest])
        chosen = random.choice(candidates)
        self.facing &= 0xFC
        self.facing |= chosen

    def has_similar_monster_graphic(self, other):
        if not (self.graphic == 0x82 and other.graphic == 0x82):
            return False

        if (get_job(self.job).monster_graphic
                == get_job(other.job).monster_graphic):
            return True
        else:
            return False

    @property
    def named(self):
        return bool(self.name != 0xFF)

    @property
    def level_normalized(self):
        return self.level >= 100 or self.level == 0

    def normalize_level(self, boost=None):
        if boost is None:
            self.level = 0xFE
        else:
            self.level = 100 + randint(0, boost) + randint(0, boost)
            self.level = max(100, min(self.level, 199))

    def set_backup_jp_total(self):
        value = self.jp_total
        if value < JOBLEVEL_JP[0]:
            value = random.choice([value, JOBLEVEL_JP[0]])
        self.backup_jp_total = value

    @property
    def jp_total(self):
        if hasattr(self, "backup_jp_total"):
            return self.backup_jp_total

        if self.job in jobreq_indexdict:
            base_job = jobreq_indexdict[self.job]
        else:
            if (self.unlocked == 0 and self.unlocked_level == 0
                    and not self.level_normalized):
                total = mutate_normal(175 * self.level, maximum=500000)
                return total
            base_job = jobreq_indexdict[0x4a]
        unlocked_job = jobreq_indexdict[self.unlocked + 0x4a]

        joblevels = []
        for name in JOBNAMES:
            value = max(getattr(base_job, name), getattr(unlocked_job, name))
            if name == unlocked_job.name:
                value = max(value, self.unlocked_level)
            if value:
                joblevels.append(value)
        total = calculate_jp_total(joblevels)

        return total

    def mutate_trophy(self):
        if self.gil > 0:
            self.gil = mutate_normal(self.gil, maximum=65000)
            self.gil = int(round(self.gil, -2))
        if self.trophy:
            self.trophy = get_similar_item(
                self.trophy, boost_factor=boostd["trophy"]).index

    def mutate_secondary(self, base_job=None, jp_remaining=None,
                         boost_factor=None):
        if self.get_bit("load_formation"):
            return

        if boost_factor is None:
            boost_factor = boostd["jp"]
        if base_job is None:
            job = self.job
            if job in jobreq_indexdict:
                base_job = jobreq_indexdict[job]
            else:
                base_job = None

        if jp_remaining is None:
            jp_remaining = self.jp_total
            jp_remaining = randint(jp_remaining,
                                   int(jp_remaining * boost_factor))

        jobs = jobreq_namedict.values()
        jobs = [j for j in jobs if j.required_unlock_jp <= jp_remaining]
        jobs = sorted(jobs, key=lambda j: j.required_unlock_jp)
        goal_length = (len(jobs) / 2) + 1
        while len(jobs) > goal_length:
            if randint(1, len(jobs)) == 1:
                break
            else:
                jobs = jobs[1:]

        if base_job is not None:
            if (randint(1, 20) != 20 and base_job.otherindex > 0):
                base_name = base_job.name
                tempjobs = [j for j in jobs if getattr(j, base_name) > 0
                            or j == base_job]
                if tempjobs:
                    jobs = tempjobs
            random.shuffle(jobs)

            while True:
                if not jobs:
                    required_jp = base_job.required_unlock_jp
                    unlocked_job = base_job
                    break

                unlocked_job = jobs.pop()

                joblevels = []
                for name in JOBNAMES:
                    value = max(getattr(base_job, name),
                                getattr(unlocked_job, name))
                    if value:
                        joblevels.append(value)
                required_jp = calculate_jp_total(joblevels)
                if required_jp <= jp_remaining:
                    break
        else:
            required_jp = 0
            unlocked_job = random.choice(jobs)

        jp_remaining -= required_jp
        if self.is_lucavi:
            unlocked_level = 8
        else:
            unlocked_level = len([j for j in JOBLEVEL_JP if j <= jp_remaining])
            if random.choice([True, False]):
                unlocked_level += 1
            while randint(1, 7) == 7:
                unlocked_level += 1

        unlocked_level = min(unlocked_level, 8)
        self.unlocked = unlocked_job.otherindex
        self.unlocked_level = unlocked_level
        if self.is_lucavi and randint(1, 15) != 15:
            self.unlocked = 0
            candidates = get_ranked_secondaries()
            candidates = [SkillsetObject.get(c) for c in candidates]
            candidates = [ss.index for ss in candidates
                          if ss.not_just_swordskills and ss.no_randoms]
            index = None
            if self.secondary in candidates:
                index = candidates.index(self.secondary)
            elif randint(1, 5) == 5:
                index = 2 * (len(candidates) / 3)
            if index is not None and random.choice([True, False]):
                index = mutate_normal(index, maximum=len(candidates)-1)
                self.secondary = candidates[index]
            return True

        if randint(1, 20) == 20:
            candidates = get_ranked_secondaries()
            index = len(candidates) / 3
            index = mutate_normal(index, maximum=len(candidates)-1)
            self.secondary = candidates[index]
        elif (unlocked_job != base_job and unlocked_level > 1
                and randint(1, 3) != 3 and unlocked_job.name != "mime"):
            assert unlocked_job.otherindex in range(0x13)
            self.secondary = unlocked_job.otherindex + 5
        elif randint(1, 5) == 5:
            cands = []
            for name in JOBNAMES:
                if name == "mime":
                    continue
                value = max(getattr(base_job, name) if base_job else 0,
                            getattr(unlocked_job, name))
                if value:
                    cands.append(name)
            if cands:
                chosen = jobreq_namedict[random.choice(cands)]
                self.secondary = chosen.otherindex + 5
            else:
                self.secondary = 0xFE
        elif self.secondary != 0 or random.choice([True, False]):
            self.secondary = 0xFE

        return True

    def mutate_monster_job(self, preserve_graphic=False):
        monster_check = lambda u: (u.graphic == 0x82 and u.job >= 0x5E
                                   and u.job not in [0x91, 0x97]
                                   and u.map_id <= 0x1d5)
        if not monster_check(self):
            return True

        oldjob = self.job
        if self.named and (self.name, oldjob) in named_jobs:
            self.job = named_jobs[self.name, self.job]
            return True

        all_ranked_monster_jobs = get_ranked_monster_jobs()
        if self.map_id not in monster_selection and not preserve_graphic:
            assert self in mapunits[self.map_id]
            assert self.graphic == 0x82
            ranked_monster_jobs = list(all_ranked_monster_jobs)
            map_monster_jobs = [JobObject.get(u.job)
                                for u in mapunits[self.map_id]
                                if monster_check(u)]
            map_monster_jobs = sorted(map_monster_jobs, key=lambda u: u.index)
            assert JobObject.get(self.job) in map_monster_jobs
            lowjob = min(map_monster_jobs,
                         key=lambda j: ranked_monster_jobs.index(j))
            index = ranked_monster_jobs.index(lowjob)
            index = max(0, index-1)
            while index > 0 and random.choice([True, False]):
                index -= 1
            ranked_monster_jobs = ranked_monster_jobs[index:]
            ranked_monster_sprites = []
            for m in ranked_monster_jobs:
                if m.monster_portrait not in ranked_monster_sprites:
                    ranked_monster_sprites.append(m.monster_portrait)
            selected_sprites = []
            monster_sprites = set([m.monster_portrait
                                   for m in map_monster_jobs])
            for s in sorted(monster_sprites):
                temp_sprites = [t for t in ranked_monster_sprites
                                if t not in selected_sprites or t == s]
                index = temp_sprites.index(s)
                index = mutate_index(index, len(temp_sprites), [True, False],
                                     (-2, 3), (-1, 1))
                selected = temp_sprites[index]
                selected_sprites.append(selected)

            selected_monsters = [m for m in ranked_monster_jobs
                                 if m.monster_portrait in selected_sprites]
            if len(selected_monsters) <= 3:
                selected_monsters = [m for m in all_ranked_monster_jobs
                                     if m.monster_portrait in selected_sprites]
            monster_selection[self.map_id] = selected_monsters

        if preserve_graphic:
            selection = [m for m in all_ranked_monster_jobs
                         if (m.monster_portrait ==
                             JobObject.get(self.job).monster_portrait)]
        else:
            selection = monster_selection[self.map_id]
        myjob = get_job(self.job)
        ranked_selection = [m for m in all_ranked_monster_jobs
                            if m in selection or m == myjob]
        if not self.get_bit("enemy_team"):
            index = -2
            while random.choice([True, False]):
                index -= 1
            newjob = random.choice(ranked_selection[index:])
        else:
            index = ranked_selection.index(myjob)
            if myjob not in selection:
                ranked_selection.remove(myjob)
            if self.get_bit("always_present"):
                index = mutate_index(index, len(ranked_selection),
                                     [True, False, False], (-1, 2), (-1, 1))
            else:
                index = mutate_index(index, len(ranked_selection),
                                     [True, False], (-2, 3), (-1, 2))
            newjob = ranked_selection[index]
        self.job = newjob.index
        named_jobs[self.name, oldjob] = self.job
        return True

    def mutate(self, boost_factor=None,
               preserve_gender=False, preserve_job=False):
        if self.graphic == 0 and self.job == 0:
            return
        if boost_factor is None:
            boost_factor = boostd["jp"]
        self.mutate_stats()

        if self.is_lucavi:
            #self.mutate_rsm()  # done in job mutation
            self.mutate_secondary()
            return

        if self.job >= 0x5E:
            self.mutate_monster_job(preserve_graphic=preserve_job)
            return

        if preserve_job or self.job not in jobreq_indexdict:
            self.mutate_equips()
            self.mutate_rsm()
            self.mutate_secondary()
            return

        jp_remaining = self.jp_total
        jp_remaining = randint(jp_remaining, int(jp_remaining * boost_factor))

        generic_r, monster_r, other_r = mapsprite_restrictions[self.map_id]
        selection = sorted(mapsprite_selection[self.map_id],
                           key=lambda (j, g): (j.index, g))
        done_jobs = [j for (j, g) in selection]
        male_sel = [(j, g) for (j, g) in selection if g == "male"]
        female_sel = [(j, g) for (j, g) in selection if g == "female"]

        gender = None
        if self.named:
            preserve_gender = True

        if preserve_gender:
            if self.get_bit("male"):
                gender = "male"
            elif self.get_bit("female"):
                gender = "female"
            else:
                raise Exception("No gender.")

        if preserve_gender and not self.has_special_graphic:
            if gender == "male":
                assert male_sel or len(selection) < generic_r
            elif gender == "female":
                assert female_sel or len(selection) < generic_r

        assert self.job in jobreq_indexdict.keys()
        jobs = jobreq_namedict.values()
        jobs = [j for j in jobs if j.required_unlock_jp < jp_remaining]
        base_job = None

        if base_job is None and self.named and not self.has_special_graphic:
            if (self.name, self.job) in named_jobs:
                base_job = named_jobs[(self.name, self.job)]
            elif len(selection) >= generic_r:
                sel = [(j, g) for (j, g) in selection if g == gender]
                base_job, gen = random.choice(sel)
                assert gen == gender

        if base_job is None and (self.has_special_graphic
                                 or len(selection) < generic_r):
            if gender is None:
                gender = random.choice(["male", "female"])
                if self.map_id in [0x10d, 0x190, 0x1a8]:
                    # wiegraf
                    gender = "female"

            cands = [j for j in jobs if j not in done_jobs]
            if not cands:
                cands = jobs

            if gender == "male":
                cands = [c for c in cands if c.name != "dancer"]
            elif gender == "female":
                cands = [c for c in cands if c.name != "bard"]

            if cands:
                cands = sorted(cands, key=lambda j: j.required_unlock_jp)
                goal_length = (len(cands)/2) + 1
                while len(cands) > goal_length:
                    if randint(1, len(cands)) == 1:
                        break
                    else:
                        cands = cands[1:]
                base_job = random.choice(cands)
            else:
                base_job = jobreq_namedict['squire']

        if base_job is None:
            if self.named:
                assert (self.name, self.job) not in named_jobs
                if gender == "male":
                    cands = male_sel
                elif gender == "female":
                    cands = female_sel

                if not cands:
                    print "WARNING: Named unit can't keep their gender."
                    base_job, gender = random.choice(selection)
                    import pdb; pdb.set_trace()
                else:
                    base_job, gender = random.choice(cands)
            else:
                base_job, gender = random.choice(selection)

        assert base_job is not None
        if not self.has_special_graphic:
            if self.named and (self.name, self.job) in named_jobs:
                assert named_jobs[(self.name, self.job)] == base_job
            else:
                named_jobs[(self.name, self.job)] = base_job
            named_map_jobs[(self.map_id, self.job, gender)] = base_job
            mapsprite_selection[self.map_id].add((base_job, gender))

        self.job = base_job.index
        try:
            assert (len(mapsprite_selection[self.map_id]) <= generic_r)
        except Exception:
            print "ERROR: Sprite limit."
            import pdb; pdb.set_trace()

        if not self.has_special_graphic:
            self.set_gender(gender)

        self.mutate_equips()
        self.mutate_rsm()
        self.mutate_secondary()
        return True

    def set_gender(self, gender):
        if gender == "male":
            self.set_bit("male", True)
            self.set_bit("female", False)
            self.graphic = 0x80
        elif gender == "female":
            self.set_bit("female", True)
            self.set_bit("male", False)
            self.graphic = 0x81

    def mutate_equips(self):
        if self.get_bit("load_formation"):
            return

        for attr in ["lefthand", "righthand", "head", "body", "accessory"]:
            if (attr == "righthand" and (not 1 <= self.level <= 5) and
                    (self.has_swordskills or self.has_limitskills)
                    and random.randint(1, 10) != 10
                    and self.get_bit("enemy_team")):
                if self.has_limitskills:
                    self.righthand = 0x20
                elif self.has_swordskills:
                    self.equip_appropriate_sword()
            elif self.has_special_graphic:
                value = getattr(self, attr)
                if value in [0, 0xFF]:
                    setattr(self, attr, random.choice([0xFF, 0xFE]))
                elif (attr != "righthand" and value != 0xFE
                        and random.choice([True, False])):
                    if self.get_bit("enemy_team"):
                        bf = boostd["special_equipment"]
                    else:
                        bf = boostd["equipment"]
                    value = get_similar_item(
                        value, same_equip=True, boost_factor=bf).index
                    if (value in BANNED_ITEMS
                            and not self.get_bit("enemy_team")):
                        # just an extra safeguard against Stone Gun
                        continue
                    setattr(self, attr, value)
                elif randint(1, 3) == 3:
                    setattr(self, attr, 0xFE)
            elif random.choice([True, False]):
                setattr(self, attr, 0xFE)

    def equip_appropriate_sword(self):
        if self.level_normalized:
            if random.choice([True, False]):
                self.righthand = 0xFE
                return
            else:
                level = randint(1, randint(1, 40))
        else:
            level = self.level
        candidates = [i for i in ItemObject.every if i.itemtype in [3, 4]]
        candidates = sorted(candidates, key=lambda c: (c.enemy_level, c.index))
        try:
            max_index = max([n for (n, c) in enumerate(candidates)
                             if c.enemy_level <= level])
        except ValueError:
            max_index = 0
        exindex = None
        try:
            existing = ItemObject.get(self.righthand)
            if existing and existing.itemtype in [3, 4]:
                exindex = candidates.index(existing)
                max_index = max(exindex, max_index)
        except KeyError:
            pass
        booster = randint(2, randint(3, 8))
        if self.has_special_graphic:
            pass
        else:
            booster = randint(1, booster)
        max_index += booster
        index = randint(randint(1, max_index), max_index)
        if self.has_special_graphic and exindex:
            index = max(index, exindex+1)
        chosen = candidates[:index][-1]
        self.righthand = chosen.index

    def mutate_rsm(self):
        if self.get_bit("load_formation"):
            return

        job = JobObject.get(self.job)
        for attr in ["reaction", "support", "movement"]:
            cands = [a for a in AbilityObject.every
                     if getattr(a, "is_%s" % attr) is True]
            if self.has_special_graphic and randint(1, 3) == 3:
                cands = sorted(cands, key=lambda a: a.jp_cost)
                index = len(cands) / 2
                index = mutate_normal(index, maximum=len(cands)-1)
                setattr(self, attr, cands[index].index)
            elif random.choice([True, False]):
                setattr(self, attr, 0x1FE)

    def mutate_level(self):
        if (self.index <= 0xFFF and self.get_bit("randomly_present")
                and randint(1, 15) == 15):
            if not self.level_normalized:
                self.level += randint(0, 10) + randint(0, 10)
                self.level = min(self.level, 99)
            else:
                if self.level > 199:
                    self.level = 100
                self.level += randint(0, 10) + randint(0, 10)
                self.level = min(self.level, 199)
            SUPER_LEVEL_BOOSTED.append(self)
            return
        if not self.level_normalized:
            if self.is_lucavi:
                level = mutate_normal(self.level, minimum=1, maximum=99)
                level = int(round((level + self.level) / 2))
                if level < self.level:
                    self.level += (self.level - level)
                else:
                    self.level = level
            if 5 <= self.level <= 99:
                self.level = mutate_index(self.level, 99,
                                          (True, False), (-2, 3), (-1, 2))
            self.level = min(99, max(1, self.level))

    def mutate_stats(self):
        if self.job <= 3 or self.graphic <= 3:
            return

        self.mutate_level()

        for attr in ["brave", "faith"]:
            value = getattr(self, attr)
            if 0 <= value <= 100:
                value = mutate_normal(value, maximum=100)
                setattr(self, attr, value)

        if self.named and self.name in birthday_dict:
            self.month, self.day = birthday_dict[self.name]
        elif self.named or randint(1, 8) == 8:
            if random.choice([True, False, False]):
                self.month = randint(1, 12)
                self.day = randint(1, DAYS_IN_MONTH[self.month])
            elif not self.named and randint(1, 10) == 10:
                self.month, self.day = 0xFE, 0xFE

        if self.named and 1 <= self.month <= 12:
            birthday_dict[self.name] = (self.month, self.day)


class JobReqObject(TableObject):
    @property
    def job(self):
        assert 0x4A <= self.index < 0x5E
        return JobObject.get(self.index)

    def __le__(self, other):
        for attr in jobreq_namedict.keys():
            if getattr(self, attr) > getattr(other, attr):
                return False
        return True

    def same_reqs(self, other):
        for attr in jobreq_namedict.keys():
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True

    def __lt__(self, other):
        return self <= other and not self.same_reqs(other)

    @staticmethod
    def get(index):
        return jobreq_indexdict[index]

    def get_prereq_dict(self):
        prereq_dict = {}
        for attr in sorted(jobreq_namedict.keys()):
            value = getattr(self, attr)
            if value > 0:
                prereq_dict[attr] = value

        removed = []
        for attr in prereq_dict:
            prereq = jobreq_namedict[attr]
            for attr2 in prereq_dict:
                value = prereq_dict[attr2]
                value2 = getattr(prereq, attr2)
                if value2 >= value:
                    prereq_dict[attr2] = 0
                    if attr2 != "squire":
                        removed.append(attr2)
        return prereq_dict, removed

    @property
    def pretty_str(self):
        prereq_dict, removed = self.get_prereq_dict()
        s = "%s\n" % self.name.upper()
        for attr, value in prereq_dict.items():
            if value > 0:
                s += "  %s %s\n" % (value, attr)
        if removed:
            s += "  Also: " + ", ".join(sorted(set(removed)))

        return s.strip()

    @property
    def total_levels(self):
        total = 0
        for attr in jobreq_namedict.keys():
            total += getattr(self, attr)
        return total

    def set_required_unlock_jp(self):
        self.remax_jobreqs()

        joblevels = []
        for name in JOBNAMES:
            level = getattr(self, name)
            if level:
                joblevels.append(level)
        total = calculate_jp_total(joblevels)

        self.required_unlock_jp = total

    def remax_jobreqs(self):
        for name in JOBNAMES:
            value = getattr(self, name)
            if value == 0:
                continue
            jr = jobreq_namedict[name]
            jr.remax_jobreqs()
            for name in JOBNAMES:
                value = max(getattr(self, name), getattr(jr, name))
                setattr(self, name, value)

    def read_data(self, filename=None, pointer=None):
        super(JobReqObject, self).read_data(filename, pointer=pointer)
        self.squire, self.chemist = self.squche >> 4, self.squche & 0xF
        self.knight, self.archer = self.kniarc >> 4, self.kniarc & 0xF
        self.monk, self.priest = self.monpri >> 4, self.monpri & 0xF
        self.wizard, self.timemage = self.wiztim >> 4, self.wiztim & 0xF
        self.summoner, self.thief = self.sumthi >> 4, self.sumthi & 0xF
        self.mediator, self.oracle = self.medora >> 4, self.medora & 0xF
        self.geomancer, self.lancer = self.geolan >> 4, self.geolan & 0xF
        self.samurai, self.ninja = self.samnin >> 4, self.samnin & 0xF
        self.calculator, self.bard = self.calbar >> 4, self.calbar & 0xF
        self.dancer, self.mime = self.danmim >> 4, self.danmim & 0xF

    def copy_data(self, another):
        super(JobReqObject, self).copy_data(another)
        for name in JOBNAMES:
            setattr(self, name, getattr(another, name))

    def set_zero(self):
        for name in JOBNAMES:
            setattr(self, name, 0)

    def write_data(self, filename=None, pointer=None):
        self.squche = (self.squire << 4) | self.chemist
        self.kniarc = (self.knight << 4) | self.archer
        self.monpri = (self.monk << 4) | self.priest
        self.wiztim = (self.wizard << 4) | self.timemage
        self.sumthi = (self.summoner << 4) | self.thief
        self.medora = (self.mediator << 4) | self.oracle
        self.geolan = (self.geomancer << 4) | self.lancer
        self.samnin = (self.samurai << 4) | self.ninja
        self.calbar = (self.calculator << 4) | self.bard
        self.danmim = (self.dancer << 4) | self.mime
        super(JobReqObject, self).write_data(filename, pointer=pointer)


def get_units(filename=None):
    return UnitObject.every


def get_unit(index):
    return UnitObject.get(index)


def get_skillsets(filename=None):
    skillsets = SkillsetObject.every
    return skillsets[5:]


def get_skillset(index):
    try:
        return SkillsetObject.get(index)
    except KeyError:
        return None


def get_items(filename=None):
    items = ItemObject.every
    return items


def get_item(index):
    return ItemObject.get(index)


def get_monster_skills(filename=None):
    global g_monster_skills
    if g_monster_skills is not None:
        return list(g_monster_skills)
    mss = MonsterSkillsObject.every
    for ms in mss:
        ms.index += 0xb0
    g_monster_skills = mss
    return get_monster_skills()


def get_monster_skillset(index):
    return MonsterSkillsObject.get(index-0xb0)


def get_move_finds(filename=None):
    return MoveFindObject.every


def get_poaches(filename=None):
    return PoachObject.every


def get_abilities(filename=None):
    AbilityObject.get(0x1F3).jp_cost = 9999
    return [a for a in AbilityObject.every if a.index not in BANNED_SKILLS]


def get_abilities_attributes(filename=None):
    return AbilityAttributesObject.every


def get_ability(index):
    return AbilityObject.get(index)


def get_jobs(filename=None):
    jobs = JobObject.every
    for j in jobs:
        if j.index in range(0x4A, 0x5E):
            j.name = JOBNAMES[j.index - 0x4A]
        else:
            j.name = "%x" % j.index
    return jobs


def get_job(index):
    return JobObject.get(index)


def get_jobreqs(filename=None):
    global backup_jobreqs
    if backup_jobreqs is not None:
        return list(backup_jobreqs)

    jobreqs = JobReqObject.every
    for j, jobname in zip(jobreqs, JOBNAMES[1:]):
        j.name = jobname
    for j, jobindex in zip(jobreqs, range(0x4B, 0x60)):
        j.otherindex = j.index + 1
        j.index = jobindex
    squire = JobReqObject()
    squire.copy_data(jobreqs[0])
    squire.otherindex = 0
    squire.index = 0x4A
    squire.name = "squire"
    jobreqs = [squire] + jobreqs
    for j in jobreqs:
        jobreq_namedict[j.name] = j
        assert j.index not in jobreq_indexdict
        jobreq_indexdict[j.index] = j
        assert j.otherindex not in jobreq_indexdict
    for j in jobreqs:
        j.remax_jobreqs()

    backup_jobreqs = jobreqs
    return get_jobreqs()


def unlock_jobs(outfile):
    if JAPANESE_MODE:
        raise NotImplementedError
    f = open(outfile, 'r+b')
    f.seek(0x5a4f4)
    f.write("".join([chr(0) for _ in xrange(4)]))
    f.close()


def make_rankings():
    global rankdict
    if rankdict is not None:
        return dict(rankdict)

    print "Analyzing and ranking unit data."
    units = get_units()
    units = [u for u in units if u.graphic != 0]
    banned_jobs = [j.index for j in JobObject.every
                   if not any([u.job == j.index for u in units])]
    good_jobs = [j for j in JobObject.every if j.index not in banned_jobs]
    units = [u for u in units
             if u.map_id in range(1, 0xFE) + range(0x180, 0x1D5)]

    rankable_job_features = [
        "hpmult", "mpmult", "spdmult", "pamult", "mamult", "move", "evade",
        "monster_portrait"]
    bottomhalf = ["move", "jump"]
    feature_minmax = {}
    for feature in rankable_job_features:
        if feature in bottomhalf:
            featurevals = [getattr(j, feature) & 0xF for j in good_jobs]
        else:
            featurevals = [getattr(j, feature) for j in good_jobs]
        featurevals = [v for v in featurevals if v > 0]
        minval, maxval = min(featurevals), max(featurevals)
        feature_minmax[feature] = float(minval), float(maxval)
    for j in good_jobs:
        if j.index in banned_jobs:
            continue
        vals = [getattr(j, feature) for feature in rankable_job_features]
        zerocount = vals.count(0)
        if zerocount > (len(vals) / 2):
            j.rankval = 0 + (j.index * 0.0000001)
            continue
        scores = []
        for feature in rankable_job_features:
            value = getattr(j, feature)
            if feature in bottomhalf:
                value &= 0xF
            if value == 0:
                continue
            minval, maxval = feature_minmax[feature]
            value, maxval = (value - minval), (maxval - minval)
            score = (value / maxval)
            scores.append(score)
        scores = sorted(scores)[1:]  # drop lowest
        j.rankval = sum(scores) / len(scores)
        if j.is_lucavi:
            j.rankval *= 1.5
        elif j.monster_portrait == 0:
            j.rankval *= 1.3
        if j.crippled:
            j.rankval = j.rankval / 10.0

    ranked_jobs = sorted(good_jobs, key=lambda j: j.rankval)
    ranked_jobs = [j.index for j in ranked_jobs]

    rankable_features = [
        "map_id", "unlocked", "unlocked_level", "righthand", "lefthand",
        "head", "body", "accessory", "job", "secondary", "reaction", "support",
        "movement"]
    unrankable_values = [0, 0xFE, 0xFF]
    rankdict = {}
    for j in good_jobs:
        rankdict["job", j.index] = j.rankval
    for i in xrange(100):
        rankdict[("level", i)] = i
    for u in units:
        u.rankval = None

    oldstring = ""
    set_progress_counter(300)
    for i in xrange(300):
        check_progress_counter(i)
        tempdict = {}
        for feature in rankable_features:
            tempdict[feature] = []

        for u in units:
            rankvals = []
            rank = None
            if not u.level_normalized:
                rankvals.append(u.level)

            for feature in rankable_features:
                value = getattr(u, feature)
                if (feature, value) in rankdict:
                    rankvals.append(rankdict[feature, value])

            if rankvals:
                rank = float(sum(rankvals)) / len(rankvals)
                for feature in rankable_features:
                    value = getattr(u, feature)
                    if value & 0xFF in unrankable_values:
                        continue
                    key = (feature, value)
                    if key not in tempdict:
                        tempdict[key] = []
                        if key in rankdict:
                            tempdict[key].append(rankdict[key])
                    tempdict[key].append(rank)
            if not u.level_normalized:
                u.rankval = u.level
            elif rank:
                u.rankval = rank

        for key in tempdict:
            ranks = tempdict[key]
            if ranks:
                rank = float(sum(ranks)) / len(ranks)
                rankdict[key] = rank

        codestring = "".join([chr(int(round(u.rankval))) for u in units
                              if u.rankval is not None])
        if codestring == oldstring:
            break
        oldstring = codestring

    for j in good_jobs:
        rankdict["job", j.index] = j.rankval

    for j in good_jobs:
        key = ("secondary", j.skillset)
        if key not in rankdict:
            key2 = ("job", j.index)
            jobrank = rankdict[key2]
            jobranks = sorted([v for (k, v) in rankdict.items()
                               if "job" in k])
            secranks = sorted([v for (k, v) in rankdict.items()
                               if "secondary" in k])
            index = float(jobranks.index(jobrank)) / len(jobranks)
            index = index * max(len(secranks)-1, 0)
            index = min(int(index), len(secranks)-2)
            secrank = (secranks[index] + secranks[index+1]) / 2
            rankdict[key] = secrank

    return make_rankings()


def get_ranked(category, full=False):
    make_rankings()
    ranked = []
    for key in rankdict:
        cat, value = key
        if cat == category:
            ranked.append((rankdict[key], value))
    ranked = sorted(ranked)
    if full:
        return dict([(b, a) for (a, b) in ranked])
    ranked = [b for (a, b) in ranked]
    return ranked


def get_ranked_monster_jobs():
    global g_ranked_monster_jobs
    if g_ranked_monster_jobs is not None:
        return list(g_ranked_monster_jobs)

    g_ranked_monster_jobs = [get_job(m) for m in get_ranked("job")
                             if get_job(m).is_monster_job]
    return get_ranked_monster_jobs()


def get_ranked_secondaries():
    global g_ranked_secondaries
    if g_ranked_secondaries is not None:
        return list(g_ranked_secondaries)

    def clean_ranks(ranking):
        min_rank = min([b for (a, b) in ranking.items()])
        max_rank = max([b for (a, b) in ranking.items()])
        new_ranking = []
        for a, b in ranking.items():
            b = (b - min_rank) / (max_rank - min_rank)
            new_ranking.append((a, b))
        return dict(new_ranking)

    ranked = get_ranked("secondary", full=True)
    ranked = clean_ranks(ranked)
    other_ranked = get_ranked("job", full=True)
    other_ranked = clean_ranks(other_ranked)
    for job, rank in other_ranked.items():
        job = get_job(job)
        ranked[job.skillset] = rank
    candidates = {}
    for ss in get_skillsets():
        if ss.index in ranked:
            candidates[ss] = ranked[ss.index]
    for skillset, rank in candidates.items():
        rank = rank * rank * skillset.num_actions
        if rank > 0:
            num_free = skillset.num_free_actions
            abilities = [AbilityObject.get(a) for a in skillset.actions]
            acosts = [min(a.jp_cost, 1000) if a.jp_cost > 0 else 1000
                      for a in abilities]
            if acosts:
                average_jp_cost = sum(acosts) / len(acosts)
                rank = rank * average_jp_cost
            elif num_free == 0:
                rank = 0
            if skillset.index <= 0x18:
                rank = rank / 2
        candidates[skillset] = rank

    ranked = sorted(candidates, key=lambda c: (candidates[c], c.index))
    g_ranked_secondaries = [r.index for r in ranked if candidates[r] > 0]
    return get_ranked_secondaries()


def get_ranked_items():
    items = sorted(ItemObject.every, key=lambda i: i.rank)
    return [i for i in items if i.index > 0]


def get_ranked_skills(kind=None):
    if kind in ranked_skills_dict:
        return ranked_skills_dict[kind]

    ranked_jobs = get_ranked("job")
    if kind is None:
        tempjobs = get_jobs()
    else:
        tempjobs = get_jobs_kind(kind)

    jobs = []
    for r in ranked_jobs:
        tempranked = [j for j in tempjobs if j.index == r]
        if tempranked:
            jobs.append(tempranked[0])

    ranked_skills = []
    for j in jobs:
        if 1 <= j.skillset <= 0xAF:
            ss = get_skillset(j.skillset)
            for action in ss.actions:
                if action not in ranked_skills:
                    ranked_skills.append(action)

    ranked_monster_skills = []
    for j in jobs:
        if j.skillset >= 0xB0:
            ms = get_monster_skillset(j.skillset)
            for action in ms.attacks[:3]:
                if action not in ranked_monster_skills:
                    ranked_monster_skills.append(action)
    for j in jobs:
        if j.skillset >= 0xB0:
            ms = get_monster_skillset(j.skillset)
            action = ms.attacks[3]
            if action not in ranked_monster_skills:
                ranked_monster_skills.append(action)

    if 0 in ranked_monster_skills:
        ranked_monster_skills.remove(0)

    if not ranked_skills:
        ranked_skills = ranked_monster_skills
    else:
        ranked_skills = [get_ability(a) for a in ranked_skills]
        ranked_skills = [a for a in ranked_skills
                         if a.ability_type == 1 and a.jp_cost > 0]
        ranked_skills = sorted(ranked_skills, key=lambda r: r.jp_cost)
        ranked_monster_skills = [get_ability(a) for a in ranked_monster_skills]
        length_skills = len(ranked_skills)
        length_monster_skills = len(ranked_monster_skills)
        if length_skills < (length_monster_skills / 4):
            ranked_skills = ranked_monster_skills
        elif length_monster_skills < (length_skills / 4):
            ranked_skills = ranked_skills
        else:
            factor = float(length_skills) / length_monster_skills
            for i, ms in reversed(list(enumerate(ranked_monster_skills))):
                new_index = int(round(factor * i))
                new_index = max(0, min(new_index, length_skills-1))
                ranked_skills.insert(new_index, ms)

    uniq_ranked_skills = []
    for r in ranked_skills:
        if r not in uniq_ranked_skills:
            uniq_ranked_skills.append(r)

    ranked_skills_dict[kind] = uniq_ranked_skills
    return get_ranked_skills(kind)


def sort_mapunits():
    units = get_units()
    for u in units:
        if u.map_id not in mapsprites:
            mapsprites[u.map_id] = set([])
            mapunits[u.map_id] = set([])
        mapsprites[u.map_id].add((u.graphic, u.job))
        mapunits[u.map_id].add(u)
    for map_id in mapunits.keys():
        mapunits[map_id] = sorted(mapunits[map_id], key=lambda u: u.index)
        mapsprites[map_id] = sorted(mapsprites[map_id], key=lambda u: u.index)


def get_jobs_kind(kind):
    jobs = get_jobs()
    if kind == "human":
        jobs = [j for j in jobs if j.index < 0x5E]
    elif kind == "monster":
        jobs = [j for j in jobs if j.index >= 0x5E]
    else:
        raise Exception("Unknown kind.")
    return jobs


def mutate_job_level(filename):
    global JOBLEVEL_JP
    if JAPANESE_MODE:
        jbjp_pointer = 0x5fcd8
    else:
        jbjp_pointer = 0x62984

    jp_per_level = []
    for (a, b) in zip([0] + JOBLEVEL_JP, JOBLEVEL_JP):
        difference = b - a
        jp_per_level.append(difference)

    new_joblevel_jp = [0]
    for diff in jp_per_level:
        if JAPANESE_MODE:
            maximum = 800
        else:
            maximum = 800
            diff = randint(diff, int(diff*boostd["jp"]))
        diff = mutate_normal(diff, maximum=maximum)
        diff = int(round(diff*2, -2)) / 2
        new_joblevel_jp.append(new_joblevel_jp[-1] + diff)
    JOBLEVEL_JP = new_joblevel_jp[1:]
    f = open(filename, 'r+b')
    f.seek(jbjp_pointer)
    for j in JOBLEVEL_JP:
        write_multi(f, j, length=2)
    f.close()


def mutate_job_requirements():
    print "Randomizing job requirements."
    for index in [0x7a, 0x7d]:
        # don't let gariland ninjas throw shurikens and balls
        i = ItemObject.get(index)
        i.enemy_level = max(i.enemy_level, 5)

    reqs = get_jobreqs()
    done = [r for r in reqs if r.name == "squire"]
    levels = ([randint(0, 1)] +
              [randint(1, 2) for _ in range(2)] +
              [randint(2, 3) for _ in range(2)] +
              [randint(3, 5) for _ in range(4)] +
              [randint(5, 8) for _ in range(4)] +
              [randint(8, 13) + randint(0, 8) for _ in range(3)] +
              [randint(13, 21) + randint(0, 13) for _ in range(2)] +
              [randint(34, 55)])

    num_jobpools = 2 + random.choice([0, 0, 1])
    squire = [r for r in reqs if r.name == "squire"][0]
    jobpools = [set([]) for _ in xrange(num_jobpools)]
    allpool = set([squire])
    reqs = [r for r in reqs if r is not squire]
    while True:
        random.shuffle(reqs)
        calc, priest, wizard, timemage, oracle = [
            jobreq_namedict[name] for name in [
                "calculator", "priest", "wizard", "timemage", "oracle"]]
        mages = [priest, wizard, timemage, oracle]
        calc_index = reqs.index(calc)
        mages = [jr for jr in mages if reqs.index(jr) < calc_index]
        if mages:
            break

    assert len(levels) == len(reqs) == 19
    for req, numlevels in zip(reqs, levels):
        assert req not in done

        base_numlevels = numlevels
        req.set_zero()
        prereqs = []
        sublevels = []
        if req is calc:
            jobpoolcands = [j for j in jobpools if j & set(mages)]
        else:
            jobpoolcands = [j for j in jobpools if len(j) == len(
                min(jobpools, key=lambda j: len(j)))]
        jobpool = random.choice(jobpoolcands)
        if base_numlevels >= 30 or randint(1, 15) == 15:
            candidates = [c for c in done if c.name not in ["dancer", "bard"]]
        else:
            effective_jobpool = set(jobpool)
            while len(effective_jobpool) < base_numlevels:
                if allpool <= effective_jobpool:
                    break
                else:
                    allcands = sorted(allpool, key=lambda a: a.index)
                    allcands = [a for a in allcands
                                if a not in effective_jobpool]
                    if len(allcands) > 1:
                        allcands = [a for a in allcands if a.name != "squire"]
                    effective_jobpool.add(random.choice(allcands))
            candidates = [c for c in done
                          if c in effective_jobpool
                          and c.name not in ["dancer", "bard"]]
        while numlevels > 1:
            sublevel = randint(2, 3) + randint(0, 1)
            sublevel = min(sublevel, numlevels)
            if len(sublevels) == 14 or len(sublevels) == len(candidates):
                if len(sublevels) == 1:
                    index = 0
                else:
                    index = randint(0, len(sublevels)-1)
                sublevels[index] = min(sublevels[index] + sublevel, 8)
            else:
                sublevels.append(sublevel)
            numlevels -= sublevel

        if numlevels == 1:
            if sublevels:
                index = randint(0, len(sublevels)-1)
                sublevels[index] = min(sublevels[index] + 1, 8)
            else:
                sublevels = [1]

        assert len(sublevels) <= len(candidates)
        assert len(sublevels) <= 14
        if req is not calc:
            if len(candidates) >= (len(sublevels) + 1):
                candidates = candidates[:-1]
            if (len(candidates) >= (len(sublevels) + 1)
                    and random.choice([True, False])):
                candidates = candidates[1:]

        while True:
            prereqs = []
            for _ in range(len(sublevels)):
                tempcands = list(candidates)
                for c in candidates:
                    for pr in prereqs:
                        value = getattr(pr, c.name)
                        if value > 0:
                            tempcands.remove(c)
                            break
                if not tempcands:
                    tempcands = list(candidates)
                index = len(tempcands) - 1
                while index > 0:
                    if random.choice([True, False]):
                        if index <= 3 and random.choice([True, False]):
                            break
                        index -= 1
                    else:
                        break
                prereq = tempcands[index]
                prereqs.append(prereq)
                candidates.remove(prereq)
            if req is not calc:
                break
            if set(prereqs) & set(mages):
                break

        if req is calc:
            sublevels = sorted(sublevels)
            chosen_mage = random.choice(sorted(set(prereqs) & set(mages)))
            prereqs.remove(chosen_mage)
            random.shuffle(prereqs)
            prereqs = prereqs + [chosen_mage]
            assert len(prereqs) == len(sublevels)

        for prereq, sublevel in zip(prereqs, sublevels):
            assert hasattr(req, prereq.name)
            setattr(req, prereq.name, sublevel)

        for r in reqs:
            r.remax_jobreqs()
        done.append(req)
        if req.name not in ["dancer", "bard"]:
            if base_numlevels >= randint(0, 1) + randint(0, 1):
                jobpool.add(req)
            else:
                allpool.add(req)


def mutate_job_stats():
    print "Mutating job stats."
    jobs = get_jobs_kind("human")
    for j in jobs:
        j.mutate_stats()

    skillsets = SkillsetObject.every
    random.shuffle(skillsets)
    skillsets = ([s for s in skillsets if not s.is_generic]
                 + [s for s in skillsets if s.is_generic])
    for skillset in skillsets:
        abilities = skillset.actions + skillset.rsms
        if not abilities:
            continue
        abilities = [AbilityObject.get(a) for a in abilities]
        num_abilities = len(abilities)
        if num_abilities == 1:
            factors = [None]
        else:
            factors = [i / float(num_abilities-1)
                       for i in xrange(num_abilities)]
        jp_costs = [a.jp_cost for a in abilities]
        average_jp_cost = sum(jp_costs) / len(jp_costs)
        for (factor, a) in zip(factors, abilities):
            if a.jp_cost > 0:
                a.jp_cost = mutate_normal(a.jp_cost, maximum=3000)
                if a.jp_cost > 200:
                    a.jp_cost = int(round(a.jp_cost*2, -2) / 2)
                else:
                    a.jp_cost = int(round(a.jp_cost, -1))

                if num_abilities == 1:
                    a.learn_chance = 100
                elif 1 <= a.learn_chance <= 99 or randint(1, 20) == 20:
                    jp_factor = a.jp_cost / float(average_jp_cost)
                    if average_jp_cost < 500:
                        k = average_jp_cost / 500.0
                    else:
                        k = 1
                    learn_rate = ((factor * 110) +
                                  ((1-factor) * (25 / jp_factor)))
                    learn_rate = (learn_rate**2) / float(90)
                    learn_rate = (k*learn_rate) + ((1-k)*100)
                    minimum = randint(10, 40)
                    learn_rate = min(90, max(learn_rate, minimum))
                    learn_rate = mutate_normal(learn_rate, maximum=100)
                    a.learn_chance = learn_rate
            else:
                a.learn_chance = 100
            assert 0 <= a.learn_chance <= 100


def mutate_job_innates():
    print "Mutating job innate features."
    jobs = get_jobs_kind("human")
    for j in jobs:
        j.mutate_innate()


def mutate_skillsets():
    print "Shuffling job skillsets."
    skillsets = get_skillsets()
    skillsets = [s for s in skillsets if s.has_learnable_actions
                 and s.index not in BANNED_SKILLSET_SHUFFLE]

    doing_skillsets = [s for s in skillsets if 5 <= s.index <= 0x18]
    for j in STORYLINE_RECRUITABLE_JOBS:
        j = JobObject.get(j)
        doing_skillsets.append(SkillsetObject.get(j.skillset))

    done_actions = set([])
    for ss in doing_skillsets:
        done_actions |= set(ss.actions)
    random.shuffle(skillsets)
    for ss in skillsets:
        if ss in doing_skillsets:
            continue
        if set(ss.actions) - done_actions:
            doing_skillsets.append(ss)
            done_actions |= set(ss.actions)

    random.shuffle(doing_skillsets)
    considered_actions = set([])
    pulled_actions = {}
    for ss in doing_skillsets:
        actions = [a for a in ss.actions if a not in considered_actions]
        if len(actions) <= 1 and not 5 <= ss.index <= 0x18:
            continue
        num_to_pull = len(actions) / 2
        num_to_pull = randint(0, num_to_pull) + randint(0, num_to_pull)
        if num_to_pull > len(actions) / 2:
            num_to_pull = len(actions) - num_to_pull
        pulled = random.sample(actions, num_to_pull)
        for p in list(pulled):
            a = get_ability(p)
            if a.jp_cost > 0:
                ss.actions.remove(p)
            else:
                pulled.remove(p)
        for a in actions:
            if a not in considered_actions:
                if random.choice([True, False]):
                    considered_actions.add(a)
                elif a in pulled and random.choice([True, False]):
                    considered_actions.add(a)
        if pulled or 5 <= ss.index <= 0x18 or randint(1, 4) == 4:
            pulled_actions[ss] = pulled

    exchanges = [d for d in doing_skillsets if d in pulled_actions]
    exchanges2 = list(exchanges)
    random.shuffle(exchanges2)
    for a, b in zip(exchanges, exchanges2):
        pulled = pulled_actions[b]
        actions = list(a.actions)
        actions.extend(pulled)
        if len(actions) > 16:
            actions = random.sample(actions, 16)
        a_actions = sorted([x for x in actions if x in a.actions])
        b_actions = sorted([x for x in actions if x in pulled
                            and x not in a_actions])
        if random.choice([True, False]):
            a.actions = a_actions + b_actions
        else:
            a.actions = b_actions + a_actions
        assert len(a.actions) <= 16

    skillsets = get_skillsets()
    abilities = get_abilities()
    abilities = [a for a in abilities if a.jp_cost > 0
                 and 7 <= a.ability_type <= 9 and a.index not in BANNED_RSMS]
    abilities = [a.index for a in abilities]
    random.shuffle(skillsets)
    for skillset in skillsets:
        # RSMs for non-basic classes
        if 5 <= skillset.index <= 0x18:
            continue
        if skillset.index in BANNED_ANYTHING:
            continue
        if len(skillset.rsms) > 0:
            num_to_sample = 2 + randint(0, 3) + randint(0, 3)
            num_to_sample = min(num_to_sample, 6)
            chosens = random.sample(abilities, 6)
            chosens.extend(skillset.rsms)
            random.shuffle(chosens)
            chosens = chosens[:num_to_sample]
            skillset.rsms = sorted(set(chosens))

    done = [0x1d7]
    for skillset in skillsets:
        # RSMs for basic classes
        if not (5 <= skillset.index <= 0x18):
            continue
        if skillset.index in BANNED_ANYTHING:
            continue
        candidates = [a for a in abilities if a not in done]
        if skillset.index == 0xE and len(candidates) < 4:
            candidates = list(abilities)
        num_to_sample = min(len(candidates), 6)
        candidates = random.sample(candidates, num_to_sample)
        candidates += [a for a in skillset.rsms if a not in done]
        candidates = sorted(set(candidates))
        num_to_sample = randint(0, 3) + randint(0, 3)
        if num_to_sample <= 4 and random.choice([True, False]):
            num_to_sample += 1
        num_to_sample = min(num_to_sample, len(candidates), 6)
        if skillset.index == 0xE:
            num_to_sample = max(num_to_sample, 4)
            chosens = random.sample(candidates, num_to_sample)
            chosens[3] = 0x1d7  # secret hunt
            skillset.rsms = chosens
        else:
            chosens = random.sample(candidates, num_to_sample)
            skillset.rsms = sorted(chosens)
        done.extend(skillset.rsms)

    for skillset in get_skillsets():
        skillset.mutate_abilities()

    for index in BANNED_SKILLSET_SHUFFLE:
        if not 5 <= index <= 0x18:
            continue
        ss = get_skillset(index)
        for action in list(ss.actions):
            if randint(1, 8) == 8:
                ss.actions.remove(action)


# Ry Edit: Mutate functions for Inflict Status and Weapon/Item Stats
def mutate_inflict_status():
    print "Mutating weapon and ability status effects."
    inflict_statuses = InflictStatusObject.every
    for infst in inflict_statuses:
        infst.randomize_empty()
    abilities_attributes = get_abilities_attributes()
    for aa in abilities_attributes:
        aa.mutate_status()
    weapons = WeaponObject.every
    for w in weapons:
        w.mutate_status()


def mutate_items_and_weapons():
    print("Mutating weapon and item stats.")
    for w in WeaponObject.every:
        w.mutate()
    for s in ShieldObject.every:
        s.mutate()
    for ar in ArmorObject.every:
        ar.mutate()
    for acc in AccessoryObject.every:
        acc.mutate()
    for ci in ChemistItemObject.every:
        ci.mutate()
    for ia in ItemAttributesObject.every:
        ia.mutate()
    items = get_items()
    for i in items:
        i.mutate_attributes()


def mutate_abilities_attributes():
    print "Mutating ability attributes."
    abilities_attributes = get_abilities_attributes()
    for aa in abilities_attributes:
        aa.mutate()

    for skillset in SkillsetObject.every:
        if skillset.index != 0x29:
            for action in skillset.actions:
                if not AbilityAttributesObject.has(action):
                    continue
                aa = AbilityAttributesObject.get(action)
                if aa.get_bit("require_materia_blade"):
                    aa.set_bit("require_materia_blade", False)
                    aa.set_bit("require_sword", True)

        if 5 <= skillset.index <= 0x17:
            for action in skillset.actions:
                if not AbilityAttributesObject.has(action):
                    continue
                aa = AbilityAttributesObject.get(action)
                aa.set_bit("cant_mimic", False)

    for ms in MonsterSkillsObject.every:
        for attack in ms.attacks:
            if not AbilityAttributesObject.has(attack):
                continue
            aa = AbilityAttributesObject.get(attack)
            aa.set_bit("require_materia_blade", False)
            aa.set_bit("require_sword", False)

    for j in JobObject.every:
        if j.is_lucavi:
            ss = SkillsetObject.get(j.skillset)
            for action in ss.actions:
                if not AbilityAttributesObject.has(action):
                    continue
                aa = AbilityAttributesObject.get(action)
                aa.set_bit("require_materia_blade", False)
                aa.set_bit("require_sword", False)

    for index in MATH_SKILLSETS:
        skillset = SkillsetObject.get(index)
        for action in skillset.actions:
            if not AbilityAttributesObject.has(action):
                continue
            aa = AbilityAttributesObject.get(action)
            if not aa.get_bit("math_skill") and randint(1, 5) == 5:
                aa.set_bit("math_skill", True)


def mutate_monsters():
    print "Mutating monsters."
    jobs = get_jobs_kind("monster")
    for j in jobs:
        j.mutate_stats()
        j.mutate_innate()
    print "Mutating monster skills."
    for ms in get_monster_skills():
        ms.mutate()


def mutate_units():
    units = get_units()
    for key, value in sorted(mapsprites.items()):
        value = sorted(value)
        generic = len([_ for (g, _) in value if g in (0x80, 0x81)])
        monster = len([_ for (g, _) in value if g == 0x82])
        other = len([_ for (g, _) in value
                     if g not in (0x80, 0x81, 0x82, 0x00)])
        if key in [0x19B, 0x1AA]:
            other = max(other, 3)

        remaining = 9 - (generic + monster + other)
        if remaining > 0 and key in range(0x100, 0x14B):
            # only appropriate for maps you can't assign units to
            generic += remaining
        elif key >= 0x180 and generic > 2 and other > 2:
            # account for event poses
            generic -= 1

        mapsprite_restrictions[key] = (generic, monster, other)
        mapsprite_selection[key] = set([])

    named_units = {}
    for u in units:
        if u.named and not u.has_special_graphic:
            if u.map_id not in named_units:
                named_units[u.map_id] = []
            named_units[u.map_id].append(u)

    make_rankings()

    print "Mutating unit data."
    map_ids = sorted(named_units, key=lambda m: len(named_units[m]))
    map_ids = reversed(map_ids)
    for m in map_ids:
        nus = named_units[m]
        nuslen = len(nus)
        random.shuffle(nus)
        # do one each of males, females, monsters to get units to work with
        males = [u for u in nus if u.get_bit("male")]
        females = [u for u in nus if u.get_bit("female")]
        monsters = [u for u in nus if u.get_bit("monster")]
        nus = males[1:] + females[1:] + monsters[1:]
        random.shuffle(nus)
        nus = males[:1] + females[:1] + monsters[:1] + nus
        assert len(set(nus)) == nuslen
        for u in nus:
            assert not u.has_special_graphic
            u.mutate()
            u.job_mutated = True

    random.shuffle(units)
    unnamed = [u for u in units if u.has_special_graphic or not u.named]
    set_progress_counter(len(unnamed))
    for i, u in enumerate(unnamed):
        if u.index >> 4 == 0x133:
            continue
        check_progress_counter(i)
        u.mutate()


def mutate_units_special():
    print "Adding special surprises."
    ranked_jobs = get_ranked("job")
    special_jobs = [j for j in get_jobs() if not 5 <= j.skillset <= 0x18
                    and not j.skillset == 0
                    and not 0x4A <= j.index <= 0x8F
                    and not j.index >= 0x92]
    for j in list(special_jobs):
        for u in UnitObject.every:
            if u.job == j.index and 1 <= u.graphic <= 0x7F:
                break
        else:
            special_jobs.remove(j)
    special_jobs = [j.index for j in special_jobs]
    special_jobs = [j for j in ranked_jobs if j in special_jobs]
    backup_special_jobs = list(special_jobs)
    for map_id in range(1, 0xFE) + range(0x180, 0x1D5):
        if map_id <= 0xFF:
            boost_factor = boostd["random_special_unit"]
        else:
            boost_factor = boostd["story_special_unit"]

        lucavi_special = False
        units = sorted(mapunits[map_id], key=lambda u: u.index)
        if any([u.is_lucavi for u in units]):
            if map_id == 0x1a9:
                continue
            lucavi_special = (any([u.is_altima for u in units])
                              or randint(1, 3) != 3)
            lucavi_unit = max([u for u in units if u.is_lucavi],
                              key=lambda u2: u2.level)
        elif map_id == 1:
            probval = 8
        elif map_id == 0x180:
            probval = 15
            special_jobs = list(backup_special_jobs)
        else:
            probval -= 1
            probval = max(probval, 2)

        if map_id in [0x183, 0x184, 0x185]:
            continue
        if lucavi_special or randint(1, probval) == 1:
            candidates = [u for u in units if 0x80 <= u.graphic <= 0x82]
            noncandidates = [u for u in units if u not in candidates]
            noncandjobs = [u.job for u in noncandidates
                           if 0x80 <= u.graphic <= 0x82]
            candidates = [c for c in candidates if c.job not in noncandjobs]

            for c in list(candidates):
                if c.named or not c.get_bit("enemy_team"):
                    if 0x5E <= c.job <= 0x8D or c.graphic == 0x82:
                        candidates = [d for d in candidates if
                                      d.monster_portrait != c.monster_portrait]
                    elif c.graphic in [0x80, 0x81]:
                        candidates = [d for d in candidates
                                      if d.job != c.job]
                    assert c not in candidates

            if not candidates:
                continue
            jobs = [c.job for c in candidates]
            jobs = [get_job(j).monster_portrait | 0x100 if 0x5E <= j <= 0x8D
                    else j for j in jobs]
            jobs = [j for j in jobs if (j & 0xFF) > 0]
            jobs = Counter(jobs)
            if len(jobs.keys()) == 1 and not lucavi_special:
                continue

            jobs = [key for key in jobs if jobs[key] == min(jobs.values())]
            replace_job = random.choice(sorted(jobs))
            if replace_job >= 0x100:
                replace_job &= 0xFF
                replace_job = [c.job for c in candidates if
                               c.monster_portrait == replace_job]
                replace_job = sorted(replace_job)[0]

            cand_jobs = [j for j in ranked_jobs
                         if j in special_jobs or j == replace_job
                         or (lucavi_special and j == lucavi_unit.job)]
            if map_id in [0x10d, 0x190, 0x1a8, 0x1b0]:
                cand_jobs = [j for j in cand_jobs
                             if JobObject.get(j).guaranteed_female
                             or j == replace_job
                             or (lucavi_special and j == lucavi_unit.job)]
            if map_id >= 0x180:
                cand_jobs = [j for j in cand_jobs if j > 3]
            index = cand_jobs.index(replace_job)
            if lucavi_special:
                lucorder_index = LUCAVI_ORDER.index(lucavi_unit.job)
                badlucs = LUCAVI_ORDER[lucorder_index:]
                cand_jobs = [c for c in cand_jobs if
                             c == lucavi_unit.job or c not in badlucs]
                lucavi_index = cand_jobs.index(lucavi_unit.job)
                index = (index + lucavi_index) / 2
                if lucavi_unit.job in cand_jobs and randint(1, 10) != 10:
                    cand_jobs.remove(lucavi_unit.job)
            index = randint(index, int(round(index * boost_factor)))
            cand_jobs.remove(replace_job)
            if len(cand_jobs) >= 7:
                index = min(index, len(cand_jobs)-4)
                index = max(index, 3)
            index = mutate_normal(index, maximum=len(cand_jobs)-1)
            new_job = cand_jobs[index]

            jobunits = [u for u in get_units() if u.job == new_job
                        and u.map_id in USED_MAPS]
            jobgraphics = Counter([u.graphic for u in jobunits])
            jobgraphics = [key for key in jobgraphics
                           if jobgraphics[key] == max(jobgraphics.values())]
            if not jobunits or not jobgraphics:
                continue
            graphic = random.choice(sorted(jobgraphics))
            jobunits = [u for u in jobunits if u.graphic == graphic]

            def jobunit_filter(strength):
                candidates = []
                for u in jobunits:
                    score = 0
                    if u.get_bit("join_after_event"):
                        score += 1
                    for field in ["secondary", "lefthand", "righthand", "head",
                                  "body", "accessory", "reaction", "support",
                                  "movement"]:
                        value = getattr(u, field) & 0xFF
                        if 1 <= value <= 0xFD:
                            score += 1
                    if score > strength:
                        candidates.append(u)
                return candidates

            threshold = randint(0, 5) + randint(0, 5)
            while True:
                tempunits = jobunit_filter(threshold)
                if tempunits:
                    break
                threshold -= 1

            jobunits = tempunits
            chosen_unit = random.choice(sorted(jobunits,
                                               key=lambda u: u.index))

            if not 0x5E <= replace_job:
                change_units = [u for u in units if u.job == replace_job]
                if any([u.graphic == chosen_unit.graphic
                        and not u.get_bit("enemy_team") for u in units]):
                    continue
            else:
                mg = get_job(replace_job).monster_portrait
                assert mg > 0
                change_units = [u for u in units
                                if u.monster_portrait == mg]

            change_units = [u for u in change_units if u.graphic > 0]
            change_units = sorted(change_units, key=lambda u: u.index)
            old_job = change_units[0].job
            alternate_team = not lucavi_special and randint(1, 25) == 25
            for unit in change_units:
                try:
                    assert not any([unit.named, unit.has_special_graphic,
                                    not unit.get_bit("enemy_team")])
                except:
                    raise Exception("Invalid unit replacement.")

                unit.job = chosen_unit.job
                unit.graphic = chosen_unit.graphic
                for bitname in ["monster", "female", "male", "hidden_stats"]:
                    unit.set_bit(bitname, chosen_unit.get_bit(bitname))
                copy_attrs = ["job", "graphic", "month", "day", "trophy",
                              "gil", "brave", "faith", "palette", "secondary",
                              "reaction", "support", "movement", "unlocked",
                              "unlocked_level"]
                for attr in copy_attrs:
                    setattr(unit, attr, getattr(chosen_unit, attr))
                if lucavi_special:
                    for attr in ["lefthand", "righthand", "head", "body",
                                 "accessory", "secondary"]:
                        chosenvalue = getattr(chosen_unit, attr)
                        oldvalue = getattr(unit, attr)
                        if (1 <= chosenvalue <= 0xFE and
                                random.choice([True, False])):
                            setattr(unit, attr, chosenvalue)
                        elif oldvalue in [0, 0xFF]:
                            setattr(unit, attr, 0xFE)
                    for attr in ["reaction", "support", "movement"]:
                        chosenvalue = getattr(chosen_unit, attr)
                        oldvalue = getattr(unit, attr)
                        if (1 <= chosenvalue <= 0x1FE
                                and random.choice([True, False])):
                            setattr(unit, attr, chosenvalue)
                        elif oldvalue in [0, 0x1FF]:
                            setattr(unit, attr, 0x1FE)
                elif alternate_team or randint(1, 10) == 10:
                    unit.set_bit("alternate_team", True)
                for method in ["mutate_equips", "mutate_rsm",
                               "mutate_secondary", "mutate_level"]:
                    if random.choice([True, False]):
                        getattr(unit, method)()
                unit.set_bit("enemy_team", True)
                if chosen_unit.named:
                    unit.name = chosen_unit.name
                SUPER_SPECIAL.append(unit)

            job = get_job(chosen_unit.job)
            if (not job.can_invite and
                    random.choice([True, False, False])):
                unit = random.choice(change_units)
                unit.set_bit("join_after_event", True)

            similar_graphic_jobs = [u.job for u in UnitObject.every
                                    if u.graphic == chosen_unit.graphic]
            special_jobs = [j for j in special_jobs
                            if j not in similar_graphic_jobs]
            if not special_jobs:
                special_jobs = list(backup_special_jobs)

            if map_id >= 0x180:
                if not lucavi_special:
                    probval = max(probval, 15)
            else:
                probval = max(probval, 8)


def randomize_enemy_formations():
    es = [e for e in EncounterObject.every
          if e.map_id and e.entd and e.event and e.grid]

    def generate_heatmap(m, example_unit, done_units=None, upper=True):
        enemy_units = [u for u in done_units if u.get_bit("enemy_team")]
        ally_units = [u for u in done_units if u not in enemy_units]
        if not example_unit.get_bit("enemy_team"):
            enemy_units, ally_units = ally_units, enemy_units
        heatmap = [list([100 for _ in range(m.width)])
                   for _ in range(m.length)]
        for y in xrange(len(heatmap)):
            for x in xrange(len(heatmap[0])):
                if m.get_tile_value(x, y, "bad"):
                    if (m.get_tile_value(x, y, "unreachable") or
                            m.get_tile_value(x, y, "bad_regardless") or
                            example_unit.x != x or example_unit.y != y):
                        heatmap[y][x] = -999999999
                        continue
                for u in done_units:
                    if u.x == x and u.y == y:
                        heatmap[y][x] = -999999999
                        break
                    if u.x == x:
                        heatmap[y][x] -= 10
                    if u.y == y:
                        heatmap[y][x] -= 10
                if heatmap[y][x] <= -99999999:
                    continue
                if x == 0 or x == len(heatmap[0])-1:
                    heatmap[y][x] -= 5
                elif y == 0 or y == len(heatmap)-1:
                    heatmap[y][x] -= 5
                for i in xrange(-9, 10):
                    for j in xrange(-9, 10):
                        if min(x+i, y+j) < 0:
                            continue
                        dist = abs(i) + abs(j)
                        if dist > 9:
                            continue
                        if dist <= 2:
                            for u in enemy_units:
                                if u.x == x+i and u.y == y+j:
                                    heatmap[y][x] -= (16 / max(dist, 1))
                        if dist >= 4:
                            for u in enemy_units:
                                if u.x == x+i and u.y == y+j:
                                    heatmap[y][x] += max(10 - dist, 0)
                        try:
                            party = m.get_tile_value(x+i, y+j, "party")
                            if party:
                                distval = max(10 - dist, 0)
                                if example_unit.get_bit("enemy_team"):
                                    heatmap[y][x] -= int(round(distval ** 1.5))
                                elif distval < 7:
                                    heatmap[y][x] += distval / 2
                        except IndexError:
                            pass
        values = sorted(set([v for row in heatmap for v in row]))
        values = dict([(k, v) for (v, k) in enumerate(values)])
        valids = sorted(values.values())
        valids = valids[randint(0, len(valids)-1):]
        if random.choice([True, False]):
            valids = valids[randint(0, len(valids)-1):]
        candidates = []
        for y, row in enumerate(heatmap):
            for x, v in enumerate(row):
                heatmap[y][x] = values[heatmap[y][x]]
                if heatmap[y][x] in valids:
                    candidates.append((x, y))
        x, y = random.choice(candidates)
        example_unit.x, example_unit.y = x, y
        example_unit.fix_facing(m)
        example_unit.facing &= 0x7F
        if upper and m.get_tile_value(x, y, "upper"):
            if random.choice([True, True, True, False]):
                example_unit.facing |= 0x80
        return heatmap

    set_progress_counter(len(es))
    for n, e in enumerate(es):
        check_progress_counter(n)
        m = MapObject.get_map(e.map_id)
        if not any(m.get_tile_values("party")):
            continue
        if e.mutated:
            units = m.units
        else:
            units = m.nonmoving_units
        random.shuffle(units)
        for i in xrange(len(units)):
            ex = units[i]
            done = units[:i]
            generate_heatmap(m, ex, done, upper=not e.mutated)

        new_units = []
        rogue = False
        while True:
            unused = list(m.unused_units)
            threshold = int(60 * ((0.5*boostd['difficulty_factor'])
                                  ** len(new_units)))
            threshold = min(threshold, 60)
            value = randint(1, 100)
            if len(unused) < 6 or value > threshold:
                break
            new = max(unused, key=lambda u: u.index)
            used = (m.nonmoving_units +
                    [u for u in m.moving_units if u.graphic & 0x80])
            used = sorted(set(used), key=lambda u: u.index)
            used = [u for u in used if not u.is_lucavi and u.level != 1]
            temp = [u for u in used
                    if u.job not in [u2.job for u2 in new_units]]
            if temp and random.choice([True, True, False]):
                used = temp
            if not used:
                break
            used = [u for u in used if not u.has_special_graphic]
            if not used:
                continue
            old = random.choice(used)
            new.copy_data(old)
            new.mutate(preserve_job=True)
            new.unlocked_level = old.unlocked_level
            new_enemies = [u for u in new_units if u.get_bit("enemy_team")]
            new.set_bit("randomly_present", False)
            new.set_bit("always_present", True)
            new.set_bit("join_after_event", False)
            new.set_bit("enemy_team", True)
            if not rogue:
                if boostd["difficulty_factor"] > 1.0:
                    chance = max(7-len(new_enemies), 1)
                else:
                    chance = max(5-(2*len(new_enemies)), 1)
                if randint(1, chance) == 1:
                    new.set_bit("enemy_team", False)
                    if (not new.has_special_graphic and
                            random.choice([True, True, False])):
                        new.set_bit("join_after_event", True)
                    rogue = True
                if (boostd["difficulty_factor"] > 1.0
                        or new.get_bit("enemy_team")):
                    if randint(1, 10) == 10:
                        new.set_bit("alternate_team", True)
                        rogue = True
            while True:
                generate_heatmap(m, new, units+new_units, upper=not e.mutated)
                for u in m.units:
                    if u != new and u.x == new.x and u.y == new.y:
                        break
                else:
                    break
            new_units.append(new)


def randomize_ending(outfile):
    if JAPANESE_MODE:
        raise NotImplementedError
    enc = EncounterObject.get(0x12b)
    enc.following = 0
    enc.randomize_music(force_battle=True)
    enc.music[0] = 0x45
    f = open(outfile, 'r+b')
    f.seek(0x4DC938)
    g = open(CONDITIONALSFILE, 'rb')
    f.write(g.read())
    g.close()

    ramza_unit = UnitObject.get(0x1333)
    delita_unit = UnitObject.get(0x1330)
    ovelia_unit = UnitObject.get(0x1331)
    chocobo_unit = UnitObject.get(0x1332)
    delita_unit.backup_jp_total = 500000
    ovelia_unit.backup_jp_total = 500000
    delita_unit.mutate(preserve_job=True)
    ovelia_unit.mutate(preserve_job=True)
    chocobo_unit.mutate(preserve_job=True)
    delita_unit.level = min(int(boostd["difficulty_factor"] * 100), 199)
    ramza_unit.set_bit("always_present", False)
    ramza_unit.set_bit("load_formation", True)
    ramza_unit.set_bit("control", True)
    ramza_unit.set_bit("enemy_team", False)
    delita_unit.set_bit("enemy_team", True)
    del_job = JobObject.get(delita_unit.job)
    del_job.immune_status &= (((2**40)-1) ^ INVITE_STATUS)

    x, y = 6, 6
    north = 2
    ramza = 3
    ramza_unit.unit_id = ramza
    f.seek(0x9959B2)  # delita with flowers
    f.write("".join(map(chr, [
        0xE5, 0x01, 0x00,                                   # wait for message
        0x5F, ramza, 0x00, x, y, 0x00, north,               # warp ramza
        0x45, ramza, 0x00, 0x00,                            # add ramza
        0x48,                                               # wait add unit
        0x21, 0x6A, 0x00,                                   # teleport sound
        0x98, ramza, 0x00,                                  # teleport in
        0x11, ramza, 0x00, 0x2C, 0x00, 0x00,                # animate ramza
        0x44, ramza, 0x00,                                  # draw ramza
        0xF1, 30, 0x00,                                     # wait
        0x11, delita_unit.unit_id, 0x00, 0x01, 0x00, 0x00,  # animate delita
        0xF1, 30, 0x00,                                     # wait
        0x53, ramza, 0x00, 0x04, 0x01, 0x00, 0x00, 0x00,    # face ramza
        #0x22, 0x01, 127, 0x00,                              # change music
        0x76, 0x00, 0x01, 12, 64, 0x00, 4,                  # darken screen
        0xE5, 0x36, 0x00,                                   # wait for dark
        0x78, 0x0F, 90,                                     # show conditions
        0xE5, 0x38, 0x00,                                   # wait for dark
        0x77,                                               # remove dark
        0xE5, 0x36, 0x00,                                   # wait for dark
        0xDB,                                               # end event
        ])))
    f.close()

    henchmen = [UnitObject.get(u).graphic for u in range(0x1b93, 0x1b97)]
    used_graphics = sorted(set([u.graphic for u in UnitObject
                                if u.named and 1 <= u.graphic <= 0x77
                                and u.graphic not in henchmen]))
    chosen = random.sample(used_graphics, 4)
    priest, others = (chosen[0], chosen[1:])
    others += henchmen
    assert len(others) == 7
    random.shuffle(others)
    otherunits = [u for u in mapunits[0x134] if 0x1341 <= u.index <= 0x1347]
    otherunits = sorted(otherunits, key=lambda u: u.index)
    for u, g in zip(otherunits, others):
        u.graphic = g

    UnitObject.get(0x1348).graphic = priest


def restore_warjilis(outfile, before=0xAB, new_entd=0x1DC,
                     map_id=42, monsters=False):
    if JAPANESE_MODE:
        raise NotImplementedError
    f = open(outfile, 'r+b')
    f.seek(0x823804)
    f.write("".join([chr(0xF2) for _ in xrange(9)]))  # END bg color
    f.close()
    gariland = EncounterObject.get(9)
    new_enc = EncounterObject.get_unused()
    scenario = new_enc.scenario
    new_enc.copy_data(gariland)
    new_enc.scenario = scenario
    new_enc.event = 0x25  # deep dungeon END event
    new_enc.map_id = map_id
    new_enc.ramza = 0
    new_enc.randomize_music(prefer_unused=True)
    new_enc.randomize_weather()
    new_enc.entd = new_entd  # 1dc = test Dancers
    blank_unit = UnitObject.get(0x1d)
    assert blank_unit.job == blank_unit.graphic == 0
    for u in mapunits[new_entd]:
        u.copy_data(blank_unit)
    new_enc.generate_formations(numchar_override=1)
    mymap = MapObject.get_map(map_id)

    special_jobs = [
        j for j in get_jobs() if not 5 <= j.skillset <= 0x18
        and j.skillset not in [0, 0x2D, 0x2E, 0x32]
        and not 0x4A <= j.index <= 0x8F
        and not j.index >= 0x92
        and not j.index < 4
        and not j.crippled
        and not j.is_lucavi
        and not j.start_status & RERAISE_STATUS
        and not j.innate_status & RERAISE_STATUS
        and j.get_most_common("name") not in [None, 0xFF]
        and j.get_most_common("graphic") not in [None, 0x80, 0x81, 0x82]]

    partner_job = random.choice(special_jobs)
    partner = mapunits[new_entd][14]
    if not monsters:
        special_jobs = [j for j in special_jobs
                        if j.skillset != partner_job.skillset]
        enemy_job = random.choice(special_jobs)
        real_jobs = sorted(set(range(0x4A, 0x5E) + [enemy_job.index]))
        random.shuffle(real_jobs)
    else:
        special_jobs = [j for j in get_jobs() if j.index >= 0x5E
                        and j.skillset >= 0xB0 and
                        j.get_most_common("graphic") == 0x82]
        portraits = [j.monster_portrait for j in special_jobs]
        portraits = sorted(set(portraits))
        portraits = random.sample(portraits, 7)
        portraits = sorted(portraits * 2)
        chosen_monsters = []
        for p in portraits:
            candidates = [j for j in special_jobs if j.monster_portrait == p
                          and j not in chosen_monsters]
            c = random.choice(candidates)
            chosen_monsters.append(c)
        assert len(set(chosen_monsters)) == 14
        random.shuffle(chosen_monsters)
        for u in UnitObject.every:
            if (u.graphic == 0x82 and u.job >= 0x5E and u.name == 0xFF
                    and JobObject.get(u.job).skillset >= 0xB0):
                base_monster = u
                break

    units = mapunits[new_entd][:15]
    for unit in units:
        if unit == partner:
            job = partner_job
            for attr in ["name", "month", "day", "brave", "faith", "secondary",
                         "reaction", "movement", "palette",
                         "graphic", "misc1", "misc2"]:
                setattr(unit, attr, job.get_most_common(attr))
            unit.job = job.index
        elif monsters:
            unit.copy_data(base_monster)
            unit.job = chosen_monsters.pop().index
        else:
            job = enemy_job
            for attr in ["misc1", "misc2", "palette", "graphic"]:
                setattr(unit, attr, job.get_most_common(attr))
            for attr in ["month", "day", "brave", "faith", "secondary"]:
                setattr(unit, attr, 0xFE)
            for attr in ["reaction", "movement"]:
                setattr(unit, attr, 0x1FE)
            unit.name = 0xFF
            unit.job = real_jobs.pop()
            if unit.job == job.index:
                for attr in ["name", "day", "brave", "faith"]:
                    setattr(unit, attr, job.get_most_common(attr))

        unit.set_bit("always_present", True)
        for bit in ["save_formation", "load_formation", "hidden_stats",
                    "test_teta", "randomly_present", "join_after_event",
                    "alternate_team", "immortal"]:
            unit.set_bit(bit, False)
        if unit == partner:
            unit.set_bit("enemy_team", False)
            unit.set_bit("control", False)
            unit.set_bit("hidden_stats", True)
            unit.set_bit("immortal", True)
            unit.level = randint(randint(50, 99), 99)
        else:
            unit.level = randint(1, randint(1, randint(1, 99)))
            unit.set_bit("enemy_team", True)
            unit.set_bit("control", True)

        if not monsters:
            unit.unlocked_level = 8
            unit.mutate(preserve_job=True, preserve_gender=True)
            unit.unlocked_level = 8

        unit.trophy = 0
        unit.gil = 0
        if unit == partner:
            unit.righthand = 0x25
            unit.head = 0xab
            unit.body = 0xb8
            unit.accessory = 0xec
            unit.secondary = 0xfe
            unit.lefthand = 0xfe
            unit.support = 0x1db
        elif monsters:
            pass
        else:
            unit.support = random.choice(range(0x1C8, 0x1DF) + [0x1E2, 0x1E3])
            unit.reaction = 0
            for attr in ["lefthand", "head", "body", "accessory"]:
                setattr(unit, attr, 0xFF)
            unit.righthand = 0xFE
            item_level = randint(randint(20, 40), 100)
            attr = random.choice(
                ["righthand", "lefthand", "head", "body", "accessory"])
            if attr == "righthand":
                candidates = [c for c in ItemObject if c.get_bit("weapon")]
                setattr(unit, random.choice(["lefthand", "head", "body",
                                             "accessory"]), 0xFE)
            elif attr == "lefthand":
                candidates = [c for c in ItemObject if c.get_bit("shield")]
            else:
                candidates = [c for c in ItemObject if c.get_bit(attr)]
            candidates = [c for c in candidates if c.enemy_level <= item_level]
            if candidates:
                candidates = random.sample(candidates, min(len(candidates), 3))
                setattr(unit, attr,
                        max(candidates, key=lambda c: c.enemy_level).index)

        bads = mymap.get_values_grid("bad")
        candidates = []
        backups = []
        for j in xrange(mymap.length):
            for i in xrange(mymap.width):
                backed_up = False
                for a, b in product(range(-1, 2), range(-1, 2)):
                    i2, j2 = i+a, j+b
                    if (i2 < 0 or j2 < 0
                            or i2 >= mymap.width or j2 >= mymap.length):
                        continue
                    value = bads[j2][i2]
                    if value:
                        if a * b == 0:
                            break
                        else:
                            backed_up = True
                else:
                    if backed_up:
                        backups.append((i, j))
                    else:
                        candidates.append((i, j))
        if not candidates:
            candidates = backups
        unit.x, unit.y = random.choice(candidates)
        unit.fix_facing(mymap)
        mymap.set_occupied(unit.x, unit.y)

    try:
        len(before)
    except TypeError:
        before = [before]
    for b in before:
        before_event = EncounterObject.get(b)
        before_event.following = 0x81
        before_event.next_scene = new_enc.scenario


def mutate_treasure():
    print "Mutating treasure."
    units = get_units()
    for u in units:
        u.mutate_trophy()

    poaches = get_poaches()
    for p in poaches:
        p.mutate()

    move_finds = get_move_finds()
    for mf in move_finds:
        mf.mutate()


def mutate_shops():
    print "Mutating shop item availability."
    items = get_items()
    for i in items:
        i.mutate_shop()


def get_similar_item(base_item, same_type=False, same_equip=False,
                     boost_factor=1.0):
    if isinstance(base_item, int):
        base_item = get_item(base_item)
    items = get_ranked_items()
    if same_type:
        items = [i for i in items if i.itemtype == base_item.itemtype]
    if same_equip:
        items = [i for i in items if i.misc1 & 0xF8 == base_item.misc1 & 0xF8]

    index = items.index(base_item)
    reverse_index = len(items) - index - 1
    boost_index = int(round(reverse_index / boost_factor))
    boost_index = max(0, min(boost_index, len(items)-1))
    a, b = min(boost_index, reverse_index), max(boost_index, reverse_index)
    reverse_index = randint(a, b)
    index = len(items) - reverse_index - 1
    index = mutate_normal(index, maximum=len(items)-1)
    replace_item = items[index]
    return replace_item


def setup_fiesta(filename):
    if JAPANESE_MODE:
        return
    f = open(filename, 'r+b')
    f.seek(0x62978)
    f.write("".join([chr(i) for i in [0x88, 0x33, 0x44, 0x43, 0x44,
                                      0x43, 0x44, 0x00, 0x00, 0x00]]))
    f.seek(0x56894)
    f.write(chr(0x5d))  # Make Ramza a mime
    f.seek(0x568B0)
    f.write(chr(0x5d))  # Make Ramza a mime
    #f.seek(0x56984)
    #f.write(chr(0xff))  # unlock jobs?
    #f.seek(0x56a7c)
    #f.write(chr(0xff))  # unlock jobs?
    f.close()

    units = sorted(mapunits[0x188], key=lambda u: u.index)
    funits = [u for u in units if u.index in
              [0x1880, 0x1882, 0x1883, 0x1884, 0x1885]]
    nunits = [u for u in units if u not in funits]
    for u in units:
        u.secondary = 0
        for attr in ["reaction", "support", "movement"]:
            setattr(u, attr, 0x1FF)

    for f in funits:
        f.unlocked = 0x13  # mime
        f.unlocked_level = 1
        for attr in ["lefthand", "head", "body", "accessory"]:
            setattr(f, attr, 0xFE)
        u.righthand = 0x49

    specs = [("ramza", 0x5d, 69, 69),
             ("male", 0x5d, 70, 40),
             ("female", 0x5d, 70, 40),
             ("male", 0x5d, 70, 70),
             ("female", 0x5d, 70, 70)]

    assert len(funits) == len(specs)
    for f, (gender, job, brave, faith) in zip(funits, specs):
        if gender == "male":
            f.set_bit("male", True)
            f.set_bit("female", False)
            f.graphic = 0x80
        elif gender == "female":
            f.set_bit("male", False)
            f.set_bit("female", True)
            f.graphic = 0x81
        elif gender == "ramza":
            f.set_bit("male", True)
            f.set_bit("female", False)
            f.graphic = 0x01
        f.job = job
        f.brave = brave
        f.faith = faith

    #blank_unit = get_unit(0x001d)
    for n in nunits:
        if n.index > 0x1887:
            continue
        n.unlocked = 0
        n.unlocked_level = 1
        n.righthand = 0x49  # stone gun
        for attr in ["lefthand", "head", "body", "accessory"]:
            setattr(n, attr, 0xFF)

    for u in set(mapunits[0x183]) | set(mapunits[0x184]):
        if u.get_bit("enemy_team"):
            u.righthand = 0x49


def disable_random_battles(filename):
    if JAPANESE_MODE:
        #  0xa2fcc78
        raise NotImplementedError
    f = open(filename, 'r+b')
    '''
    f.seek(0xa44bf0a)
    f.write(chr(0))
    '''
    # credit to Xifanie of ffhacktics for this "Smart Encounters" patch
    # http://ffhacktics.com/smf/index.php?topic=953.msg189610#msg189610
    f.seek(0xa44c988)
    f.write("".join([chr(b) for b in [
        0x0D, 0x80, 0x03, 0x3c, 0x80, 0x0b, 0x62, 0x8c,
        0x00, 0x00, 0x00, 0x00, 0x7c, 0x0b, 0x63, 0x8c,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x2d, 0x00, 0x43, 0x14,
        ]]))
    f.close()


def free_soldier_office(filename):
    if JAPANESE_MODE:
        raise NotImplementedError
    f = open(filename, "r+b")
    f.seek(0xA4EAC58)
    write_multi(f, 0, length=2)
    f.seek(0xA4EB68C)
    write_multi(f, 0, length=2)
    f.seek(0xA4EB698)
    write_multi(f, 0, length=2)
    s = "".join([chr(0xFF)] * 7)
    f.seek(0x5B111)
    f.write(s)
    f.seek(0x5B11D)
    f.write(s)
    f.close()


def auto_mash(filename):
    if JAPANESE_MODE:
        raise NotImplementedError
    f = open(filename, "r+b")
    for line in open(MESSAGESFILE):
        line = line.strip()
        if not line or line[0] == "#":
            continue
        pointer = int(line.split()[0], 0x10)
        f.seek(pointer+2)
        c = ord(f.read(1))
        f.seek(pointer+2)
        f.write(chr(c & 0x8F))
    f.close()


def get_jobtree_str():
    jobreqs = JobReqObject.every
    jobreqs = sorted(jobreqs, key=lambda j: j.total_levels)
    jobtree = {}
    for j in jobreqs:
        jobtree[j] = set([])

    categorized = set([])
    for j in jobreqs:
        chosen = None
        for j2 in jobreqs:
            if j2 < j and getattr(j, j2.name) > 0:
                if j2.name in ["dancer", "bard"]:
                    continue
                if not chosen or j2 > chosen:
                    chosen = j2
                elif j2 < chosen:
                    pass
                else:
                    chosen = max(
                        [j2, chosen],
                        key=lambda j3: (j3.total_levels + getattr(j, j3.name),
                                        getattr(j, j3.name), j3.index))

        if chosen is not None:
            jobtree[chosen].add(j)
            categorized.add(j)

    def recurse(j):
        s = "%s:" % j.name.upper()
        prereqs, _ = j.get_prereq_dict()
        for key in sorted(jobreq_namedict):
            if key not in prereqs:
                continue
            value = prereqs[key]
            if value > 0:
                s += " %s %s," % (value, key[:3])
        s = s.strip(",")
        s += "\n"
        for j2 in sorted(jobtree[j], key=lambda j3: j3.name):
            s += recurse(j2) + "\n"
        s = s.strip()
        s = s.replace("\n", "\n    ")
        return s

    treestr = ""
    for j in sorted(jobtree.keys(), key=lambda j3: j3.name):
        if j not in categorized:
            treestr += recurse(j) + "\n\n"
    treestr = treestr.strip()
    return treestr


def get_new_names(basenames):
    candnamesdict = {}
    for name in basenames:
        if len(name) not in candnamesdict:
            candnamesdict[len(name)] = []

    def remove_char(line):
        removables = [i for (i, c) in enumerate(line) if i > 0 and c.lower() in "aeiou"]
        i = len(line) - 1
        if i not in removables:
            removables.append(i)
        i = random.choice(removables)
        line = line[:i] + line[i+1:]
        return line

    for line in open(NAMESFILE):
        line = line.replace("_", " ")
        line = line.strip()
        if len(line) not in candnamesdict and " " in line:
            line = line.replace(" ", "")
        if len(line) not in candnamesdict:
            while len(line) not in candnamesdict:
                line = remove_char(line)
                if len(line) == 0:
                    break
            if len(line)-1 in candnamesdict and random.choice([True, False]):
                line = remove_char(line)
        line = line.strip()
        if len(line) in candnamesdict:
            candnamesdict[len(line)].append(line)

    transitions = {}
    randomnames = list(basenames)
    random.shuffle(randomnames)
    for name in randomnames:
        candidates = list(candnamesdict[len(name)])
        if not candidates:
            result = None
        else:
            candidates = candidates[:randint(1, len(candidates))]
            ss = random.choice(candidates)
            candnamesdict[len(name)].remove(ss)
            result = []
            ss = ss.split()
            for s in ss:
                if s == s.lower():
                    s = s[0].upper() + s[1:]
                result += [s]
            result = " ".join(result)
        transitions[name] = result
    data = ""
    for name in basenames:
        if data:
            data += chr(0xFE)
        newname = transitions[name]
        data += name_to_bytes(newname)
    return data


def get_all_names(filename, pointer=0x3E83C7):
    f = open(filename, "r+b")
    f.seek(pointer)
    seenbytes = []
    names = []
    while True:
        if len(names) == 3 * 256:
            break
        c = ord(f.read(1))
        if c == 0xFE:
            try:
                name = bytes_to_name(seenbytes)
            except KeyError:
                import pdb; pdb.set_trace()
            names.append(name)
            seenbytes = []
        else:
            seenbytes.append(c)
    f.close()
    return names


def replace_generic_names(filename):
    if JAPANESE_MODE:
        return
    names = get_all_names(filename, 0x3e83c7)
    newdata = get_new_names(names)
    for pointer in [0x3e83c7, 0x4d660b, 0xded46b, 0xdeeccf, 0xe0c362]:
        f = open(filename, "r+b")
        f.seek(pointer)
        f.write(newdata)
        f.close()


def randomize():
    global JAPANESE_MODE, JOBLEVEL_JP
    print ('You are using the FFT RUMBLE CHAOS CRASHDOWN randomizer '
           'version "%s".' % VERSION)
    flags, seed = None, None
    if len(argv) >= 2:
        sourcefile = argv[1]
        if len(argv) >= 3:
            if '.' in argv[2]:
                flags, seed = argv[2].split('.')
            else:
                try:
                    seed = int(argv[2])
                except ValueError:
                    flags = argv[2]
            for a in argv:
                if a.lower() == "japanese":
                    JAPANESE_MODE = True

    if len(argv) <= 2:
        print ("NOTICE: This randomizer requires 1 GB of free space "
               "to create a new rom file.\n")
        if len(argv) <= 1:
            print ("Include the filename extension when entering the filename "
                   "of your Final Fantasy Tactics iso.")
            sourcefile = raw_input("Filename? ").strip()
            print

    srchash = get_md5_hash(sourcefile)
    stats = os.stat(sourcefile)
    filesize = stats.st_size
    if srchash in JPMD5HASHES:
        JAPANESE_MODE = True

    if (srchash not in JPMD5HASHES + MD5HASHES + RAWMD5HASHES and
            filesize not in ISO_SIZES + RAW_SIZES):
        filesize = min(ISO_SIZES + RAW_SIZES,
                       key=lambda s: abs(s-filesize))
    if srchash not in JPMD5HASHES + MD5HASHES + RAWMD5HASHES:
        print "WARNING! The file you provided has the following md5 hash: "
        print srchash
        print "\nThis is not a known hash value. See the README."
        resp = raw_input("Continuing might have unexpected results. "
                         "Proceed? (y/n) ")
        if resp and resp[0].lower() == 'y':
            pass
        else:
            sys.exit(0)
        resp = raw_input("\nTreat this rom as the Japanese version? (y/n) ")
        if resp and resp[0].lower() == 'y':
            JAPANESE_MODE = True

    if len(argv) >= 4:
        difficulty = float(argv[3])
    else:
        difficulty = 1.0

    if len(argv) <= 2:
        print ("u  Randomize enemy and ally units.\n"
               "f  Randomize enemy and ally formations.\n"
               "j  Randomize job stats and JP required for skills.\n"
               "i  Randomize innate properties of jobs.\n"
               "s  Randomize job skillsets.\n"
               "a  Randomize abilities, including CT, MP cost, etc.\n"
               "y  Randomize ability and weapon status effects.\n"
               "r  Randomize job requirements and job level JP.\n"
               "t  Randomize trophies, poaches, and move-find items.\n"
               "p  Randomize item prices and shop availability.\n"
               "w  Randomize weapon and item stats.\n"
               "m  Randomize monster stats and skills.\n"
               "c  Randomize battle music.\n"
               "z  Enable special surprises.\n"
               "o  Enable autoplay cutscenes.\n")
        flags = raw_input("Flags? (blank for all) ").strip()
        seed = raw_input("Seed? (blank for random) ").strip()
        print "\nYou can adjust the difficulty of this randomizer."
        difficulty = raw_input("CHAOS MULTIPLIER? (default: 1.0) ").strip()
        if difficulty:
            difficulty = float(difficulty)
        else:
            difficulty = 1.0
        print

    set_difficulty_factors(difficulty)

    if seed:
        seed = int(seed)
    else:
        seed = int(time())
    seed = seed % (10**10)
    random.seed(seed)
    print "Using seed: %s.%s\n" % (flags, seed)
    if flags:
        newsource = "fft_rcc.%s.%s.iso" % (flags, seed)
    else:
        newsource = "fft_rcc.%s.iso" % seed

    if filesize in RAW_SIZES:
        newsource = newsource[:-3] + "bin"

    secret_codes = {}
    secret_codes['fiesta'] = "JOB FIESTA MODE"
    secret_codes['easymodo'] = "EASY MODE"
    activated_codes = set([])
    for key in secret_codes.keys():
        if key in flags:
            flags = flags.replace(key, '')
            print "SECRET CODE: %s ACTIVATED" % secret_codes[key]
            activated_codes.add(key)

    if not flags:
        flags = lowercase

    print "COPYING ROM IMAGE"
    copyfile(sourcefile, newsource)
    sourcefile = newsource

    assert filesize in ISO_SIZES + RAW_SIZES
    if filesize in ISO_SIZES:
        remove_sector_metadata(sourcefile, TEMPFILE)
    else:
        copyfile(sourcefile, TEMPFILE)

    set_global_table_filename(TEMPFILE)

    if JAPANESE_MODE:
        set_table_specs("tables_list_jp.txt")
        JOBLEVEL_JP = [100, 200, 400, 700, 1100, 1600, 2200, 3000]
    else:
        JOBLEVEL_JP = [100, 200, 350, 550, 800, 1150, 1550, 2100]

    print "Reading game data."
    all_objects = [g for g in globals().values()
                   if isinstance(g, type) and issubclass(g, TableObject)
                   and g is not TableObject]
    for ao in all_objects:
        ao.every

    get_jobreqs()
    sort_mapunits()
    make_rankings()

    if 'r' in flags:
        # before units
        random.seed(seed)
        mutate_job_level(TEMPFILE)
        for u in get_units():
            u.set_backup_jp_total()
        mutate_job_requirements()

    for req in get_jobreqs():
        req.set_required_unlock_jp()

    if 'r' in flags:
        s = get_jobtree_str()
        f = open("%s.txt" % seed, "w+")
        f.write(s)
        f.close()
        del(f)

    if 'i' in flags:
        # before units
        random.seed(seed)
        mutate_job_innates()

    if 's' in flags:
        random.seed(seed)
        mutate_skillsets()

    if 'a' in flags:
        # do after randomizing skillsets
        random.seed(seed)
        mutate_abilities_attributes()

    if 'y' in flags:
        random.seed(seed)
        mutate_inflict_status()

    if 'j' in flags:
        # do after randomizing skillsets
        random.seed(seed)
        mutate_job_stats()

    if 'm' in flags:
        # before units
        random.seed(seed)
        mutate_monsters()

    if 'u' in flags:
        # do after randomizing skillsets
        random.seed(seed)
        mutate_units()

    if 'z' in flags:
        # do after randomizing skillsets
        random.seed(seed)
        mutate_units_special()
        randomize_ending(TEMPFILE)
        replace_generic_names(TEMPFILE)
        for e in EncounterObject.every:
            e.randomize_weather()

    if 'z' in flags and 'f' in flags:
        random.seed(seed)
        encs = EncounterObject.get_replaceable_maps()
        half = len(encs) / 2
        sampsize = randint(1, half)
        sampsize = randint(sampsize, half)
        encs = random.sample(encs, sampsize)
        for e in encs:
            e.mutate_map()

    if 'f' in flags:
        print "Randomizing formations."
        random.seed(seed)
        fs = [f for f in FormationObject.every
              if f.bitmap and f.num_characters]
        for i, f in enumerate(fs):
            f.mutate()
        random.seed(seed)
        es = [e for e in EncounterObject.every
              if e.map_id and e.entd and e.event and e.grid]
        for i, e in enumerate(es):
            while True:
                result = e.generate_formations()
                if result or not e.mutated:
                    break
        randomize_enemy_formations()

    if 't' in flags:
        random.seed(seed)
        mutate_treasure()

    if 'p' in flags:
        random.seed(seed)
        mutate_shops()

    if 'w' in flags:
        random.seed(seed)
        mutate_items_and_weapons()

    if 'c' in flags:
        random.seed(seed)
        print "Randomizing music."
        for e in EncounterObject.every:
            e.randomize_music()

    if 'z' in flags:
        # aeris @ zarghidas: 1ca or 1cb
        first = random.choice([True, False])
        second = not first
        restore_warjilis(TEMPFILE, before=0xab, new_entd=0x1dc,
                         map_id=42, monsters=first)
        restore_warjilis(TEMPFILE, before=[0x1c1, 0x1c2], new_entd=0x1dd,
                         map_id=33, monsters=second)
        altima1 = JobObject.get(0x41)
        altima1.skillset = 0x7B

    if 'o' in flags:
        try:
            auto_mash(TEMPFILE)
        except NotImplementedError:
            pass

    if set(flags) & set("rujimtpsazfyw"):
        random.seed(seed)
        for unit_id in [0x1951, 0x19d0, 0x1a10, 0x1ac0, 0x1b10]:
            u = get_unit(unit_id)
            u.normalize_level(randint(1, 3))

        # make Orbonne controllable
        for u in sorted(mapunits[0x183], key=lambda u: u.index):
            if not u.get_bit("enemy_team"):
                u.set_bit("control", True)

        try:
            disable_random_battles(TEMPFILE)
            free_soldier_office(TEMPFILE)
        except NotImplementedError:
            pass

    if "fiesta" in activated_codes:
        setup_fiesta(TEMPFILE)

    if "easymodo" in activated_codes:
        for u in UnitObject:
            if u.get_bit("enemy_team"):
                u.level = 1

    DOUBLE_SUPER = set(SUPER_LEVEL_BOOSTED) & set(SUPER_SPECIAL)

    print "WRITING MUTATED DATA"
    for ao in all_objects:
        print "Writing %s data." % ao.__name__
        for obj in ao.every:
            obj.write_data()

    #unlock_jobs(TEMPFILE)
    diffstr = str(difficulty)
    if len(diffstr) > 10:
        diffstr = diffstr[:9] + "?"
    rewrite_header(TEMPFILE, "FFT RCC %s %s %s" % (VERSION, seed, diffstr))

    assert filesize in RAW_SIZES + ISO_SIZES
    if filesize in ISO_SIZES:
        inject_logical_sectors(TEMPFILE, sourcefile)
    else:
        copyfile(TEMPFILE, sourcefile)

    remove(TEMPFILE)
    print "Output file has hash: %s" % get_md5_hash(sourcefile)

    if len(argv) <= 2:
        raw_input("\nRandomization completed successfully. "
                  "\nOutput filename: %s"
                  "\nPress enter to close this program. " % sourcefile)

if __name__ == "__main__":
    if "test" in argv:
        randomize()
    else:
        try:
            randomize()
        except Exception, e:
            print "ERROR: %s %s" % (e.__class__.__name__, e)
            raw_input("Press enter to quit. ")
