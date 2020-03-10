# coding: utf-8

import requests, re, json

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from bs4 import BeautifulSoup
from base import clean_html

class RuTracker(object):

	season_parts = {
		'660': [2020],
		'1551': [ year for year in range(2012, 2019+1) ],
		'626': [ year for year in range(1950, 2011+1) ]
	}

	@staticmethod
	def part_for_year(year):
		year = int(year)
		for part in RuTracker.season_parts:
			if year in RuTracker.season_parts[part]:
				return part
		return None

	def __init__(self, settings):
		self.settings = settings
		self._session = None

	@property
	def session(self):
		if not self._session:
			self._session = self.make_session()
		return self._session

	@property
	def username(self):
		return self.settings.rt_username

	@property
	def password(self):
		return self.settings.rt_password

	@property
	def baseurl(self):
		return self.settings.rt_baseurl

	def make_session(self):
		s = requests.Session()
		if not self.check_login(s):
			self.login(s)
		return s

	def check_settings(self):
		if not self.username or not self.password or not self.baseurl:
			return False
		return True

	def check_login(self, session):
		try:
			js = json.loads(self.settings.rt_cookies)
		except ValueError:
			return False
		"""
		except BaseException:
			import xbmc
			xbmc.log(self.settings.rt_cookies)
			return False
		"""
		resp = session.get('http://%s/forum/index.php' % self.baseurl, cookies=js)
		if re.compile('<input.+?type="text" name="login_username"').search(resp.text):
			return False
		return True

	def login(self, session):
		pageContent = session.get('http://%s/forum/login.php' % (self.baseurl))
		captchaMatch = re.compile(
			'(//static\.t-ru\.org/captcha/\d+/\d+/[0-9a-f]+\.jpg\?\d+).+?name="cap_sid" value="(.+?)".+?name="(cap_code_[0-9a-f]+)"',
			re.DOTALL | re.MULTILINE).search(pageContent.text)
		data = {
			'login_password': self.password,
			'login_username': self.username,
			'login': '%C2%F5%EE%E4',
			'redirect': 'index.php'
		}
		if captchaMatch:
			captcha = 'http:'+captchaMatch.group(1)
			#captchaCode = self.askCaptcha('http:'+captchaMatch.group(1))
			captchaCode = ''
			if captchaCode:
				data['cap_sid'] = captchaMatch.group(2)
				data[captchaMatch.group(3)] = captchaCode
			else:
				return False
			
		r = session.post(
			'http://%s/forum/login.php' % self.baseurl,
			data=data,
			allow_redirects = False
		)

		if r.ok:
			c = requests.utils.dict_from_cookiejar(r.cookies)
			self.settings.set_setting('rt_cookies', json.dumps(c))

			return c

	def get_request(self, url, data=None, headers=None, cookies=None):
		return self.session.get(url, data=data, headers=headers, cookies=cookies)

	def post_request(self, url, data=None, headers=None, cookies=None):
		return self.session.post(url, data=data, headers=headers, cookies=cookies)

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

		s = unicode(year) + ' ' + event + ' ' + GP
		s = s.encode('cp1251')

		data = { 'fsf': '255', 'nm': s }

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
		import vsdbg
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

	def torrent_download(self, url, path):
		t = re.search('(\d+)$', url).group(1)
		referer = 'http://%s/forum/viewtopic.php?t=%s' % (self.baseurl, t)
		headers = {'Referer': referer,
					'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 YaBrowser/15.10.2454.3658 Safari/537.36',
					'Origin': 'http://%s' % self.baseurl, 
					'Upgrade-Insecure-Requests': '1'
					}
		data = { 't': t	}

		js = json.loads(self.settings.rt_cookies)
	

		r = self.post_request(url, headers=headers, data=data, cookies=js)
		if r.ok:
			with open(path, 'wb') as fd:
				for chunk in r.iter_content(chunk_size=128):
					fd.write(chunk)			

if __name__ == '__main__':
	try:
		import rutracker_test
		rutracker_test.test()
	except ImportError:
		pass