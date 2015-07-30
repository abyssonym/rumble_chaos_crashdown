from shutil import copyfile
import os
from os import remove
import sys
from sys import argv
from time import time
from string import lowercase
from collections import Counter

from utils import (mutate_index, mutate_normal, mutate_bits, write_multi,
                   utilrandom as random)
from tablereader import TableObject, set_global_table_filename
from uniso import remove_sector_metadata, inject_logical_sectors


def randint(a, b):
    return random.randint(min(a, b), max(a, b))

VERSION = "13"
MD5HASHES = ["aefdf27f1cd541ad46b5df794f635f50",
             "b156ba386436d20fd5ed8d37bab6b624",
             ]
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

VALID_INNATE_STATUSES = 0xCAFCE92A10
VALID_START_STATUSES = VALID_INNATE_STATUSES | 0x3402301000
BENEFICIAL_STATUSES = 0xC278600000
BANNED_SKILLSET_SHUFFLE = [0, 1, 2, 3, 6, 8, 0x11, 0x12, 0x13, 0x14, 0x15,
                           0x18, 0x34, 0x38, 0x39, 0x3B, 0x3E, 0x9C, 0xA1]
BANNED_RSMS = [0x1BB, 0x1E1, 0x1E4, 0x1E5, 0x1F1]
BANNED_ANYTHING = [0x18]
LUCAVI_INNATES = (range(0x1A6, 0x1A9)
                  + range(0x1AA, 0x1B4) + [0x1B5, 0x1B6, 0x1BA, 0x1BD, 0x1BE]
                  + range(0x1C0, 0x1C6)
                  + range(0x1D1, 0x1D6) + [0x1D8, 0x1DD, 0x1DE, 0x1E2, 0x1E3]
                  + [0x1E7, 0x1E8]
                  + range(0x1EB, 0x1EF) + [0x1F2, 0x1F3, 0x1F6, 0x1FA, 0x1FB]
                  )


LUCAVI_JOBS = [0x3C, 0x3E, 0x40, 0x41, 0x43, 0x45, 0x49, 0x97]
LUCAVI_ORDER = [0x43, 0x3C, 0x3E, 0x45, 0x40, 0x41, 0x97, 0x49]
BASIC_JOBS = range(0x4A, 0x5E)
MONSTER_JOBS = range(0x5E, 0x8E) + [0x90, 0x91, 0x96, 0x97, 0x99, 0x9A]
STORYLINE_RECRUITABLE_JOBS = [0xD, 0xF, 0x16, 0x1A, 0x1E, 0x1F,
                              0x29, 0x2A, 0x90, 0x91]
USED_MAPS = range(0, 0x14B) + range(0x180, 0x1d6)

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
g_ranked_monster_jobs = None
g_ranked_secondaries = None
birthday_dict = {}
boostd = {}
rng_report_counter = 0

SUPER_LEVEL_BOOSTED = []
SUPER_SPECIAL = []


def set_difficulty_factors(value):
    value = max(value, 0)
    try:
        boostd["common_item"] = max(2.0 - (0.5 * value), 0.5)
        boostd["trophy"] = max(1.5 - (0.5 * value), 0.25)
        boostd["default_stat"] = 1.2 ** value
        boostd["level_stat"] = 0.75 * value
        boostd["equipment"] = 1.2 ** value
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
    while len(message) < 0x20:
        message += " "
    f = open(filename, 'r+b')
    f.seek(0x8028)
    f.write(message)
    f.close()


TEMPFILE = "_fftrandom.tmp"


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

    def mutate(self):
        if random.choice([True, False]):
            self.coordinates = randint(0, 0xFF)

        if self.common != 0:
            self.common = get_similar_item(
                self.common, boost_factor=boostd["common_item"]).index
        if self.rare != 0:
            common = ItemObject.get(self.common)
            candidates = [i for i in ItemObject.every if i.rank > common.rank]
            self.rare = random.choice(candidates).index

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
    def mutate(self):
        self.common = get_similar_item(
            self.common, boost_factor=boostd["common_item"]).index
        common = ItemObject.get(self.common)
        candidates = [i for i in ItemObject.every if i.rank > common.rank]
        self.rare = random.choice(candidates).index


