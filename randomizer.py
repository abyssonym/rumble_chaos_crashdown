from shutil import copyfile
from os import remove
import sys
from sys import argv
from time import time
from string import lowercase

from utils import (TABLE_SPECS, mutate_index, mutate_normal, mutate_bits,
                   write_multi,
                   utilrandom as random)
from tablereader import TableSpecs, TableObject, get_table_objects
from uniso import remove_sector_metadata, inject_logical_sectors

randint = random.randint

VERSION = "1"
MD5HASH = "aefdf27f1cd541ad46b5df794f635f50"

unit_specs = TableSpecs(TABLE_SPECS['unit'])
job_specs = TableSpecs(TABLE_SPECS['job'])
job_reqs_specs = TableSpecs(TABLE_SPECS['job_reqs'])
ss_specs = TableSpecs(TABLE_SPECS['skillset'])
item_specs = TableSpecs(TABLE_SPECS['item'])
monster_skills_specs = TableSpecs(TABLE_SPECS['monster_skills'])
move_find_specs = TableSpecs(TABLE_SPECS['move_find'])
poach_specs = TableSpecs(TABLE_SPECS['poach'])
ability_specs = TableSpecs(TABLE_SPECS['ability'])

VALID_INNATE_STATUSES = 0xCAFCE92A10
VALID_START_STATUSES = VALID_INNATE_STATUSES | 0x3402301000
BANNED_SKILLSET_SHUFFLE = [0, 1, 2, 3, 6, 8, 0x11, 0x12, 0x13, 0x14, 0x15,
                           0x34, 0x38, 0x39, 0x3B, 0x3E, 0x9C]
BANNED_RSMS = [0x1BB, 0x1E1, 0x1E4, 0x1E5, 0x1F1]

jobreq_namedict = {}
jobreq_indexdict = {}
JOBNAMES = ["squire", "chemist", "knight", "archer", "monk", "priest",
            "wizard", "timemage", "summoner", "thief", "mediator", "oracle",
            "geomancer", "lancer", "samurai", "ninja", "calculator", "bard",
            "dancer", "mime"]
JOBLEVEL_JP = [100, 200, 350, 550, 800, 1150, 1550, 2100]


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
    while len(message) < 0x20:
        message += " "
    f = open(filename, 'r+b')
    f.seek(0x8028)
    f.write(message)
    f.close()


TEMPFILE = "_fftrandom.tmp"


class MonsterSkillsObject(TableObject):
    specs = monster_skills_specs

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
            index = mutate_normal(index, maximum=len(candidates)-1, smart=True)
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
    specs = move_find_specs

    @property
    def x(self):
        return self.coordinates >> 4

    @property
    def y(self):
        return self.coordinates & 0xF

    def mutate(self):
        if random.choice([True, False]):
            self.coordinates = randint(0, 0xFF)

        if self.common != 0:
            self.common = get_similar_item(self.common,
                                           boost_factor=1.25).index
        if self.rare != 0:
            self.rare = get_similar_item(self.rare, boost_factor=1.15).index

        if self.common or self.rare:
            trapvalue = random.choice([True, False])
            self.set_bit("disable_trap", not trapvalue)
            if trapvalue:
                self.set_bit("always_trap", randint(1, 3) == 3)
                traptypes = ["sleeping_gas", "steel_needle",
                             "deathtrap", "degenerator"]
                for traptype in traptypes:
                    self.set_bit(traptype, False)
                self.set_bit(random.choice(traptypes), True)


class PoachObject(TableObject):
    specs = poach_specs

    def mutate(self):
        self.common = get_similar_item(self.common, boost_factor=1.25).index
        self.rare = get_similar_item(self.rare, boost_factor=1.15).index


class AbilityObject(TableObject):
    specs = ability_specs

    @property
    def ability_type(self):
        return self.misc_type & 0xF


class ItemObject(TableObject):
    specs = item_specs

    def mutate_shop(self):
        self.price = mutate_normal(self.price, maximum=65000, smart=True)
        self.price = int(round(self.price, -1))
        if self.price > 500:
            self.price = int(round(self.price, -2))
        if 1 <= self.time_available <= 16:
            self.time_available = mutate_normal(self.time_available,
                                                maximum=16, smart=True)
        if self.enemy_level > 1:
            self.enemy_level = int(round(0.8 * self.enemy_level))
            self.enemy_level = mutate_normal(self.enemy_level, minimum=1,
                                             maximum=99, smart=True)


