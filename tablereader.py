from utils import read_multi, write_multi, classproperty, mutate_normal
from os import path
import string


try:
    from sys import _MEIPASS
    tblpath = path.join(_MEIPASS, "tables")
except ImportError:
    tblpath = "tables"


TABLE_SPECS = {}
GLOBAL_FILENAME = None
GRAND_OBJECT_DICT = {}


def set_global_table_filename(filename):
    global GLOBAL_FILENAME
    GLOBAL_FILENAME = filename


class TableSpecs:
    def __init__(self, specfile, pointer=None, count=None, grouped=False):
        self.attributes = []
        self.bitnames = {}
        self.total_size = 0
        self.pointer = pointer
        self.count = count
        self.grouped = grouped
        for line in open(specfile):
            line = line.strip()
            if not line or line[0] == "#":
                continue
            line = line.strip().split(',')
            if len(line) == 2:
                name, size, other = line[0], line[1], None
            elif len(line) == 3:
                name, size, other = tuple(line)

            if size[:3] == "bit":
                size, bitnames = tuple(size.split(':'))
                size = 1
                bitnames = bitnames.split(" ")
                self.bitnames[name] = bitnames

            size = int(size)
            self.attributes.append((name, size, other))
            self.total_size += size


class TableObject(object):
    class __metaclass__(type):
        def __iter__(self):
            for obj in self.ranked:
                yield obj

    def __init__(self, filename=None, pointer=None):
        assert hasattr(self, "specs")
        assert self.total_size
        self.filename = filename
        self.pointer = pointer
        if filename:
            self.read_data(filename, pointer)

    @classproperty
    def specs(cls):
        return TABLE_SPECS[cls.__name__]

    @classproperty
    def specsattrs(cls):
        return cls.specs.attributes

    @classproperty
    def specspointer(cls):
        return cls.specs.pointer

    @classproperty
    def specscount(cls):
        return cls.specs.count

    @classproperty
    def specsgrouped(cls):
        return cls.specs.grouped

    @classproperty
    def bitnames(cls):
        return cls.specs.bitnames

    @classproperty
    def total_size(cls):
        return cls.specs.total_size

    @classproperty
    def every(cls):
        return get_table_objects(cls, filename=GLOBAL_FILENAME)

    @property
    def rank(self):
        return self.index

    @property
    def catalogue_index(self):
        return self.index

    @classproperty
    def ranked(cls):
        return sorted(cls.every, key=lambda c: (c.rank, c.index))

    def get_similar(self):
        if self.rank < 0:
            return self
        candidates = [c for c in self.ranked if c.rank >= 0]
        index = candidates.index(self)
        index = mutate_normal(index, maximum=len(candidates)-1)
        return candidates[index]

    @classmethod
    def get(cls, index):
        if isinstance(index, int):
            return GRAND_OBJECT_DICT[cls, index]
        elif isinstance(index, str) or isinstance(index, unicode):
            objs = [o for o in cls.every if index in o.name]
            if len(objs) == 1:
                return objs[0]
            elif len(objs) >= 2:
                raise Exception("Too many matching objects.")
            else:
                raise Exception("No matching objects.")
        else:
            raise Exception("Bad index.")

    @classmethod
    def has(cls, index):
        try:
            cls.get(index)
            return True
        except KeyError:
            return False

    def get_bit(self, bitname):
        for key, value in sorted(self.bitnames.items()):
            if bitname in value:
                index = value.index(bitname)
                byte = getattr(self, key)
                bitvalue = byte & (1 << index)
                return bool(bitvalue)
        raise Exception("No bit registered under that name.")

    def set_bit(self, bitname, bitvalue):
        bitvalue = 1 if bitvalue else 0
        for key, value in self.bitnames.items():
            if bitname in value:
                index = value.index(bitname)
                byte = getattr(self, key)
                if bitvalue:
                    byte = byte | (1 << index)
                else:
                    byte = byte & (0xFF ^ (1 << index))
                setattr(self, key, byte)
                return
        raise Exception("No bit registered under that name.")

    @property
    def display_name(self):
        if not hasattr(self, "name"):
            self.name = "%x" % self.index
        if isinstance(self.name, int):
            return "%x" % self.name
        return "".join([c for c in self.name if c in string.printable])

    @property
    def description(self):
        classname = self.__class__.__name__
        pointer = "%x" % self.pointer if self.pointer else "None"
        desc = "{0} {1:02x} {2} {3}".format(
            classname, self.index, pointer, self.display_name)
        return desc

    @property
    def long_description(self):
        s = []
        for attr in sorted(dir(self)):
            if attr.startswith('_'):
                continue

            if attr == "specs":
                continue

            if hasattr(self.__class__, attr):
                class_attr = getattr(self.__class__, attr)
                if (isinstance(class_attr, property)
                        or hasattr(class_attr, "__call__")):
                    continue

            value = getattr(self, attr)
            if isinstance(value, dict):
                continue

            if isinstance(value, list):
                if value and not isinstance(value[0], int):
                    continue
                value = " ".join(["%x" % v for v in value])

            if isinstance(value, int):
                value = "%x" % value

            s.append((attr, "%s" % value))
        s = ", ".join(["%s: %s" % (a, b) for (a, b) in s])
        s = "%x - %s" % (self.index, s)
        return s

    @classproperty
    def catalogue(self):
        logs = []
        for obj in sorted(self.every, key=lambda o: o.catalogue_index):
            logs.append(obj.log.strip())

        if any(["\n" in log for log in logs]):
            return "\n\n".join(logs)
        else:
            return "\n".join(logs)

    @property
    def log(self):
        return str(self)

    def __repr__(self):
        return self.description

    def read_data(self, filename=None, pointer=None):
        if pointer is None:
            pointer = self.pointer
        if filename is None:
            filename = self.filename
        if pointer is None or filename is None:
            return
        f = open(filename, 'r+b')
        f.seek(pointer)
        for name, size, other in self.specsattrs:
            if other in [None, "int"]:
                value = read_multi(f, length=size)
            elif other == "str":
                value = f.read(size)
            elif other == "list":
                value = f.read(size)
                value = map(ord, value)
            setattr(self, name, value)
        f.close()

    def copy_data(self, another):
        for name, _, _ in self.specsattrs:
            if name in ["filename", "pointer", "index"]:
                continue
            value = getattr(another, name)
            setattr(self, name, value)

    def write_data(self, filename=None, pointer=None):
        if pointer is None:
            pointer = self.pointer
        if filename is None:
            filename = self.filename
        if pointer is None or filename is None:
            return
        f = open(filename, 'r+b')
        f.seek(pointer)
        for name, size, other in self.specsattrs:
            value = getattr(self, name)
            if other in [None, "int"]:
                write_multi(f, value, length=size)
            elif other == "str":
                assert len(value) == size
                f.write(value)
            elif other == "list":
                for v in value:
                    f.write(chr(v))
        f.close()


