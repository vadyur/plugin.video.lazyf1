# coding: utf-8

import os
import requests
import re
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

try:
    from .f1base import current_year
except ImportError:
    from f1base import current_year

from vdlib.util.log import debug
from vdlib.scrappers.base import clean_html
import lazyf1images


MSK = timezone(timedelta(hours=3), 'MSK')


class Championat(object):

    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.100 Safari/537.36'}

    # Без этой cookie сайт отдаёт заглушку с JS-редиректом на SberID
    cookies = {'unity_pause_sso': '1'}

    root_url = 'https://www.championat.ru'

    first_season = 2009

    tournament_ids = {
        2009: 7, 2010: 24, 2011: 42, 2012: 71, 2013: 97, 2014: 247, 2015: 293,
        2016: 345, 2017: 422, 2018: 469, 2019: 523, 2020: 583, 2021: 621,
        2022: 689, 2023: 741, 2024: 834, 2025: 922, 2026: 1032
    }

    tracks_path = lazyf1images.tracks()

    track_map = {
        u"Мельбурн": "melbourne",
        u"Шанхай": "shanghai",
        u"Сахир": "sakhir",
        u"Бахрейн": "sakhir",
        u"Сочи": "sochi",
        u"Барселона": "barcelona",
        u"Монте-Карло": "monaco",
        u"Монако": "monaco",
        u"Монреаль": "montreal",
        u"Баку": "baku",
        u"Шпильберг": "redbullring",
        u"Сильверстоун": "silverstone",
        u"Будапешт": "hungaroring",
        u"Модьород": "hungaroring",
        u"Хоккенхайм": "hockenheim",
        u"Нюрбург": "nuerburgring",
        u"Нюрбургринг": "nuerburgring",
        u"Спа": "spa",
        u"Монца": "monza",
        u"Марина Бей": "singapore",
        u"Марина-Бей": "singapore",
        u"Сингапур": "singapore",
        u"Куала-Лумпур": "sepang",
        u"Сепанг": "sepang",
        u"Сузука": "suzuka",
        u"Остин": "austin",
        u"Мехико": "mexico",
        u"Сан-Паулу": "interlagos",
        u"Абу-Даби": "yasmarina",
        # схемы этих трасс взяты с f1-ua.com, фоновых bg.jpg для них нет
        u"Валенсия": "valencia",
        u"Дели": "buddh",
        u"Джидда": "jeddah",
        u"Доха": "lusail",
        u"Зандворт": "zandvoort",
        u"Имола": "imola",
        u"Йонам": "yeongam",
        u"Лас-Вегас": "lasvegas",
        u"Ле-Кастелле": "paulricard",
        u"Мадрид": "madring",
        u"Майами": "miami",
        u"Портимау": "portimao",
        u"Скарперия-э-Сан-Пьеро": "mugello",
        u"Стамбул": "istanbul"
    }

    tracks_with_fanart = {
        "austin", "baku", "barcelona", "hungaroring", "interlagos",
        "melbourne", "mexico", "monaco", "montreal", "monza", "nuerburgring",
        "redbullring", "sakhir", "sepang", "shanghai", "silverstone", "singapore",
        "sochi", "spa", "suzuka", "yasmarina"
    }

    def __init__(self, res_path, storage={}):
        self.res_path = res_path
        self.storage = storage

        self._calendars = {}
        return super(Championat, self).__init__()

    @staticmethod
    def make_url(url):
        if url.startswith('http'):
            return url
        return Championat.root_url + url

    def _get(self, url, **kwargs):
        # сайт обычно отвечает за 1-2 сек, но изредка подвисает - одна повторная попытка
        for attempt in (1, 2):
            try:
                return requests.get(url, headers=self.headers, cookies=self.cookies, verify=False, timeout=(5, 15), **kwargs)
            except requests.exceptions.RequestException as e:
                debug('championat: attempt {} failed: {}'.format(attempt, e))
                if attempt == 2:
                    raise

    def http_get(self, url):
        url = self.make_url(url)
        resp = self._get(url)
        if 'SberID' in resp.text[:2000]:
            debug('championat: SberID stub, retry with utm_auth=false')
            resp = self._get(url, params={'utm_auth': 'false'})
        return resp

    def _soup(self, url):
        try:
            resp = self.http_get(url)
        except requests.exceptions.RequestException as e:
            debug('championat: {} unavailable: {}'.format(url, e))
            return None
        if resp.status_code == requests.codes.ok:
            return BeautifulSoup(clean_html(resp.text), 'html.parser')

    def tournament_id(self, year):
        year = int(year)
        if year not in self.tournament_ids:
            soup = self._soup('/auto/_f1.html')
            if soup:
                for a in soup.find_all('a', href=re.compile(r'^/auto/_f1/tournament/\d+/$')):
                    m = re.match(r'(\d{4}) ', a.get_text(' ', strip=True))
                    if m:
                        self.tournament_ids[int(m.group(1))] = int(a['href'].split('/')[-2])
        return self.tournament_ids.get(year)

    @staticmethod
    def _parse_calendar(soup):
        ''' Возвращает список этапов:
            {'number': int, 'place': str, 'GP': str, 'events': [{'name': str, 'dt': datetime}]} '''
        stages = []
        table = soup.find('table', class_='tournament-calendar__table')
        if not table:
            return stages

        stage = None
        for tr in table.find_all('tr'):
            classes = tr.get('class', [])
            if 'tournament-calendar__head' in classes:
                m = re.match(r'Этап\s+(\d+)\.\s*(.+)', tr.get_text(' ', strip=True))
                if m:
                    stage = {'number': int(m.group(1)), 'place': m.group(2), 'GP': '', 'events': []}
                    stages.append(stage)
                else:
                    # тесты и прочее, что не является этапом чемпионата
                    stage = None
            elif 'tournament-calendar__row' in classes and stage is not None:
                td_date = tr.find('td', class_='tournament-calendar__date')
                td_name = tr.find('td', class_='tournament-calendar__name')
                if not td_date or not td_name:
                    continue
                try:
                    dt = datetime.strptime(td_date.get_text(strip=True), '%d.%m.%Y %H:%M').replace(tzinfo=MSK)
                except ValueError:
                    continue

                GP, _, name = td_name.get_text(' ', strip=True).partition('. ')
                if not stage['GP']:
                    stage['GP'] = GP
                # 'Гонка (58 кругов, 306.124 км)' -> 'Гонка'
                name = re.sub(r'\s*\(.*\)\s*$', '', name)
                stage['events'].append({'name': name, 'dt': dt})

        return [s for s in stages if s['events']]

    def season(self, year):
        year = int(year)
        if year not in self._calendars:
            stages = []
            tid = self.tournament_id(year)
            if tid:
                soup = self._soup('/auto/_f1/tournament/%d/calendar/' % tid)
                if soup:
                    stages = self._parse_calendar(soup)
            self._calendars[year] = stages
        return self._calendars[year]

    def track(self, stage):
        for part in stage['place'].split(','):
            key = self.track_map.get(part.strip())
            if key:
                return key

    def current_stage(self):
        ''' Этап, который идёт сейчас или будет следующим; прошедший держится до следующего дня после гонки '''
        now = datetime.now(MSK)
        for stage in self.season(current_year()):
            if stage['events'][-1]['dt'] + timedelta(days=1) >= now:
                return stage

    def weekend_title(self):
        stage = self.current_stage()
        return stage['GP'] if stage else ''

    def weekend_fanart(self):
        stage = self.current_stage()
        key = self.track(stage) if stage else None
        return self.tracks_path + key + '/bg.jpg' if key in self.tracks_with_fanart else ''

    def weekend_schedule(self, get_url):
        stage = self.current_stage()
        if not stage:
            return

        from vdlib.util.string import colored

        now = datetime.now(MSK)
        occurred = []
        upcoming = []
        for event in stage['events']:
            if event['dt'] <= now:
                title = event['name']
                action = 'search'
                event_time = None
                occurred.append((title, action, event_time))
            else:
                event_time = event['dt'].astimezone().strftime('%d.%m %H:%M')
                title = colored(u'{} [{}]'.format(event['name'], event_time), 'FF808080')
                action = 'nothing'
                upcoming.append((title, action, event_time))

        for title, action, event_time in list(reversed(occurred)) + upcoming:
            yield { 'label': title,
                    'is_playable': False,
                    'event_time': event_time,
                    'url': get_url(action=action,
                                    event=title,
                                    season=str(current_year()),
                                    GP=stage['GP'])}

    def calendar(self, year, get_url):
        year = int(year)
        for stage in self.season(year):
            race = stage['events'][-1]
            for event in stage['events']:
                if event['name'].startswith(u'Гонка'):
                    race = event

            city = stage['place'].split(',')[0].strip()

            item = {'is_playable': False}
            item['label'] = u'%s %s (%s)' % (race['dt'].strftime('%d.%m'), stage['GP'], city)

            infovideo = {'year': year, 'genre': 'sport', 'season': year,
                        'episode': stage['number'], 'tracknumber': stage['number'], 'title': item['label'],
                        'studio': 'Formula One Management', 'tvshowtitle': 'Formula One Championship',
                        'premiered': '1950-05-13' }

            key = self.track(stage)
            if key:
                item['thumb'] = self.tracks_path + key + '/map.png'
                item['art'] = {'thumb': item['thumb'], 'poster': item['thumb']}
                if key in self.tracks_with_fanart:
                    item['fanart'] = item['art']['fanart'] = self.tracks_path + key + '/bg.jpg'
                try:
                    # res_path - обычный путь на диске; vdlib.filesystem.fopen под Kodi
                    # читает через xbmcvfs и отдаёт str вместо bytes
                    path = os.path.join(self.res_path, 'tracks', key, 'info.txt')
                    if os.path.exists(path):
                        with open(path, 'rb') as info:
                            data = info.read()
                        try:
                            infovideo['plot'] = data.decode('utf-8-sig')
                        except UnicodeDecodeError:
                            infovideo['plot'] = data.decode('cp1251')
                except Exception as e:
                    debug('championat: track info: {}'.format(e))

            item['info'] = {'video': infovideo }
            item['url'] = get_url(action='show_gp', season=str(year), GP=stage['GP'])

            yield item
