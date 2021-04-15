# coding: utf-8

import requests
import re
from bs4 import BeautifulSoup
from .base import clean_html, current_year
from vdlib.util.log import debug
import lazyf1images

class F1News(object):

	headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.100 Safari/537.36',
				'upgrade-insecure-requests':'1'}

	champ_soaps = {}

	tracks_path = lazyf1images.tracks()

	track_map = {"ru-f1news": 
		{u"Альберт-парк":"melbourne",
		u"Мельбурн":"melbourne",
		u"Шанхай":"shanghai",
		u"Сахир":"sakhir",
		u"Сочи":"sochi",
		u"Барселона":"barcelona",
		u"Монте-Карло":"monaco",
		u"Монреаль":"montreal",
		u"Баку":"baku",
		u"Ред Булл Ринг":"redbullring",
		u"Шпильберг":"redbullring",
		u"Сильверстоун":"silverstone",
		u"Хунгароринг":"hungaroring",
		u"Будапешт":"hungaroring",
		u"Хоккенхайм":"hockenheim",
		u"Нюрбургринг":"nuerburgring",
		u"Спа":"spa",
		u"Монца":"monza",
		u"Марина-Бей":"singapore",
		u"Сингапур":"singapore",
		u"Сепанг":"sepang",
		u"Сузука":"suzuka",
		u"Остин":"austin",
		u"Мехико":"mexico",
		u"Сан-Паулу":"interlagos",
		u"Яс-Марина":"yasmarina"
		}
	}

	root_url = 'https://www.f1news.ru'

	@staticmethod
	def make_url(url):
		if url.startswith(F1News.root_url):
			return url

		return F1News.root_url + url


	def __init__(self, res_path, *args, **kwargs):
		self.root_soap = self._get_root_soap()
		self.res_path = res_path
		self._preview_soap = None
		return super(F1News, self).__init__(*args, **kwargs)

	def _get_root_soap(self):
		resp = requests.get(self.root_url, headers=self.headers, verify=False)
		if resp.status_code == requests.codes.ok:
			html = clean_html(resp.text)
			soup = BeautifulSoup(html, 'html.parser')
			return soup

	def _get_champ_soap(self, year):
		resp = requests.get(self.make_url('/Championship/%s/') % str(year), headers=self.headers, verify=False)
		if resp.status_code == requests.codes.ok:
			html = clean_html(resp.text)
			soup = BeautifulSoup(html, 'html.parser')
			return soup

	def champ_soap(self, year):
		year = str(year)
		if year not in self.champ_soaps:
			self.champ_soaps[year] = self._get_champ_soap(year)

		return self.champ_soaps.get(year)

	@property
	def curr_champ_soap(self, year):
		return self.champ_soap(current_year())

	def weekend_title(self):
		if self.root_soap:
			div = self.root_soap.find('div', class_='widget_title')
			if div:
				return div.span.get_text()
		return 'No weekend_title'

	def weekend_url(self):
		if self.root_soap:
			try:
				ul = self.root_soap.find('ul', class_='gp-widget-menu')
				for a in ul.find_all('a'):
					if 'preview.shtml' in a['href']:
						return self.make_url(a['href'])
			except IndexError:
				pass 

	@property
	def preview_soap(self):
		if not self._preview_soap:
			url = self.weekend_url()
			if url:
				resp = requests.get(url, headers=self.headers, verify=False)
				if resp.status_code == requests.codes.ok:
					html = clean_html(resp.text)
					self._preview_soap = BeautifulSoup(html, 'html.parser')
				
		return self._preview_soap

	def weekend_fanart(self):
		if self.preview_soap:
			div = self.preview_soap.find('div', class_="post_head")
			if div:
				div = div.find('div', class_="post_thumbnail")
				if div:
					img = div.find('img')
					if img:
						return img['src']
		return ''

	def weekend_schedule(self, get_url):
		def _weekend_schedule(occurred_event):
			if self.root_soap:
				for div_name in self.root_soap.find_all('div', class_='gp-widget-item__name'):

					div_time = div_name.find_next_sibling('div', class_='gp-widget-item__date')
					if not div_time:
						continue

					from vdlib.util.string import colored
					try:
						if occurred_event:
							title = div_name.a.get_text()
							action = 'search'
						else:
							title = colored(u'{} [{}]'.format(div_name.span.get_text(), div_time.get_text()), 'FF808080')
							action = 'nothing'
					except AttributeError:
						continue

					yield {'label': title, 'is_playable': False, 
							'url': get_url(action=action, event=title.strip('\n\r\t '), season=str(current_year()), GP=self.weekend_title().strip('\n\r\t '))}
		for item in reversed(list(_weekend_schedule(True))):
			yield item
		for item in _weekend_schedule(False):
			yield item

	def calendar(self, year, get_url):
		year = str(year)
		soap = self.champ_soap(year)
		if soap:

			ep_number = 0
			for tr in soap.find('table', class_='f1Table').find_all('tr'):
				if 'firstLine' in tr.get('class', ''):
					continue

				TDs = tr.find_all('td')
				t1 = TDs[0].get_text()
				m = re.match(r'\d+[/.]\d+', t1)
				if not m:
					continue

				ep_number += 1

				item = {'is_playable': False}
				item['label'] = u'%s %s (%s)' % (TDs[0].get_text(), TDs[2].get_text(), TDs[3].get_text())
				try:
					infovideo = {'year': int(year), 'genre': 'sport', 'season': int(year), 
								'episode': ep_number, 'tracknumber': ep_number, 'title': item['label'],
								'studio': 'Formula One Management', 'tvshowtitle': 'Formula One Championship',
								'premiered': '1950-05-13' }
					ru = TDs[3].get_text()
					tm = self.track_map['ru-f1news']
					if ru in tm:
						item['thumb'] = self.tracks_path + tm[ru] + '/map.png'
						item['fanart'] = self.tracks_path + tm[ru] + '/bg.jpg'
						item['art'] = {'thumb': item['thumb'], 'fanart': item['fanart'], 'poster': item['thumb']}
						import filesystem
						path = filesystem.join(self.res_path, 'tracks', tm[ru], 'info.txt')
						debug(path)
						if filesystem.exists(path):
							debug('exists')
							with filesystem.fopen(path, 'r') as info:
								infovideo['plot'] = info.read()
					else:
						#import urlparse
						from vdlib.util import urlparse
						res = urlparse.urlparse(TDs[1].img['src'])
						res = urlparse.ParseResult(res.scheme if res.scheme else 'https', res.netloc, res.path, res.params, res.query, res.fragment)
						item['thumb'] = urlparse.urlunparse(res)  

					item['info'] = {'video': infovideo }
					debug(item)
				except:
					pass
				item['url'] = get_url(action='show_gp', season=str(year), GP=TDs[2].get_text().encode('utf-8'))

				yield item
