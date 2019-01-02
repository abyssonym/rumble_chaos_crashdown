from os import path
from randomtools.tablereader import tblpath

bin_offsets = {}
alt_filenames = {}

for line in open(path.join(tblpath, "binfile_offsets.txt")):
    line = line.strip()
    if not line or line[0] == '#':
        continue
    while '  ' in line:
        line = line.replace('  ', ' ')

    filename, alt_filename, offset = line.split()
    offset = int(offset, 0x10)
    bin_offsets[filename] = offset
    alt_filenames[filename] = alt_filename


def patch_patch(filename, patchdict, verify=False, compare_offsets=False):
    if 'varvals' not in patchdict:
        varvals = {}
    else:
        varvals = patchdict['varvals']

    if not (verify or compare_offsets):
        print "APPLYING PATCH: %s" % patchdict['name']
    elif verify:
        print "VERIFYING PATCH: %s" % patchdict['name']

    for location in patchdict['locations'] + patchdict['variables']:
        binfile = location['file']
        bin_offset = bin_offsets[binfile]
        offset = location['offset'] + bin_offset

        length = (location['bytes'] if 'bytes' in location
                  else len(location['data']))

        if 'bytes' in location:
            length = location['bytes']
            if location['name'] in varvals:
                value = varvals[location['name']]
            elif 'default' in location:
                value = location['default']
            else:
                raise Exception("No value given for variable: %s %s" %
                                (patchdict['name'], location['name']))
            if not (verify or compare_offsets):
                print '-- VARIABLE:', location['name'], value
            to_write = ''
            while len(to_write) < length:
                to_write = chr(value & 0xff) + to_write
                value >>= 8
            assert len(to_write) == length
        else:
            to_write = location['data']
            length = len(to_write)

        to_patch = open(filename, 'r+b')
        to_patch.seek(offset)

        if compare_offsets:
            compare_filename = alt_filenames[binfile]
            compare_filename = path.join('sandbox', compare_filename)
            print filename, hex(offset)
            print compare_filename, hex(location['offset'])
            to_compare = open(compare_filename, 'r+b')
            to_compare.seek(location['offset'])
            patch_data = to_patch.read(length)
            compare_data = to_compare.read(length)
            print patch_data == compare_data
            assert patch_data == compare_data
            to_compare.close()

        if verify:
            patched_data = to_patch.read(length)
            if patched_data != to_write:
                raise Exception("Verification failed: %s %s"
                                % (patchdict['name'], location['offset']))

        if not (compare_offsets or verify):
            to_patch.write(to_write)
        to_patch.close()
