# coding: utf-8

import requests
import re
from bs4 import BeautifulSoup
from base import clean_html, current_year
from log import debug
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


	def __init__(self, res_path, *args, **kwargs):
		self.root_soap = self._get_root_soap()
		self.res_path = res_path
		self._preview_soap = None
		return super(F1News, self).__init__(*args, **kwargs)

	def _get_root_soap(self):
		resp = requests.get('https://www.f1news.ru', headers=self.headers, verify=False)
		if resp.status_code == requests.codes.ok:
			html = clean_html(resp.text)
			soup = BeautifulSoup(html, 'html.parser')
			return soup

	def _get_champ_soap(self, year):
		resp = requests.get('https://www.f1news.ru/Championship/%s/' % str(year), headers=self.headers, verify=False)
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
			for selector in ['div.widget.stream.widget_danger > div.widget_head > div > span', 
							'#sidebar > div.widget.widget_danger.gp-widget > div.widget_head > div > span']:
				try:
					return self.root_soap.select(selector)[0].get_text()
				except IndexError:
					pass 
		return 'No weekend_title'

	def weekend_url(self):
		if self.root_soap:
			try:
				tbl = self.root_soap.select('div.widget.stream.widget_danger > div.widget_body.stream_list > div > table')[0]
				for a in tbl.find_all('a'):
					if 'preview.shtml' in a['href']:
						return a['href']
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
		if self.root_soap:
			for a in self.root_soap.find_all('a', class_='red', attrs={'href': '/lc/'}):
				tr = a.parent.parent
				try:
					title = tr.find('td').get_text()
				except AttributeError:
					continue
					
				yield {'label': title, 'is_playable': False, 
						'url': get_url(action='search', event=title.encode('utf-8').strip('\n\r\t '), season=str(current_year()), GP=self.weekend_title().encode('utf-8').strip('\n\r\t '))}

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
						import urlparse
						res = urlparse.urlparse(TDs[1].img['src'])
						res = urlparse.ParseResult(res.scheme if res.scheme else 'https', res.netloc, res.path, res.params, res.query, res.fragment)
						item['thumb'] = urlparse.urlunparse(res)  

					item['info'] = {'video': infovideo }
					debug(item)
				except:
					pass
				item['url'] = get_url(action='show_gp', season=str(year), GP=TDs[2].get_text().encode('utf-8'))

				yield item
