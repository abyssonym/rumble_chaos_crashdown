from os import path
from sys import argv
from xml.etree import ElementTree


def text_to_bytecode(text):
    text = ''.join(text.strip().split())
    assert not (len(text) % 2)
    pairs = [a + b for (a, b) in zip(text[::2], text[1::2])]
    assert len(pairs) == len(text) / 2.0
    return ''.join([chr(int(p, 0x10)) for p in pairs])


def get_patchdicts(filename):
    tree = ElementTree.parse(filename)
    assert tree.getroot().tag == 'Patches'
    patches = [n for n in tree.getroot()]
    patchdicts = []
    for patch in patches:
        is_asm_patch = False
        patchdict = {}
        patchdict['filename'] = filename
        patchdict['locations'] = []
        patchdict['variables'] = []
        for key, value in patch.items():
            assert key == 'name'
            patchdict['name'] = value
        assert patch.tag == 'Patch'
        for node in patch:
            if node.tag == 'Location':
                locdict = {}
                for key, value in node.items():
                    assert key in {'file', 'offset', 'mode',
                                   'offsetMode', 'inputFile'}
                    assert key not in locdict
                    locdict[key] = value
                locdict['offset'] = int(locdict['offset'], 0x10)
                if 'mode' not in locdict:
                    locdict['mode'] = 'DATA'
                assert locdict['mode'] in {'DATA', 'ASM'}
                if locdict['mode'] == 'DATA':
                    locdict['data'] = text_to_bytecode(node.text)
                if locdict['mode'] == 'ASM' or 'offsetMode' in locdict:
                    is_asm_patch = True
                patchdict['locations'].append(locdict)
            elif node.tag == 'Description':
                assert 'description' not in patchdict
                patchdict['description'] = node.text.strip()
            elif node.tag == 'Variable':
                assert node.text is None
                vardict = {}
                for key, value in node.items():
                    assert key in {'name', 'file', 'offset', 'default',
                                   'bytes'}
                    assert key not in vardict
                    if key in {'offset', 'default'}:
                        vardict[key] = int(value, 0x10)
                    elif key in {'bytes'}:
                        vardict[key] = int(value)
                    else:
                        vardict[key] = value
                if 'bytes' not in vardict:
                    vardict['bytes'] = 1
                patchdict['variables'].append(vardict)
            else:
                assert False
        if not is_asm_patch:
            patchdicts.append(patchdict)
    patchdicts = sorted(patchdicts, key=lambda p: p['name'])
    assert len(patchdicts) == len(set([p['name'] for p in patchdicts]))
    return patchdicts


if __name__ == '__main__':
    from xml_patch_patcher import patch_patch
    for filename in argv[1:]:
        patchdicts = get_patchdicts(filename)
        for p in patchdicts:
            print path.split(filename)[-1], p['name']
            patch_patch('unheadered_na.img', p, compare_offsets=True)