class SkillsetObject(TableObject):
    specs = ss_specs

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
        candidates = [a for a in get_abilities() if a.ability_type == 1]
        for i, a in enumerate(self.actions):
            if get_ability(a).ability_type == 1:
                if randint(1, 100) == 100:
                    a = random.choice(candidates)
                    if a.jp_cost == 0:
                        a.jp_cost = 100 + randint(0, 700) + randint(0, 700)
                        a.jp_cost = int(round(a.jp_cost*2, -2) / 2)
                    self.actions[i] = a.index

        candidates = [a for a in get_abilities() if 7 <= a.ability_type <= 9]
        for i, a in enumerate(self.rsms):
            if randint(1, 100) == 100:
                a = random.choice(candidates)
                if a.jp_cost == 0:
                    a.jp_cost = 100 + randint(0, 700) + randint(0, 700)
                    a.jp_cost = int(round(a.jp_cost*2, -2) / 2)
                self.rsms[i] = a.index


class JobObject(TableObject):
    specs = job_specs

    def get_appropriate_boost(self):
        units = [u for u in get_units() if u.job == self.index
                 and u.get_bit("team1") and not u.level_normalized
                 and 0x180 <= u.map_id <= 0x1D5]
        if not units:
            return 1.3
        units = sorted(units, key=lambda u: u.level)
        units = units[-2:]
        average_level = sum([u.level for u in units]) / float(len(units))
        boost = 1.0 + (average_level / 100.0)
        return boost

    def mutate_stats(self, boost_factor=None):
        if boost_factor is None:
            boost_factor = self.get_appropriate_boost()
        for attr in ["hpgrowth", "hpmult", "mpgrowth", "mpmult", "spdgrowth",
                     "spdmult", "pagrowth", "pamult", "magrowth", "mamult",
                     "move", "jump", "evade"]:
            value = getattr(self, attr)
            newvalue = value
            if self.index not in range(0xE) + range(0x4A, 0x5E):
                newvalue = randint(newvalue,
                                   int(round(newvalue * boost_factor)))
            newvalue = mutate_normal(newvalue, smart=True)
            if value > 0:
                newvalue = max(newvalue, 1)
            setattr(self, attr, newvalue)

        return True

    def mutate_innate(self):
        if random.choice([True, False]):
            self.equips = mutate_bits(self.equips, 32)

        if random.choice([True, False]):
            self.nullify_elem = mutate_bits(self.nullify_elem)
            vulnerable = 0xFF ^ self.nullify_elem
            self.absorb_elem = mutate_bits(self.absorb_elem) & vulnerable
            self.resist_elem = mutate_bits(self.resist_elem) & vulnerable
            vulnerable = 0xFF ^ (self.nullify_elem | self.resist_elem)
            self.weak_elem = mutate_bits(self.weak_elem) & vulnerable

        if self.index in [0x4A]:
            return True

        if random.choice([True, False]):
            immune = mutate_bits(self.immune_status, 40)
            for i in range(40):
                mask = (1 << i)
                if mask & immune:
                    if randint(1, 50) == 50:
                        self.immune_status ^= mask
                    else:
                        self.immune_status |= mask
            not_innate = ((2**40)-1) ^ self.innate_status
            not_start = ((2**40)-1) ^ self.start_status
            self.immune_status &= not_innate
            self.immune_status &= not_start

            vulnerable = ((2**40)-1) ^ self.immune_status
            innate = mutate_bits(self.innate_status, 40)
            innate &= vulnerable
            innate &= VALID_INNATE_STATUSES
            not_innate2 = ((2**40)-1) ^ innate
            start = mutate_bits(self.start_status, 40)
            start &= vulnerable
            start &= (not_innate & not_innate2)
            start &= VALID_START_STATUSES
            self.innate_status |= innate
            self.start_status |= start

        if random.choice([True, False]):
            innate_cands = [a for a in get_abilities()
                            if a.ability_type in [7, 8, 9]]
            innate_cands = sorted(innate_cands, key=lambda a: a.jp_cost)
            innate_cands = [a.index for a in innate_cands]
            innate_attrs = ["innate1", "innate2", "innate3", "innate4"]
            innates = []
            for attr in innate_attrs:
                value = getattr(self, attr)
                if randint(1, 10) == 10:
                    index = None
                    if value:
                        assert value in innate_cands
                        index = innate_cands.index(value)
                    if not value and randint(1, 2) == 2:
                        ranked_jobs = get_ranked("job")
                        if self.index not in ranked_jobs:
                            continue
                        index = ranked_jobs.index(self.index)
                        index = float(index) / len(ranked_jobs)
                        index = int(round(index * len(innate_cands)))
                    if index is not None:
                        index = mutate_index(index, len(innate_cands),
                                             [True, False], (-6, 7), (-4, 4))
                        value = innate_cands[index]
                innates.append(value)
            innates = reversed(sorted(innates))
            for attr, innate in zip(innate_attrs, innates):
                setattr(self, attr, innate)

        return True


