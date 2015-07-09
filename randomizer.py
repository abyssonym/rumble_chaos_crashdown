from shutil import copyfile
from os import remove
from sys import argv

from utils import TABLE_SPECS, mutate_index, utilrandom as random
from tablereader import TableSpecs, TableObject, get_table_objects
from uniso import remove_sector_metadata, inject_logical_sectors

unit_specs = TableSpecs(TABLE_SPECS['unit'])
job_specs = TableSpecs(TABLE_SPECS['job'])
job_reqs_specs = TableSpecs(TABLE_SPECS['job_reqs'])


jobreq_namedict = {}
jobreq_indexdict = {}
JOBNAMES = ["squire", "chemist", "knight", "archer", "monk", "priest",
            "wizard", "timemage", "summoner", "thief", "mediator", "oracle",
            "geomancer", "lancer", "samurai", "ninja", "calculator", "bard",
            "dancer", "mime"]
JOBLEVEL_JP = [100, 200, 350, 550, 800, 1150, 1550, 2100]


mapsprite_restrictions = {}
mapsprite_selection = {}
mapunits = {}
mapsprites = {}
named_jobs = {}
named_map_jobs = {}
rankdict = None


def calculate_jp_total(joblevels):
    total = 0
    for j in joblevels:
        if j == 0:
            continue
        total += JOBLEVEL_JP[j-1]
    return total


TEMPFILE = "_fftrandom.tmp"


class JobObject(TableObject):
    specs = job_specs.specs
    bitnames = job_specs.bitnames
    total_size = job_specs.total_size


class UnitObject(TableObject):
    specs = unit_specs.specs
    bitnames = unit_specs.bitnames
    total_size = unit_specs.total_size

    @property
    def map_id(self):
        return self.index >> 4

    @property
    def has_special_graphic(self):
        return self.graphic not in [0x80, 0x81, 0x82]

    @property
    def named(self):
        return bool(self.name != 0xFF)

    @property
    def level_normalized(self):
        return self.level >= 100 or self.level == 0

    @property
    def jp_total(self):
        if self.job in jobreq_indexdict:
            base_job = jobreq_indexdict[self.job]
        else:
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

    def mutate_secondary(self, base_job=None, jp_remaining=None,
                         boost_factor=1.2):
        if base_job is None:
            job = self.job
            if job in jobreq_indexdict:
                base_job = jobreq_indexdict[job]
            else:
                base_job = None

        if jp_remaining is None:
            jp_remaining = self.jp_total
            jp_remaining = random.randint(jp_remaining,
                                          int(jp_remaining * boost_factor))

        jobs = jobreq_namedict.values()
        jobs = [j for j in jobs if j.required_unlock_jp <= jp_remaining]
        if base_job is not None:
            if (random.randint(1, 5) != 5 and base_job.otherindex > 0):
                base_name = base_job.name
                jobs = [j for j in jobs if getattr(j, base_name) > 0
                        or j == base_job]
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
            if random.choice([True, False]):
                jobs = jobs[len(jobs)/2:]
            unlocked_job = random.choice(jobs)

        jp_remaining -= required_jp
        unlocked_level = len([j for j in JOBLEVEL_JP if j <= jp_remaining])
        if random.choice([True, False]):
            unlocked_level += 1
        while random.randint(1, 7) == 7:
            unlocked_level += 1

        unlocked_level = min(unlocked_level, 8)
        self.unlocked = unlocked_job.otherindex
        self.unlocked_level = unlocked_level

        #if self.secondary > 0x18:
        #    return

        if random.randint(1, 10) == 10:
            candidates = get_ranked("secondary")
            base = get_job(self.job).skillset
            if self.secondary in candidates:
                base = random.choice([base, self.secondary])
            index = candidates.index(base)
            candidates.remove(base)
            index = max(index-1, 0)
            index = mutate_index(index, len(candidates), [True, False],
                                 (-4, 5), (-2, 3))
            self.secondary = candidates[index]
        elif (unlocked_job != base_job and unlocked_level > 1
                and random.randint(1, 3) != 3):
            assert unlocked_job.otherindex in range(0x4A, 0x5E)
            self.secondary = unlocked_job.otherindex + 5
        elif self.secondary != 0 or random.choice([True, False]):
            self.secondary = 0xFE

        return True

    def mutate_job(self, boost_factor=1.2, preserve_gender=False):
        if self.job not in jobreq_indexdict:
            success = self.mutate_secondary()
            return success

        jp_remaining = self.jp_total
        jp_remaining = random.randint(jp_remaining,
                                      int(jp_remaining * boost_factor))

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
            try:
                if gender == "male":
                    assert male_sel or len(selection) < generic_r
                elif gender == "female":
                    assert female_sel or len(selection) < generic_r
            except:
                import pdb; pdb.set_trace()

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

            cands = [j for j in jobs if j not in done_jobs]
            if not cands:
                cands = jobs

            if gender == "male":
                cands = [c for c in cands if c.name != "dancer"]
            elif gender == "female":
                cands = [c for c in cands if c.name != "bard"]

            if cands:
                cands = sorted(cands, key=lambda j: j.required_unlock_jp)
                if random.choice([True, False]):
                    cands = cands[len(cands)/2:]
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
                try:
                    assert named_jobs[(self.name, self.job)] == base_job
                except:
                    import pdb; pdb.set_trace()
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

        for attr in ["reaction", "support", "movement"]:
            if random.choice([True, False]):
                setattr(self, attr, 0x1FE)

        for attr in ["lefthand", "righthand", "head", "body", "accessory"]:
            if random.choice([True, False]):
                setattr(self, attr, 0xFE)

        if gender == "male":
            self.set_bit("male", True)
            self.set_bit("female", False)
            self.graphic = 0x80
        elif gender == "female":
            self.set_bit("female", True)
            self.set_bit("male", False)
            self.graphic = 0x81

        self.mutate_secondary()

        return True


