# coding: utf-8

from __future__ import absolute_import

import re, json
from vdlib.util.log import debug

from vdlib.scrappers.rutracker import RuTrackerBase

from bs4 import BeautifulSoup

try:
	from .base import current_year
except ImportError:
	from base import current_year	# type: ignore

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

	def search(self, event, GP, year):
		if not self.check_settings():
			return

		# tcp://localhost:6668
		"""
		import ptvsd
		ptvsd.enable_attach(secret=None, address = ('0.0.0.0', 6668))	
		ptvsd.wait_for_attach()
		# """

		url = 'http://%s/forum/viewforum.php?f=' % self.baseurl + RuTracker.part_for_year(year)
		headers = {'Referer': url}

		event = event.lower().replace(u'тренировка', u'практика')

		from vdlib.util.string import uni_type

		s = uni_type(year) + ' ' + event + ' ' + GP
		s = s.encode('cp1251')

		data = { 'fsf': '255', 'nm': s }

		debug(url)

		r = self.post_request(url, headers=headers, data=data)
		if r.ok:
			bs = BeautifulSoup(clean_html(r.text), 'html.parser')
			for tr in bs.find_all('tr', class_='hl-tr'):
				try:
					title = tr.find('a', class_='torTopic').get_text()
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
					'seeds': seeds,
					'leechers': tr.find('span', class_='leechmed').get_text(),
					'dl_link': 'http://%s/forum/' % self.baseurl + tr.find('a', class_='f-dl')['href']
				}

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