class UnitObject(TableObject):
    specs = unit_specs

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

    def normalize_level(self):
        self.level = 0xFE

    def set_backup_jp_total(self):
        self.backup_jp_total = self.jp_total

    @property
    def jp_total(self):
        if hasattr(self, "backup_jp_total"):
            return self.backup_jp_total

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

    def mutate_trophy(self):
        if self.gil > 0:
            self.gil = mutate_normal(self.gil, maximum=65000, smart=True)
            self.gil = int(round(self.gil, -2))
        if self.trophy:
            self.trophy = get_similar_item(self.trophy).index

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
            jp_remaining = randint(jp_remaining,
                                   int(jp_remaining * boost_factor))

        jobs = jobreq_namedict.values()
        jobs = [j for j in jobs if j.required_unlock_jp <= jp_remaining]
        if base_job is not None:
            if (randint(1, 5) != 5 and base_job.otherindex > 0):
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
        while randint(1, 7) == 7:
            unlocked_level += 1

        unlocked_level = min(unlocked_level, 8)
        self.unlocked = unlocked_job.otherindex
        self.unlocked_level = unlocked_level

        #if self.secondary > 0x18:
        #    return

        if randint(1, 10) == 10:
            candidates = get_ranked("secondary")
            candidates = [c for c in candidates if c < 0xb0]
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
                and randint(1, 3) != 3):
            assert unlocked_job.otherindex in range(0x14)
            self.secondary = unlocked_job.otherindex + 5
        elif self.secondary != 0 or random.choice([True, False]):
            self.secondary = 0xFE

        return True

    def mutate_monster_job(self):
        ranked_monster_jobs = [get_job(m) for m in get_ranked("job")
                               if m >= 0x5E]
        if self.map_id not in monster_selection:
            monster_jobs = [get_job(m.job) for m in mapunits[self.map_id]
                            if m.job >= 0x5E]
            monster_sprites = set([m.monster_graphic for m in monster_jobs])
            ranked_monster_sprites = []
            for m in ranked_monster_jobs:
                if m.monster_graphic not in ranked_monster_sprites:
                    ranked_monster_sprites.append(m.monster_graphic)
            selected_sprites = []
            for s in sorted(monster_sprites):
                temp_sprites = [t for t in ranked_monster_sprites
                                if t not in selected_sprites or t == s]
                index = temp_sprites.index(s)
                if s in selected_sprites:
                    temp_sprites.remove(s)
                index = mutate_index(index, len(temp_sprites), [True, False],
                                     (-2, 3), (-1, 1))
                selected = temp_sprites[index]
                selected_sprites.append(selected)
            selected_monsters = [m for m in ranked_monster_jobs
                                 if m.monster_graphic in selected_sprites]
            monster_selection[self.map_id] = selected_monsters

        selection = monster_selection[self.map_id]
        myjob = get_job(self.job)
        ranked_selection = [m for m in ranked_monster_jobs
                            if m in selection or m == myjob]
        index = ranked_selection.index(myjob)
        if myjob not in selection:
            ranked_selection.remove(myjob)
        index = mutate_index(index, len(ranked_selection), [True, False],
                             (-1, 2), (-1, 1))
        newjob = ranked_selection[index]
        self.job = newjob.index
        return True

    def mutate_job(self, boost_factor=1.2, preserve_gender=False):
        if self.job >= 0x5E:
            return self.mutate_monster_job()

        if self.job not in jobreq_indexdict:
            success = self.mutate_secondary()
            return success

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

        for attr in ["reaction", "support", "movement"]:
            if random.choice([True, False]):
                setattr(self, attr, 0x1FE)

        for attr in ["lefthand", "righthand", "head", "body", "accessory"]:
            if self.has_special_graphic:
                value = getattr(self, attr)
                if value in [0, 0xFF]:
                    setattr(self, attr, random.choice([0xFF, 0xFE]))
                elif value != 0xFE and random.choice([True, False]):
                    value = get_similar_item(value, same_equip=True,
                                             boost_factor=1.3).index
                    setattr(self, attr, value)
            elif random.choice([True, False]):
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
    specs = job_reqs_specs

    @property
    def pretty_str(self):
        s = "%s\n" % self.name.upper()
        prereq_dict = {}
        for attr in sorted(jobreq_namedict.keys()):
            value = getattr(self, attr)
            if value > 0:
                prereq_dict[attr] = value

        for attr in prereq_dict:
            prereq = jobreq_namedict[attr]
            for attr2 in prereq_dict:
                value = prereq_dict[attr2]
                value2 = getattr(prereq, attr2)
                if value2 >= value:
                    prereq_dict[attr2] = 0

        for attr, value in prereq_dict.items():
            if value > 0:
                s += "  %s %s\n" % (value, attr)

        return s.strip()

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
    return get_table_objects(UnitObject, 0x75e0800, 512*16, filename)


