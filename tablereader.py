from utils import read_multi, write_multi


class TableSpecs:
    def __init__(self, specfile):
        self.attributes = []
        self.bitnames = {}
        self.total_size = 0
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
    def __init__(self, filename=None, pointer=None):
        assert hasattr(self, "specs")
        assert self.total_size
        self.filename = filename
        self.pointer = pointer
        if filename:
            self.read_data(filename, pointer)

    @property
    def specattrs(self):
        return self.specs.attributes

    @property
    def bitnames(self):
        return self.specs.bitnames

    @property
    def total_size(self):
        return self.specs.total_size

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
        return "".join([c for c in self.name if ord(c) > 0])

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
                value = " ".join(["%x" % v for v in value])

            if isinstance(value, int):
                value = "%x" % value

            s.append((attr, "%s" % value))
        s = ", ".join(["%s: %s" % (a, b) for (a, b) in s])
        return s

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
        for name, size, other in self.specattrs:
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
        for name, _, _ in self.specattrs:
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
        for name, size, other in self.specattrs:
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


def get_table_objects(objtype, pointer, number, filename=None, grouped=False):
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

    return get_table_objects(objtype, pointer, number, filename=filename)
