# coding: utf-8

from __future__ import absolute_import

import re, json
from vdlib.util.log import debug

from vdlib.scrappers.rutracker import RuTrackerBase

from bs4 import BeautifulSoup

try:
	from .f1base import current_year
except ImportError:
	from f1base import current_year	# type: ignore

from vdlib.scrappers.base import clean_html

class RuTracker(RuTrackerBase):

	season_parts = {
		'660': [current_year()],
		'1551': [ year for year in range(2012, current_year()) ],
		'626': [ year for year in range(1950, 2011+1) ]
	}

	@staticmethod
	def part_for_year(year):
		year = int(year)
		for part in RuTracker.season_parts:
			if year in RuTracker.season_parts[part]:
				return part
		return None

	def _fix_url_encoding(self, s):
		"""Fix Kodi 21 cp1251 garbling of Cyrillic in plugin URLs.
		Kodi decodes %D0%D0%D8... as cp1251, producing garbled Unicode.
		Re-encode cp1251 -> bytes -> decode UTF-8 to recover original text.
		"""
		if not isinstance(s, str):
			return s
		try:
			return s.encode('cp1251').decode('utf-8')
		except (UnicodeDecodeError, UnicodeEncodeError):
			return s

	# Country name: nominative -> genitive for rutracker search
	_GP_GENITIVE = {
		u'Испания': u'Испании',
		u'Бахрейн': u'Бахрейна',
		u'Австралия': u'Австралии',
		u'Китай': u'Китая',
		u'Япония': u'Японии',
		u'Канада': u'Канады',
		u'Австрия': u'Австрии',
		u'Великобритания': u'Великобритании',
		u'Венгрия': u'Венгрии',
		u'Бельгия': u'Бельгии',
		u'Нидерланды': u'Нидерландов',
		u'Италия': u'Италии',
		u'Азербайджан': u'Азербайджана',
		u'Сингапур': u'Сингапура',
		u'Мексика': u'Мексики',
		u'Бразилия': u'Бразилии',
		u'Катар': u'Катара',
		u'Саудовская Аравия': u'Саудовской Аравии',
		u'Лас-Вегас': u'Лас-Вегаса',
		u'Майами': u'Майами',
		u'Монако': u'Монако',
		u'США': u'США',
		u'ОАЭ': u'ОАЭ',
		u'Эмираты': u'Эмиратов',
	}

	def _to_genitive(self, gp):
		"""Convert country GP name to genitive case for rutracker search.
		e.g. 'Испания' -> 'Испании', 'Бахрейн' -> 'Бахрейна'
		"""
		if 'Гран-при ' in gp:
			country = gp[len('Гран-при '):]
			gen = self._GP_GENITIVE.get(country)
			if gen:
				return u'Гран-при ' + gen
		gen = self._GP_GENITIVE.get(gp)
		if gen:
			return gen
		return gp

	def search(self, event, GP, year):
		if not self.check_settings():
			return

		# tcp://localhost:6668
		"""
		import ptvsd
		ptvsd.enable_attach(secret=None, address = ('0.0.0.0', 6668))	
		ptvsd.wait_for_attach()
		# """

		url = 'https://%s/forum/viewforum.php?f=' % self.baseurl + RuTracker.part_for_year(year)
		headers = {'Referer': url}

		event = self._fix_url_encoding(event)
		GP = self._fix_url_encoding(GP)

		event = event.lower().replace(u'тренировка', u'практика')

		if 'при' not in GP.lower() and 'prix' not in GP.lower():
			GP = u'Гран-при ' + GP

		GP = self._to_genitive(GP)

		from vdlib.util.string import uni_type

		s = uni_type(year) + ' ' + event + ' ' + GP

		data = { 'fsf': '255', 'nm': s }

		debug(url)

		r = self.post_request(url, headers=headers, data=data)
		if r.ok:
			bs = BeautifulSoup(clean_html(r.text), 'html.parser')
			for tr in bs.find_all('tr', class_='hl-tr'):
				try:
					a = tr.find('a', class_='torTopic')
					title = a.get_text()
					page_url = a['href'] 
				except AttributeError:
					continue

				if str(year) not in title:
					continue
				indx = title.find('[')
				info = title[indx:].strip('[]')
				title = title[:indx].strip()
				seeds = tr.find('span', class_='seedmed').get_text()
				if seeds == '0':
					continue

				skip_wrong = False
				for p in RuTracker.parts(title):
					if u'практика' in p:
						m = re.search('(\d)', p)
						if m:
							n = m.group(1)
							if n not in event:
								skip_wrong = True
								break

				if skip_wrong:
					continue

				yield {
					'title': title,	'info': info,
					'page_url': page_url,
					'seeds': seeds,
					'leechers': tr.find('span', class_='leechmed').get_text(),
					'dl_link': 'https://%s/forum/' % self.baseurl + tr.find('a', class_='f-dl')['href']
				}

	def poster(self, page_url):
		req = self.get_request(page_url)
		if req.ok:
			bs = BeautifulSoup(clean_html(req.text), 'html.parser')
			var = bs.find('var', class_='postImg postImgAligned img-right')
			if var:
				result = var.get('title')
				return result

	def magnet_link(self, page_url):
		req = self.get_request(page_url)
		if req.ok:
			bs = BeautifulSoup(clean_html(req.text), 'html.parser')
			for a in bs.find_all('a', href=re.compile(r'^magnet:')):
				return a['href']
		return None

	@staticmethod
	def parts(title):
		pts = title.split(' / ')
		if len(pts) < 2:
			pts = title.split('. ')
			if len(pts) < 2:
				pts = title.split(u' – ')

		return pts
	
	@staticmethod
	def clean_title(title, year=None):
		#import vsdbg
		#vsdbg._bp()

		parts = RuTracker.parts(title)

		skips = [u'формула', u'сезон', u'этап', u'Формула', u'Сезон', u'Этап', u'ФОРМУЛА', u'СЕЗОН', u'ЭТАП']

		if len(parts) > 1:
			new = []
			for part in parts:
				_part = part.lower()

				do_cont = False
				for skip in skips:
					if skip in _part:
						do_cont = True
				if do_cont:
					continue

				if re.search(r'\d+/\d\d', part):
					continue
				if year and str(year) in part:
					continue

				new.append(part)

			return ' / '.join(new)
		else:
			return title