def get_unit(index):
    return [u for u in get_units() if u.index == index][0]


def get_skillsets(filename=None):
    skillsets = get_table_objects(SkillsetObject, 0x61294, 176, filename)
    return skillsets[5:]


def get_skillset(index):
    return [ss for ss in get_skillsets() if ss.index == index][0]


def get_items(filename=None):
    items = get_table_objects(ItemObject, 0x5f6b8, 254, filename)
    return items


def get_item(index):
    return [i for i in get_items() if i.index == index][0]


def get_monster_skills(filename=None):
    global g_monster_skills
    if g_monster_skills is not None:
        return g_monster_skills
    mss = get_table_objects(MonsterSkillsObject, 0x623c4, 48, filename)
    for ms in mss:
        ms.index += 0xb0
    g_monster_skills = mss
    return get_monster_skills()


def get_monster_skillset(index):
    return [ms for ms in get_monster_skills() if ms.index == index][0]


def get_move_finds(filename=None):
    return get_table_objects(MoveFindObject, 0x282e74, 512, filename)


def get_poaches(filename=None):
    return get_table_objects(PoachObject, 0x62864, 48, filename)


def get_abilities(filename=None):
    return get_table_objects(AbilityObject, 0x5b3f0, 512, filename)


def get_ability(index):
    return [a for a in get_abilities() if a.index == index][0]


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
    global backup_jobreqs
    if backup_jobreqs is not None:
        return backup_jobreqs

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

    backup_jobreqs = jobreqs
    return get_jobreqs()


def unlock_jobs(outfile):
    f = open(outfile, 'r+b')
    f.seek(0x5a4f4)
    f.write("".join([chr(0) for _ in xrange(4)]))
    f.close()


def make_rankings():
    global rankdict
    if rankdict is not None:
        return rankdict

    print "Analyzing and ranking unit data."
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

    rankdict["job", 0x7B] = 30 + (0.001 * 0x7B)  # wildbow
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


