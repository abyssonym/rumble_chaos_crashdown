from shutil import copyfile
from os import remove


def remove_sector_metadata(sourcefile, outfile):
    # playstation discs are CD-ROM XA mode 2 (form 1 for data)
    print "REMOVING SECTOR METADATA"
    copyfile(sourcefile, outfile)
    f = open(sourcefile, 'r+b')
    g = open(outfile, 'r+b')
    g.truncate()
    while True:
        header = f.read(0x18)
        data = f.read(0x800)
        if len(data) < 0x800:
            break
        #g.write(header)
        g.write(data)
        #g.write("".join([chr(0) for _ in xrange(0x118)]))
        checkdata = f.read(4)
        '''
        checksum = crc32(data)
        if checksum < 0:
            checksum += (1 << 32)
        '''
        f.seek(0x114, 1)
    f.close()
    g.close()


def inject_logical_sectors(sourcefile, outfile):
    print "REINJECTING LOGICAL SECTORS TO ORIGINAL ISO"
    f = open(sourcefile, 'r+b')
    g = open(outfile, 'r+b')
    minpointer, maxpointer = None, None
    num_changed_sectors = 0
    while True:
        pointer_source = f.tell()
        pointer_dest = g.tell()
        data_source = f.read(0x800)
        header = g.read(0x18)
        data_dest = g.read(0x800)
        checkdata = g.read(0x118)
        if (len(data_source) == len(header) == len(data_dest)
                == len(checkdata) == 0):
            break
        if not all([len(data_source) == 0x800,
                    len(header) == 0x18,
                    len(data_dest) == 0x800,
                    len(checkdata) == 0x118]):
            import pdb; pdb.set_trace()
            raise Exception("Data alignment mismatch.")
        if data_source == data_dest:
            continue
        else:
            #print "%x %x CHANGED" % (pointer_source, pointer_dest)
            if minpointer is None:
                minpointer = pointer_dest
            maxpointer = max(pointer_dest + 0x800, maxpointer)
            num_changed_sectors += 1
            # gotta do this dumb file seeking thing for windows
            g.seek(pointer_dest)
            g.write(header)
            g.seek(pointer_dest + len(header))
            g.write(data_source)
            g.seek(pointer_dest + len(header) + len(data_source))
            g.write("".join([chr(0) for _ in range(0x118)]))
            g.seek(pointer_dest + len(header) + len(data_source) + 0x118)

    if minpointer is not None and maxpointer is not None:
        print "%s SECTORS CHANGED IN RANGE %x-%x" % (
            num_changed_sectors, minpointer, maxpointer)
    else:
        print "NO CHANGES MADE TO ISO"


if __name__ == "__main__":
    from sys import argv
    SOURCE = argv[1]
    TEMPFILE = "unheadered.img"
    remove_sector_metadata(SOURCE, TEMPFILE)
    #inject_logical_sectors(TEMPFILE, SOURCE)
    #remove(TEMPFILE)