class AbilityAttributesObject(TableObject):
    def mutate(self):
        for attr in ["ct", "mp"]:
            value = getattr(self, attr)
            if 1 <= value <= 0xFD:
                value = mutate_normal(value)
                setattr(self, attr, value)

        #if 1 <= self.xval <= 0xFD and self.formula in X_FORMULAS:
        if randint(1, 2) <= self.xval <= 0xFD:
            self.xval = mutate_normal(self.xval, minimum=1, maximum=0xFD)

        #if 1 <= self.yval <= 0xFD and self.formula in Y_FORMULAS:
        if randint(1, 2) <= self.yval <= 0xFD:
            self.yval = mutate_normal(self.yval, minimum=1, maximum=0xFD)

        for attr in ["range", "effect", "vertical"]:
            if randint(1, 20) == 20:
                value = getattr(self, attr)
                if randint(1, 2) <= value <= 0xFD:
                    value = mutate_normal(value, minimum=1, maximum=0xFD)
                    setattr(self, attr, value)


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
            if self.enemy_level <= 5:
                self.enemy_level = 50
            self.set_bit("rare", False)

        if self.enemy_level >= 1:
            self.enemy_level = int(round(
                self.enemy_level / boostd["equipment"]))
            self.enemy_level = mutate_normal(self.enemy_level, minimum=1,
                                             maximum=99)


class SkillsetObject(TableObject):
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

        candidates = [a for a in get_abilities() if 7 <= a.ability_type <= 9]
        for i, a in enumerate(self.rsms):
            if randint(1, 100) == 100:
                a = random.choice(candidates)
                if a.jp_cost == 0:
                    a.jp_cost = 100 + randint(0, 700) + randint(0, 700)
                    a.jp_cost = int(round(a.jp_cost*2, -2) / 2)
                self.rsms[i] = a.index