def get_ranked_items():
    items = [i for i in get_items() if i.index > 0]
    priceless = [i for i in items if i.price <= 10]
    priced = [i for i in items if i not in priceless]
    priced = sorted(priced, key=lambda i: i.price)
    priceless = sorted(priceless, key=lambda i: i.enemy_level)
    return priced + priceless


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
    jp_per_level = []
    for (a, b) in zip([0] + JOBLEVEL_JP, JOBLEVEL_JP):
        difference = b - a
        jp_per_level.append(difference)

    new_joblevel_jp = [0]
    for diff in jp_per_level:
        diff = randint(diff, int(diff*1.5))
        diff = mutate_normal(diff, maximum=800, smart=True)
        diff = int(round(diff*2, -2)) / 2
        new_joblevel_jp.append(new_joblevel_jp[-1] + diff)
    JOBLEVEL_JP = new_joblevel_jp[1:]
    f = open(filename, 'r+b')
    f.seek(0x62984)
    for j in JOBLEVEL_JP:
        write_multi(f, j, length=2)
    f.close()


def mutate_job_requirements():
    print "Mutating job requirements."
    reqs = get_jobreqs()
    done = [r for r in reqs if r.name == "squire"]
    levels = ([randint(0, 1)] +
              [randint(2, 3) for _ in range(4)] +
              [randint(3, 5) for _ in range(4)] +
              [randint(5, 8) for _ in range(4)] +
              [randint(8, 13) + randint(0, 8) for _ in range(3)] +
              [randint(13, 21) + randint(0, 13) for _ in range(2)] +
              [randint(34, 55)])
    assert len(levels) == 19
    random.shuffle(reqs)
    for req, numlevels in zip(reqs, levels):
        if req.name == "squire":
            continue
        assert req not in done

        req.set_zero()
        prereqs = []
        sublevels = []
        candidates = [c for c in done if c.name not in ["dancer", "bard"]]
        while numlevels > 1:
            sublevel = randint(2, 3) + randint(0, 1)
            sublevel = min(sublevel, numlevels)
            if len(sublevels) == 14 or len(sublevels) == len(candidates):
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
        if len(candidates) >= (len(sublevels) + 1):
            candidates = candidates[:-1]

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
                    index -= 1
                else:
                    break
            prereq = tempcands[index]
            prereqs.append(prereq)
            candidates.remove(prereq)

        for prereq, sublevel in zip(prereqs, sublevels):
            assert hasattr(req, prereq.name)
            setattr(req, prereq.name, sublevel)

        for r in reqs:
            r.remax_jobreqs()
        done.append(req)