class JobReqObject(TableObject):
    specs = job_reqs_specs.specs
    bitnames = job_reqs_specs.bitnames
    total_size = job_reqs_specs.total_size

    @property
    def required_unlock_jp(self):
        self.remax_jobreqs()

        joblevels = []
        for name in JOBNAMES:
            level = getattr(self, name)
            if level:
                joblevels.append(level)
        total = calculate_jp_total(joblevels)

        return total

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
    return get_table_objects(UnitObject, 0x75e0800, 512*16, filename)


def get_unit(index):
    return [u for u in get_units() if u.index == index][0]


def get_jobs(filename=None):
    jobs = get_table_objects(JobObject, 0x5d8b8, 160, filename)
    for j in jobs:
        if j.index in range(0x4A, 0x5E):
            j.name = JOBNAMES[j.index - 0x4A]
        else:
            j.name = "%x" % j.index
    return jobs


def get_job(index):
    return [j for j in get_jobs() if j.index == index][0]


def get_jobreqs(filename=None):
    jobreqs = get_table_objects(JobReqObject, 0x628c4, 19, filename)
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
    return jobreqs


def unlock_jobs(outfile):
    f = open(outfile, 'r+b')
    f.seek(0x5a4f4)
    f.write("".join([chr(0) for _ in xrange(4)]))
    f.close()