class JobObject(TableObject):
    @property
    def crippled(self):
        status = self.innate_status | self.start_status
        bad_start = 0xFFFFFFFFFF ^ VALID_START_STATUSES
        return bool(status & bad_start)

    @property
    def can_invite(self):
        return not bool(self.immune_status & 0x4000)

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

    def get_appropriate_boost(self):
        if self.index in [1, 2, 3, 0xD] + range(0x4A, 0x5E):
            return 1.0

        units = [u for u in get_units() if u.job == self.index
                 and u.get_bit("enemy_team") and not u.level_normalized
                 and 0x180 <= u.map_id <= 0x1D5]
        if not units:
            return boostd["default_stat"]
        units = sorted(units, key=lambda u: u.level)
        units = units[-2:]
        average_level = sum([u.level for u in units]) / float(len(units))
        boost = (1.0 + (average_level / 100.0)) ** boostd["level_stat"]
        return boost

    def mutate_stats(self, boost_factor=None):
        if boost_factor is None:
            boost_factor = self.get_appropriate_boost()
        for attr in ["hpgrowth", "hpmult", "mpgrowth", "mpmult", "spdgrowth",
                     "spdmult", "pagrowth", "pamult", "magrowth", "mamult",
                     "move", "jump", "evade"]:
            value = getattr(self, attr)
            newvalue = value
            newvalue = randint(newvalue,
                               int(round(newvalue * boost_factor)))
            newvalue = max(1, min(newvalue, 0xFD))
            if 1 <= newvalue <= 0xFD:
                newvalue = mutate_normal(newvalue, minimum=1, maximum=0xFD)
                if self.is_lucavi and newvalue < value:
                    newvalue = value + abs(value - newvalue)
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
            self.mutate_statuses()
        if self.is_lucavi and random.choice([True, False]):
            self.mutate_statuses()
            if randint(1, 30) != 30:
                self.unset_negative_statuses()

        if not self.is_lucavi and random.choice([True, False]):
            innate_cands = [a for a in get_abilities()
                            if a.ability_type in [7, 8, 9]]
            innate_cands = sorted(innate_cands, key=lambda a: a.jp_cost)
            innate_attrs = ["innate1", "innate2", "innate3", "innate4"]
            innates = []
            for attr in innate_attrs:
                value = getattr(self, attr)
                chance = randint(1, 10)
                if chance == 10 or (self.is_monster_job and chance > 5):
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
            innate_cands = [i.index for i in innate_cands if i.is_support]
            if not self.is_altima:
                innate_cands += [0, 0, 0]
            random.shuffle(innate_cands)
            new_innates = []
            while len(new_innates) < 4:
                # short charge or non-charge
                value = innate_cands.pop()
                if value in new_innates:
                    continue
                if 0x1E2 not in new_innates and 0x1E3 not in new_innates:
                    if len(new_innates) == 3:
                        new_innates.append(0x1E2)
                        break
                elif value in [0x1E2, 0x1E3]:
                    continue
                new_innates.append(value)
            assert len(new_innates) == 4
            new_innates = sorted(new_innates)
            for attr, innate in zip(innate_attrs, new_innates):
                setattr(self, attr, innate)
            assert all([isinstance(i, int) for i in self.innates])

        return True

    def mutate_statuses(self):
        immune = mutate_bits(self.immune_status, 40)
        for i in range(40):
            mask = (1 << i)
            if mask & immune:
                if mask & BENEFICIAL_STATUSES or randint(1, 50) == 50:
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
    def is_lucavi(self):
        return self.job in LUCAVI_JOBS

    @property
    def is_altima(self):
        return self.job in [0x41, 0x49]

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
        unlocked_level = len([j for j in JOBLEVEL_JP if j <= jp_remaining])
        if random.choice([True, False]):
            unlocked_level += 1
        while randint(1, 7) == 7:
            unlocked_level += 1

        unlocked_level = min(unlocked_level, 8)
        self.unlocked = unlocked_job.otherindex
        self.unlocked_level = unlocked_level
        if self.is_lucavi and randint(1, 15) != 15:
            candidates = get_ranked_secondaries()
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
                and randint(1, 3) != 3):
            assert unlocked_job.otherindex in range(0x14)
            self.secondary = unlocked_job.otherindex + 5
        elif randint(1, 5) == 5:
            cands = []
            for name in JOBNAMES:
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

    def mutate_monster_job(self):
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
        if self.map_id not in monster_selection:
            assert self in mapunits[self.map_id]
            assert self.graphic == 0x82
            ranked_monster_jobs = list(all_ranked_monster_jobs)
            map_monster_jobs = [JobObject.get(u.job)
                                for u in mapunits[self.map_id]
                                if monster_check(u)]
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
            index = mutate_index(index, len(ranked_selection), [True, False],
                                 (0, 1), (-1, 1))
            newjob = ranked_selection[index]
        self.job = newjob.index
        named_jobs[self.name, oldjob] = self.job
        return True

    def mutate(self, boost_factor=None, preserve_gender=False):
        if boost_factor is None:
            boost_factor = boostd["jp"]
        self.mutate_stats()

        if self.is_lucavi:
            self.mutate_rsm()
            self.mutate_secondary()
            return

        if self.job >= 0x5E:
            self.mutate_monster_job()
            return

        if self.job not in jobreq_indexdict:
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
            if gender == "male":
                self.set_bit("male", True)
                self.set_bit("female", False)
                self.graphic = 0x80
            elif gender == "female":
                self.set_bit("female", True)
                self.set_bit("male", False)
                self.graphic = 0x81

        self.mutate_equips()
        self.mutate_rsm()
        self.mutate_secondary()
        return True

    def mutate_equips(self):
        for attr in ["lefthand", "righthand", "head", "body", "accessory"]:
            if self.has_special_graphic:
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
                    setattr(self, attr, value)
                elif randint(1, 3) == 3:
                    setattr(self, attr, 0xFE)
            elif random.choice([True, False]):
                setattr(self, attr, 0xFE)

    def mutate_rsm(self):
        job = JobObject.get(self.job)
        for attr in ["reaction", "support", "movement"]:
            cands = [a for a in AbilityObject.every
                     if getattr(a, "is_%s" % attr) is True]
            if self.is_lucavi:
                cands = [c.index for c in cands]
                cands = [c for c in cands
                         if c in LUCAVI_INNATES and c not in job.innates
                         and c not in [0x1e2, 0x1e3]]
                setattr(self, attr, random.choice(cands))
            elif self.has_special_graphic and randint(1, 3) == 3:
                cands = sorted(cands, key=lambda a: a.jp_cost)
                index = len(cands) / 2
                index = mutate_normal(index, maximum=len(cands)-1)
                setattr(self, attr, cands[index].index)
            elif random.choice([True, False]):
                setattr(self, attr, 0x1FE)

        if job.is_altima:
            self.movement = 0x1F3

    def mutate_level(self):
        if (self.index <= 0xFFF and self.get_bit("randomly_present")
                and randint(1, 10) == 10):
            if not self.level_normalized:
                self.level += randint(0, 10) + randint(0, 10)
                self.level = min(self.level, 99)
            else:
                if self.level > 199:
                    self.level = 100
                self.level += randint(0, 10) + randint(0, 10)
                self.level = min(self.level, 199)
            SUPER_LEVEL_BOOSTED.append(self)
        if not self.level_normalized and 5 <= self.level <= 99:
            self.level = mutate_index(self.level, 99,
                                      (True, False), (-2, 3), (-1, 2))

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
    def pretty_str(self):
        s = "%s\n" % self.name.upper()
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

        for attr, value in prereq_dict.items():
            if value > 0:
                s += "  %s %s\n" % (value, attr)
        if removed:
            s += "  Also: " + ", ".join(sorted(set(removed)))

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
    return AbilityObject.every


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
            j.rank = 0 + (j.index * 0.0000001)
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
        j.rank = sum(scores) / len(scores)
        if j.is_lucavi:
            j.rank *= 1.5
        elif j.monster_portrait == 0:
            j.rank *= 1.3
        if j.crippled:
            j.rank = j.rank / 10.0

    ranked_jobs = sorted(good_jobs, key=lambda j: j.rank)
    ranked_jobs = [j.index for j in ranked_jobs]

    rankable_features = [
        "map_id", "unlocked", "unlocked_level", "righthand", "lefthand",
        "head", "body", "accessory", "job", "secondary", "reaction", "support",
        "movement"]
    unrankable_values = [0, 0xFE, 0xFF]
    rankdict = {}
    for j in good_jobs:
        rankdict["job", j.index] = j.rank
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

    for j in good_jobs:
        rankdict["job", j.index] = j.rank

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
        rank = rank * (skillset.num_actions / 8.0)
        if rank > 0:
            num_free = skillset.num_free_actions
            abilities = [AbilityObject.get(a) for a in skillset.actions]
            acosts = [a.jp_cost for a in abilities if 1 <= a.jp_cost <= 199]
            if acosts:
                average_jp_cost = sum(acosts) / len(acosts)
                rank = rank * average_jp_cost
            elif num_free == 0:
                rank = 0
            else:
                rank = rank * 200
            for i in xrange(num_free):
                rank *= 1.1
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
        diff = randint(diff, int(diff*boostd["jp"]))
        diff = mutate_normal(diff, maximum=800)
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

    num_jobpools = 2 + random.choice([0, 0, 1])
    squire = [r for r in reqs if r.name == "squire"][0]
    jobpools = [set([]) for _ in xrange(num_jobpools)]
    allpool = set([squire])
    reqs = [r for r in reqs if r is not squire]
    random.shuffle(reqs)
    assert len(levels) == len(reqs) == 19
    for req, numlevels in zip(reqs, levels):
        assert req not in done

        base_numlevels = numlevels
        req.set_zero()
        prereqs = []
        sublevels = []
        jobpoolcands = [j for j in jobpools
                        if len(j) == len(min(jobpools, key=lambda j: len(j)))]
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
        if len(candidates) >= (len(sublevels) + 1):
            candidates = candidates[:-1]
        if (len(candidates) >= (len(sublevels) + 1)
                and random.choice([True, False])):
            candidates = candidates[1:]

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

        for prereq, sublevel in zip(prereqs, sublevels):
            assert hasattr(req, prereq.name)
            setattr(req, prereq.name, sublevel)

        for r in reqs:
            r.remax_jobreqs()
        done.append(req)
        if req.name not in ["dancer", "bard"]:
            if base_numlevels >= randint(2, 3):
                jobpool.add(req)
            else:
                allpool.add(req)