def mutate_job_stats():
    print "Mutating job stats."
    jobs = get_jobs_kind("human")
    for j in jobs:
        j.mutate_stats()

    abilities = get_abilities()
    for a in abilities:
        if a.jp_cost > 0:
            a.jp_cost = mutate_normal(a.jp_cost, maximum=9999, smart=True)
            if a.jp_cost > 200:
                a.jp_cost = int(round(a.jp_cost*2, -2) / 2)
            else:
                a.jp_cost = int(round(a.jp_cost, -1))
            a.learn_chance = mutate_normal(a.learn_chance, maximum=100,
                                           smart=True)


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
    done_actions = set([])
    for ss in doing_skillsets:
        done_actions |= set(ss.actions)
    #skillsets = reversed(sorted(skillsets, key=lambda s: s.num_actions))
    random.shuffle(skillsets)
    for ss in skillsets:
        if ss in doing_skillsets:
            continue
        if set(ss.actions) & done_actions:
            continue
        doing_skillsets.append(ss)
        done_actions |= set(ss.actions)
    pulled_actions = {}
    for ss in doing_skillsets:
        num_to_pull = len(ss.actions) / 2
        num_to_pull = randint(0, num_to_pull) + randint(0, num_to_pull)
        if num_to_pull > len(ss.actions) / 2:
            num_to_pull = len(ss.actions) - num_to_pull
        pulled = random.sample(ss.actions, num_to_pull)
        for p in list(pulled):
            a = get_ability(p)
            if a.jp_cost > 0:
                ss.actions.remove(p)
            else:
                pulled.remove(p)
        pulled_actions[ss] = pulled
    exchanges = list(doing_skillsets)
    random.shuffle(exchanges)
    for a, b in zip(doing_skillsets, exchanges):
        pulled = pulled_actions[b]
        a.actions.extend(pulled)
        if len(a.actions) > 16:
            a.actions = random.sample(a.actions, 16)
        a.actions = sorted(a.actions)

    skillsets = get_skillsets()
    abilities = get_abilities()
    abilities = [a for a in abilities if a.jp_cost > 0
                 and 7 <= a.ability_type <= 9 and a.index not in BANNED_RSMS]
    abilities = [a.index for a in abilities]
    random.shuffle(skillsets)
    for skillset in skillsets:
        if 5 <= skillset.index <= 0x18:
            continue
        if len(skillset.rsms) > 0:
            num_to_sample = 2 + randint(0, 3) + randint(0, 3)
            num_to_sample = min(num_to_sample, 6)
            chosens = random.sample(abilities, 6)
            chosens.extend(skillset.rsms)
            random.shuffle(chosens)
            chosens = chosens[:num_to_sample]
            skillset.rsms = sorted(set(chosens))

    done = []
    for skillset in skillsets:
        if not (5 <= skillset.index <= 0x18):
            continue
        candidates = [a for a in abilities if a not in done]
        num_to_sample = min(len(candidates), 6)
        candidates = random.sample(candidates, num_to_sample)
        candidates += [a for a in skillset.rsms if a not in done]
        candidates = sorted(set(candidates))
        num_to_sample = randint(0, 3) + randint(0, 3)
        if num_to_sample <= 4 and random.choice([True, False]):
            num_to_sample += 1
        num_to_sample = min(num_to_sample, len(candidates), 6)
        chosens = random.sample(candidates, num_to_sample)
        skillset.rsms = sorted(chosens)
        done.extend(skillset.rsms)

    for skillset in get_skillsets():
        skillset.mutate_abilities()

    '''
    jobs = [j for j in get_jobs() if 0x4A <= j.index <= 0x5D]
    jobs = [j for j in jobs if j.skillset not in BANNED_SKILLSET_SHUFFLE]
    other_jobs_skills = [j.skillset for j in jobs]
    random.shuffle(other_jobs_skills)
    for j, ss in zip(jobs, other_jobs_skills):
        j.skillset = ss
    '''


def mutate_monsters():
    print "Mutating monsters."
    jobs = get_jobs_kind("monster")
    for j in jobs:
        j.mutate_stats() and j.mutate_innate()
    print "Mutating monster skills."
    for ms in get_monster_skills():
        ms.mutate()


def mutate_units():
    units = get_units()
    for key, value in mapsprites.items():
        generic = len([_ for (g, _) in value if g in (0x80, 0x81)])
        monster = len([_ for (g, _) in value if g == 0x82])
        other = len([_ for (g, _) in value if g not in (0x80, 0x81, 0x82, 0x00)])

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
            u.mutate_job()
            u.job_mutated = True

    random.shuffle(units)
    for u in [u for u in units if u.has_special_graphic or not u.named]:
        u.mutate_job()


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
    reverse_index = randint(int(round(reverse_index / boost_factor)),
                            reverse_index)
    index = len(items) - reverse_index - 1
    index = mutate_normal(index, maximum=len(items)-1, smart=True)
    replace_item = items[index]
    return replace_item


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

    for u in mapunits[0x183] | mapunits[0x184]:
        if u.get_bit("team1"):
            u.righthand = 0x49