def make_rankings():
    global rankdict
    if rankdict is not None:
        return rankdict

    print "Analyzing and ranking unit data..."
    units = get_units()
    units = [u for u in units if u.graphic != 0]
    units = [u for u in units
             if u.map_id in range(1, 0xFE) + range(0x180, 0x1D5)]
    rankable_features = ["map_id", "unlocked", "unlocked_level",
                         "righthand", "lefthand", "head", "body", "accessory",
                         "job", "secondary", "reaction", "support", "movement",
                         ]
    unrankable_values = [0, 0xFE, 0xFF]
    rankdict = {}
    for i in xrange(100):
        rankdict[("level", i)] = i
    for u in units:
        u.rank = None

    oldstring = ""
    for i in xrange(1000):
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
                u.rank = u.level
            elif rank:
                u.rank = rank

        for key in tempdict:
            ranks = tempdict[key]
            if ranks:
                rank = float(sum(ranks)) / len(ranks)
                rankdict[key] = rank

        codestring = "".join([chr(int(round(u.rank))) for u in units
                              if u.rank is not None])
        #if len(codestring) == len(oldstring):
        if codestring == oldstring:
            break
        oldstring = codestring

    jobs = get_jobs()
    for j in jobs:
        if j.index in range(0x4A, 0x5E):
            if ("job", j.index) not in rankdict:
                rankdict["job", j.index] = 24 + (0.001 * j.index)

        key = ("secondary", j.skillset)
        if key not in rankdict:
            key2 = ("job", j.index)
            if key2 in rankdict:
                rankdict[key] = rankdict[key2]
            else:
                rankdict["secondary", j.skillset] = 24 + (0.001 * j.index)

    return make_rankings()


def get_ranked(category):
    make_rankings()
    ranked = []
    for key in rankdict:
        cat, value = key
        if cat == category:
            ranked.append((rankdict[key], value))
    ranked = sorted(ranked)
    ranked = [b for (a, b) in ranked]
    return ranked


def sort_mapunits():
    units = get_units()
    for u in units:
        if u.map_id not in mapsprites:
            mapsprites[u.map_id] = set([])
            mapunits[u.map_id] = set([])
        mapsprites[u.map_id].add((u.graphic, u.job))
        mapunits[u.map_id].add(u)


def mutate_units():
    units = get_units()
    sort_mapunits()
    for key, value in mapsprites.items():
        generic = len([_ for (g, _) in value if g in (0x80, 0x81)])
        monster = len([_ for (g, _) in value if g == 0x82])
        other = len([_ for (g, _) in value if g not in (0x80, 0x81, 0x82, 0x00)])

        remaining = 9 - (generic + monster + other)
        if remaining > 0 and key in range(0x100, 0x14B):
            # only appropriate for maps you can't assign units to
            generic += remaining

        mapsprite_restrictions[key] = (generic, monster, other)
        mapsprite_selection[key] = set([])

    named_units = {}
    for u in units:
        if u.named and not u.has_special_graphic:
            if u.map_id not in named_units:
                named_units[u.map_id] = []
            named_units[u.map_id].append(u)

    make_rankings()

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
            success = u.mutate_job()
            u.job_mutated = True
            if success:
                u.write_data()

    random.shuffle(units)
    for u in [u for u in units if u.has_special_graphic or not u.named]:
        success = u.mutate_job()
        if success:
            u.write_data()


def setup_fiesta(filename):
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

    sort_mapunits()
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
        for attr in ["righthand", "lefthand", "head", "body", "accessory"]:
            setattr(f, attr, 0xFE)

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

    for u in mapunits[0x183] | mapunits[0x184]:
        if u.get_bit("team1"):
            u.righthand = 0x49
            u.write_data()

    for u in units:
        u.write_data()


if __name__ == "__main__":
    sourcefile = argv[1]
    newsource = "out.img"
    copyfile(sourcefile, newsource)
    sourcefile = newsource

    remove_sector_metadata(sourcefile, TEMPFILE)

    units = get_units(TEMPFILE)
    jobs = get_jobs(TEMPFILE)
    jobreqs = get_jobreqs(TEMPFILE)

    for j in jobs[0x4A:0x5A]:
        print j.long_description
        print

    ''' Unlock all jobs (lowers overall enemy JP)
    for j in jobreqs:
        j.set_zero()
        j.write_data()

    # make Orbonne controllable
    sort_mapunits()
    for u in sorted(mapunits[0x183], key=lambda u: u.index):
        if not u.get_bit("team1"):
            u.set_bit("control", True)
            u.write_data()
    '''

    mutate_units()

    #setup_fiesta(TEMPFILE)
    #unlock_jobs(TEMPFILE)

    inject_logical_sectors(TEMPFILE, sourcefile)
    remove(TEMPFILE)