def mutate_job_stats():
    print "Mutating job stats."
    jobs = get_jobs_kind("human")
    for j in jobs:
        j.mutate_stats()
        skillset = SkillsetObject.get(j.skillset)
        abilities = skillset.actions + skillset.rsms
        if not abilities:
            continue
        abilities = [AbilityObject.get(a) for a in abilities]
        num_abilities = len(abilities)
        learn_base = 100 / num_abilities
        learn_factor = (100 - learn_base) / 2
        for a in abilities:
            if a.jp_cost > 0:
                a.jp_cost = mutate_normal(a.jp_cost, maximum=9999)
                if a.jp_cost > 200:
                    a.jp_cost = int(round(a.jp_cost*2, -2) / 2)
                else:
                    a.jp_cost = int(round(a.jp_cost, -1))
            if 1 <= a.learn_chance <= 99 or randint(1, 20) == 20:
                a.learn_chance = (learn_base + randint(0, learn_factor)
                                  + randint(0, learn_factor))
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
    #skillsets = reversed(sorted(skillsets, key=lambda s: s.num_actions))
    random.shuffle(skillsets)
    for ss in skillsets:
        if ss in doing_skillsets:
            continue
        if set(ss.actions) - done_actions:
            doing_skillsets.append(ss)
            done_actions |= set(ss.actions)
    random.shuffle(doing_skillsets)
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
        if pulled or random.choice([True, False, False]):
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
        b_actions = sorted([x for x in actions if x in pulled])
        if random.choice([True, False]):
            a.actions = a_actions + b_actions
        else:
            a.actions = b_actions + a_actions

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

    done = []
    for skillset in skillsets:
        # RSMs for basic classes
        if not (5 <= skillset.index <= 0x18):
            continue
        if skillset.index in BANNED_ANYTHING:
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

    for index in BANNED_SKILLSET_SHUFFLE:
        if not 5 <= index <= 0x18:
            continue
        ss = get_skillset(index)
        for action in list(ss.actions):
            if randint(1, 8) == 8:
                ss.actions.remove(action)


