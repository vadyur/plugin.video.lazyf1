# coding: utf-8

import re

def current_year():
	return 2021

def gp_variants(GP):
	# type: (str) -> str
	variants = {
		u'мехико': u'Мексики',
		u'сан-паулу': u'Бразилии',
		u'азербайджан': u'Азербайджана'
	}

	key = GP.lower().replace(u'гран при', u'').strip()
	alt = variants.get(key)
	if alt:
		return u'{} | {}'.format(GP, alt)
	return GP