already_gotten = {}


def get_table_objects(objtype, filename=None):
    pointer = objtype.specspointer
    number = objtype.specscount
    grouped = objtype.specsgrouped
    identifier = (objtype, pointer, number)
    if identifier in already_gotten:
        return already_gotten[identifier]

    objects = []

    def add_objects(n):
        p = pointer
        accumulated_size = 0
        for i in xrange(n):
            obj = objtype(filename, p)
            obj.index = len(objects)
            objects.append(obj)
            p += obj.total_size
            accumulated_size += obj.total_size
        return accumulated_size

    if not grouped:
        add_objects(number)
    else:
        while len(objects) < number:
            f = open(filename, 'r+b')
            f.seek(pointer)
            value = ord(f.read(1))
            f.close()
            pointer += 1
            pointer += add_objects(value)
    already_gotten[identifier] = objects

    for o in objects:
        GRAND_OBJECT_DICT[objtype, o.index] = o

    return get_table_objects(objtype, filename=filename)


def set_table_specs(filename="tables_list.txt"):
    tablesfile = path.join(tblpath, filename)
    for line in open(tablesfile):
        line = line.strip()
        if line and line[0] == "#":
            continue

        while "  " in line:
            line = line.replace("  ", " ")
        line = line.split()
        if len(line) == 5:
            objname, tablefilename, pointer, count, grouped = tuple(line)
            grouped = True if grouped.lower() == "true" else False
        else:
            objname, tablefilename, pointer, count = tuple(line)
            grouped = False
        pointer = int(pointer, 0x10)
        count = int(count)
        TABLE_SPECS[objname] = TableSpecs(path.join(tblpath, tablefilename),
                                          pointer, count, grouped)

set_table_specs()