def mutate_abilities_attributes():
    abilities_attributes = get_abilities_attributes()
    for aa in abilities_attributes:
        aa.mutate()


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
    for key, value in mapsprites.items():
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
    for u in [u for u in units if u.has_special_graphic or not u.named]:
        u.mutate()


def mutate_units_special(job_names):
    print "Adding special surprises."
    mundane_job_names = job_names[0x4A:0x5E]
    ranked_jobs = get_ranked("job")
    special_jobs = [j for j in get_jobs() if not 5 <= j.skillset <= 0x18
                    and not j.skillset == 0
                    and not 0x4A <= j.index <= 0x8F
                    and not j.index >= 0x92
                    and job_names[j.index] not in mundane_job_names
                    and job_names[j.index]]
    special_jobs = [j.index for j in special_jobs]
    special_jobs = [j for j in ranked_jobs if j in special_jobs]
    for map_id in range(1, 0xFE) + range(0x180, 0x1D5):
        if map_id <= 0xFF:
            boost_factor = boostd["random_special_unit"]
        else:
            boost_factor = boostd["story_special_unit"]

        lucavi_special = False
        units = mapunits[map_id]
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
        else:
            probval -= 1
            probval = max(probval, 2)

        if map_id in [0x183, 0x184, 0x185]:
            continue
        if lucavi_special or randint(1, probval) == 1:
            candidates = [u for u in units if not u.named
                          and u.get_bit("enemy_team")
                          and 0x80 <= u.graphic <= 0x82]
            noncandidates = [u for u in units if u not in candidates]
            noncandjobs = [u.job for u in noncandidates
                           if 0x80 <= u.graphic <= 0x82]
            candidates = [c for c in candidates if c.job not in noncandjobs]
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
                               get_job(c.job).monster_portrait == replace_job]
                replace_job = sorted(replace_job)[0]

            cand_jobs = [j for j in ranked_jobs
                         if j in special_jobs or j == replace_job
                         or (lucavi_special and j == lucavi_unit.job)]
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
            else:
                mg = get_job(replace_job).monster_portrait
                assert mg > 0
                change_units = [u for u in units
                                if get_job(u.job).monster_portrait == mg]

            change_units = sorted(change_units, key=lambda u: u.index)
            old_job = change_units[0].job
            for unit in change_units:
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

            #print "%x %x %s" % (map_id, job.index, len(change_units))

            if map_id >= 0x180:
                similar_graphic_jobs = [u.job for u in UnitObject.every
                                        if u.graphic == chosen_unit.graphic]
                special_jobs = [j for j in special_jobs
                                if j not in similar_graphic_jobs]
                if not special_jobs:
                    break
                if not lucavi_special:
                    probval = max(probval, 15)
            else:
                probval = max(probval, 8)


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
        if u.get_bit("enemy_team"):
            u.righthand = 0x49


