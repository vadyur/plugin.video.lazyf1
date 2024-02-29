import re

import calendar
import time
from datetime import datetime,tzinfo,timedelta

def current_year():
	return 2024

def gp_variants(GP):
	# type: (str) -> str
	variants = {
		u'мехико': u'Мексики',
		u'сан-паулу': u'Бразилии',
		u'азербайджан': u'Азербайджана'
	}

	key = GP.lower().replace(u'гран при', '').strip()
	alt = variants.get(key)
	if alt:
		return '{} | {}'.format(GP, alt)
	return GP

def local_time_from_msk(msk_dt):
	class Zone(tzinfo):
		def __init__(self,offset,isdst,name):
			self.offset = offset
			self.isdst = isdst
			self.name = name
		def utcoffset(self, dt):
			return timedelta(hours=self.offset) + self.dst(dt)
		def dst(self, dt):
			return timedelta(hours=1) if self.isdst else timedelta(0)
		def tzname(self,dt):
			return self.name

	t = time.time()
	lt = time.localtime(t)

	if hasattr(lt, 'tm_gmtoff'):
		TZ_OFFSET = lt.tm_gmtoff // 3600
	else:
		gmt = time.gmtime(t)
		offset = time.mktime(lt) - time.mktime(gmt)
		TZ_OFFSET = offset // 3600

	MSK = Zone(3,False,'MSK')
	LOCAL = Zone(TZ_OFFSET, False, 'LOCAL')

	format = '%H:%M'
	dt = datetime.strptime(msk_dt, format)
	dt = dt.replace(tzinfo=MSK)
	dt = dt.astimezone(LOCAL)
	result = datetime.strftime(dt, format)
	return result