def randomize():
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

    if len(argv) <= 2:
        print ("NOTICE: This randomizer requires 1 GB of free space "
               "to create a new rom file.\n")
        if len(argv) <= 1:
            sourcefile = raw_input("Filename? ").strip()
            print
        print ("u  Randomize enemy and ally units.\n"
               "j  Randomize job stats and JP required for skills.\n"
               "i  Randomize innate properties of jobs.\n"
               "s  Randomize job skillsets.\n"
               "r  Randomize job requirements and job level JP.\n"
               "t  Randomize trophies, poaches, and move-find items.\n"
               "p  Randomize item prices and shop availability.\n"
               "m  Randomize monster stats and skills.\n")
        flags = raw_input("Flags? (blank for all) ").strip()
        seed = raw_input("Seed? (blank for random) ").strip()
        print

    srchash = get_md5_hash(sourcefile)
    if srchash != MD5HASH:
        print "WARNING! The file you provided has the following md5 hash: "
        print srchash
        print "\nThis randomizer was tested on a file with this hash: "
        print MD5HASH
        resp = raw_input("\nContinuing might have unexpected results. "
                         "Proceed? (y/n) ")
        if resp and resp[0].lower() == 'y':
            pass
        else:
            sys.exit(0)

    if seed:
        seed = int(seed)
    else:
        seed = int(time())
    seed = seed % (10**10)
    print "Using seed: %s.%s\n" % (flags, seed)
    if flags:
        newsource = "fft_rcc.%s.%s.iso" % (flags, seed)
    else:
        newsource = "fft_rcc.%s.iso" % seed

    secret_codes = {}
    secret_codes['fiesta'] = "JOB FIESTA MODE"
    activated_codes = set([])
    if not flags:
        flags = lowercase
    else:
        for key in secret_codes.keys():
            if key in flags:
                flags = flags.replace(key, '')
                print "SECRET CODE: %s ACTIVATED" % secret_codes[key]
                activated_codes.add(key)

    print "COPYING ROM IMAGE"
    copyfile(sourcefile, newsource)
    sourcefile = newsource

    remove_sector_metadata(sourcefile, TEMPFILE)

    units = get_units(TEMPFILE)
    jobs = get_jobs(TEMPFILE)
    jobreqs = get_jobreqs(TEMPFILE)
    skillsets = get_skillsets(TEMPFILE)
    items = get_items(TEMPFILE)
    monster_skills = get_monster_skills(TEMPFILE)
    move_finds = get_move_finds(TEMPFILE)
    poaches = get_poaches(TEMPFILE)
    abilities = get_abilities(TEMPFILE)

    all_objects = [units, jobs, jobreqs, skillsets, items,
                   monster_skills, move_finds, poaches, abilities]

    sort_mapunits()
    make_rankings()
    if 'r' in flags:
        random.seed(seed)
        mutate_job_level(TEMPFILE)
        for u in units:
            u.set_backup_jp_total()
        mutate_job_requirements()
        s = ""
        for name in sorted(jobreq_namedict.keys()):
            jr = jobreq_namedict[name]
            s = "\n\n".join([s, jr.pretty_str])
        s = s.strip()
        f = open("%s.txt" % seed, "w+")
        f.write(s)
        f.close()

    for req in jobreqs:
        req.set_required_unlock_jp()

    if 'u' in flags:
        random.seed(seed)
        mutate_units()

    if 'j' in flags:
        random.seed(seed)
        mutate_job_stats()

    if 'i' in flags:
        random.seed(seed)
        mutate_job_innates()

    if 'm' in flags:
        random.seed(seed)
        mutate_monsters()

    if 't' in flags:
        random.seed(seed)
        mutate_treasure()

    if 'p' in flags:
        random.seed(seed)
        mutate_shops()

    if 's' in flags:
        random.seed(seed)
        mutate_skillsets()

    if set(flags) & set("rujimtps"):
        for map_id in range(0x180, 0x1D5):
            if map_id == 0x183:
                continue
            for u in mapunits[map_id]:
                if not u.get_bit("team1") and not u.level_normalized:
                    u.normalize_level()

        # make Orbonne controllable
        for u in sorted(mapunits[0x183], key=lambda u: u.index):
            if not u.get_bit("team1"):
                u.set_bit("control", True)

    if "fiesta" in activated_codes:
        setup_fiesta(TEMPFILE)

    print "WRITING MUTATED DATA"
    for objects in all_objects:
        print "Writing %s data." % objects[0].__class__.__name__
        for obj in objects:
            obj.write_data()

    #unlock_jobs(TEMPFILE)
    rewrite_header(TEMPFILE, "FFT RCC %s" % seed)

    inject_logical_sectors(TEMPFILE, sourcefile)
    remove(TEMPFILE)

    if len(argv) <= 2:
        raw_input("\nRandomization completed successfully. "
                  "\nOutput filename: %s"
                  "\nPress enter to close this program. " % sourcefile)

if __name__ == "__main__":
    try:
        randomize()
    except Exception, e:
        print "ERROR: %s" % e
        raw_input("Press enter to quit. ")