def get_job_names(filename):
    pointer = 0x2eed41
    job_names = []
    f = open(filename, "r+b")
    f.seek(pointer)
    for i in xrange(0xA0):
        s = ""
        while True:
            c = f.read(1)
            if ord(c) == 0xFE:
                job_names.append(s)
                break
            else:
                s += c
    f.close()
    return job_names


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

    srchash = get_md5_hash(sourcefile)
    stats = os.stat(sourcefile)
    filesize = stats.st_size
    if filesize not in ISO_SIZES + RAW_SIZES:
        resp = raw_input("WARNING! The file you provided is not a known "
                         "file size. Continue? (y/n) ")
        if resp and resp[0].lower() == 'y':
            filesize = min(ISO_SIZES + RAW_SIZES,
                           key=lambda s: abs(s-filesize))
        else:
            sys.exit(0)
    elif srchash not in MD5HASHES + RAWMD5HASHES:
        print "WARNING! The file you provided has the following md5 hash: "
        print srchash
        print "\nThis randomizer was tested on a file with this hash: "
        print MD5HASHES[0]
        resp = raw_input("\nContinuing might have unexpected results. "
                         "Proceed? (y/n) ")
        if resp and resp[0].lower() == 'y':
            pass
        else:
            sys.exit(0)

    if len(argv) == 4:
        difficulty = float(argv[3])
    else:
        difficulty = 1.0

    if len(argv) <= 2:
        print ("u  Randomize enemy and ally units.\n"
               "j  Randomize job stats and JP required for skills.\n"
               "i  Randomize innate properties of jobs.\n"
               "s  Randomize job skillsets.\n"
               "a  Randomize abilities, including CT, MP cost, etc.\n"
               "r  Randomize job requirements and job level JP.\n"
               "t  Randomize trophies, poaches, and move-find items.\n"
               "p  Randomize item prices and shop availability.\n"
               "m  Randomize monster stats and skills.\n"
               "z  Enable special surprises.\n")
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
    print "Using seed: %s.%s\n" % (flags, seed)
    if flags:
        newsource = "fft_rcc.%s.%s.iso" % (flags, seed)
    else:
        newsource = "fft_rcc.%s.iso" % seed

    if filesize in RAW_SIZES:
        newsource = newsource[:-3] + "bin"

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

    assert filesize in ISO_SIZES + RAW_SIZES
    if filesize in ISO_SIZES:
        remove_sector_metadata(sourcefile, TEMPFILE)
    else:
        copyfile(sourcefile, TEMPFILE)

    set_global_table_filename(TEMPFILE)

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
        s = ""
        for name in sorted(jobreq_namedict.keys()):
            jr = jobreq_namedict[name]
            s = "\n\n".join([s, jr.pretty_str])
        s = s.strip()
        f = open("%s.txt" % seed, "w+")
        f.write(s)
        f.close()

    for req in get_jobreqs():
        req.set_required_unlock_jp()

    if 'i' in flags:
        # before units
        random.seed(seed)
        mutate_job_innates()

    if 'm' in flags:
        # before units
        random.seed(seed)
        mutate_monsters()

    if 'u' in flags:
        random.seed(seed)
        mutate_units()

    if 'z' in flags:
        random.seed(seed)
        mutate_units_special(get_job_names(TEMPFILE))

    if 'j' in flags:
        random.seed(seed)
        mutate_job_stats()

    if 't' in flags:
        random.seed(seed)
        mutate_treasure()

    if 'p' in flags:
        random.seed(seed)
        mutate_shops()

    if 's' in flags:
        random.seed(seed)
        mutate_skillsets()

    if 'a' in flags:
        random.seed(seed)
        mutate_abilities_attributes()

    if set(flags) & set("rujimtpsaz"):
        random.seed(seed)
        for unit_id in [0x1951, 0x19d0, 0x1a10, 0x1ac0, 0x1b10]:
            u = get_unit(unit_id)
            u.normalize_level(randint(1, 3))

        # make Orbonne controllable
        for u in sorted(mapunits[0x183], key=lambda u: u.index):
            if not u.get_bit("enemy_team"):
                u.set_bit("control", True)

    if "fiesta" in activated_codes:
        setup_fiesta(TEMPFILE)

    DOUBLE_SUPER = set(SUPER_LEVEL_BOOSTED) & set(SUPER_SPECIAL)
    #for unit in DOUBLE_SUPER:
    #    print "%x %x %s" % (unit.map_id, unit.job, unit.level)

    print "WRITING MUTATED DATA"
    for ao in all_objects:
        print "Writing %s data." % ao.__name__
        for obj in ao.every:
            obj.write_data()

    #unlock_jobs(TEMPFILE)
    rewrite_header(TEMPFILE, "FFT RCC %s" % seed)

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
    try:
        randomize()
    except Exception, e:
        print "ERROR: %s" % e
        raw_input("Press enter to quit. ")
