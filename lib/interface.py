# coding: utf-8

from simpleplugin import Plugin
from lib.f1news import F1News
from lib.rutracker import RuTracker
from lib.log import debug

import lazyf1images
import xbmc, xbmcaddon, xbmcgui, xbmcplugin
import sys, json, os


plugin = Plugin()
f1news = F1News(res_path=os.path.join(plugin.path, 'resources'))
rutracker = RuTracker(plugin)

_addon_title_ = '[COLOR=FFFFFFFF]Lazy[/COLOR] [COLOR=FFFF0000]F1[/COLOR]'
_addon = xbmcaddon.Addon()

@plugin.action()
def root(params):
	xbmcplugin.setContent(int(sys.argv[1]), 'files')

	return [{'label': u'Уикэнд: ' + f1news.weekend_title(), 'url': plugin.get_url(action='weekend')},
			{'label': u'Текущий сезон', 'url': plugin.get_url(action='curr_season')},
			{'label': u'Предыдущие сезоны', 'url': plugin.get_url(action='prev_seasons')},
			{'label': u'Прямая трансляция', 'url': plugin.get_url(action='live')}
	]


@plugin.action()
def weekend(params):
	xbmcplugin.setContent(int(sys.argv[1]), 'files')

	return [ item for item in f1news.weekend_schedule(plugin.get_url) ]


@plugin.action()
def curr_season(params):
	xbmcplugin.setContent(int(sys.argv[1]), 'episodes')

	return [ item for item in f1news.calendar(2017, plugin.get_url) ]

def item_by_year(year):
	return {'label': str(year), 
			'thumb': lazyf1images.seasons() +'current/bg.jpg', 
			'fanart': lazyf1images.seasons() + str(year) + '/bg.jpg', 
			'is_playable': False, 'url': plugin.get_url(action='show_season', year=str(year))}

@plugin.action()
def prev_seasons(params):
	xbmcplugin.setContent(int(sys.argv[1]), 'tvshows')

	return [item_by_year(item) for item in range(2016, 1999-1, -1)]

@plugin.action()
def show_season(params):
	xbmcplugin.setContent(int(sys.argv[1]), 'episodes')

	return [ item for item in f1news.calendar(params['year'], plugin.get_url) ]

def gp_event(event, params):
	url = plugin.get_url(action='search', event=event.encode('utf-8'), season=params['season'], GP=params['GP'])
	return {'label': event, 'url': url}

@plugin.action()
def show_gp(params):
	xbmcplugin.setContent(int(sys.argv[1]), 'files')
	return [ 
			gp_event(u'Квалификация', params),
			gp_event(u'Гонка', params)
	]

def search_item(item):
	title = "[%s/%s] %s" % (item['seeds'], item['leechers'], RuTracker.clean_title(item['title']))
	#title = title + '\n' + item['info']
	w = 0
	h = 0
	if '720p' in item['info']:
		w = 1280
		h = 720
		title += ' / 720p'
	elif '1080' in item['info']:
		w = 1920
		h = 1080
		title += ' / 1080'

	lang = ''
	part = item['info'].split(',')[-1].lower()
	if 'en' in part or 'ru' in part or 'int' in part:
		title += ' [' + part + ']'

	info = {}
	if w:
		info['width'] = w
	if h:
		info['height'] = h

	stream_info = { 'video': info }
	return {'label': title, 'label2': item['info'], 'is_playable': True, 'stream_info': stream_info, 
			'url': plugin.get_url(action='list_torrent', dl_link=item['dl_link'])
	}

@plugin.action()
def search(params):
	if not rutracker.check_params():
		xbmcgui.Dialog().notification(_addon_title_, u'Введите логин/пароль для RuTracker')
		_addon.openSettings()

	items = [search_item(item) for item in rutracker.search(params['event'].decode('utf-8'), params['GP'].decode('utf-8'), params['season'])] 
	if len(items) > 0: 
		return items
	else:
		xbmcgui.Dialog().notification(_addon_title_, u'Пока ничего нет')

def path2url(path):
	import urllib, urlparse
	return urlparse.urljoin('file:', urllib.pathname2url(path))

def torrents_path():
	path = xbmc.translatePath('special://temp/lazyf1')
	return path.decode('utf-8')

@plugin.action()
def list_torrent(params):
	path = xbmc.translatePath('special://temp/lazyf1.torrent').decode('utf-8')
	rutracker.torrent_download(params['dl_link'], path)

	#import urllib
	#url = 'plugin://plugin.video.yatp/?action=list_files&torrent=' + urllib.quote(path2url(path))
	#url = 'plugin://plugin.video.torrenter/?action=playSTRM&url=' + urllib.quote(path2url(path))

	try:
		import torrent2httpplayer, time
		plugin.torrents_path = torrents_path
		player = torrent2httpplayer.Torrent2HTTPPlayer(plugin)

		player.AddTorrent(path)
		while not player.CheckTorrentAdded():
			time.sleep(1)

		files = player.GetLastTorrentData()['files']
		playable_item = files[0]

		player.StartBufferFile(0)

		while not player.CheckBufferComplete():
			time.sleep(1)

		playable_url = player.GetStreamURL(playable_item)
		debug(playable_url)

		handle = int(sys.argv[1])
		list_item = xbmcgui.ListItem(path=playable_url)

		xbmc_player = xbmc.Player()
		xbmcplugin.setResolvedUrl(handle, True, list_item)

		while not xbmc_player.isPlaying():
			xbmc.sleep(300)

		debug('!!!!!!!!!!!!!!!!! Start PLAYING !!!!!!!!!!!!!!!!!!!!!')

		# Wait until playing finished or abort requested
		while not xbmc.abortRequested and xbmc_player.isPlaying():
			player.loop()
			xbmc.sleep(1000)

		debug('!!!!!!!!!!!!!!!!! END PLAYING !!!!!!!!!!!!!!!!!!!!!')
	finally:
		player.close()
	#return url

@plugin.action()
def play(params):
	return params.url

def channelName2uniqueId(channelname):
	query = {
			"jsonrpc": "2.0",
			"method": "PVR.GetChannels",
			"params": {"channelgroupid": "alltv", "properties" :["channelnumber"]},
			"id": 1
			}
	res = json.loads(xbmc.executeJSONRPC(json.dumps(query, encoding='utf-8')))
	debug(res)
	"""
	# translate via json if necessary
	trans = json.loads(str(ChannelTranslate))
	for tr in trans:
		if channelname == tr['name']:
			debug("Translating %s to %s" % (channelname,tr['pvrname']))
			channelname = tr['pvrname']
	"""

	if 'result' in res and 'channels' in res['result']:
		res = res['result'].get('channels')
		for channels in res:
			#debug("TVHighlights %s - %s" % (channels['label'],channelname))
			# priorize HD Channel
			if channelname+" HD".lower() in channels['label'].lower(): 
				debug("TVHighlights found  HD priorized channel %s" % (channels['label']))
				return channels['uniqueid']
			if channelname.lower() in channels['label'].lower(): 
				debug("TVHighlights found  channel %s" % (channels['label']))
				return channels['uniqueid']
	return 0 

def get_channels():
	"""
	import ptvsd
	ptvsd.enable_attach(secret=None, address = ('0.0.0.0', 6666))
	ptvsd.wait_for_attach()
	"""

	ret = json.loads(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "PVR.GetChannelGroups", "params":{"channeltype":"tv"} }'))
	debug(ret)
	try:
		channelgroups = ret['result']['channelgroups']
	except KeyError:
		return

	for channelgroup in channelgroups:
		#Get Channels
		ret = json.loads(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "PVR.GetChannels", "params":{"channelgroupid" : ' + str(channelgroup['channelgroupid']) + '} }'))
		try:
			channels = ret['result']['channels']
		except KeyError:
			return
		for channel in channels:
			if u'Матч! Арена' in channel['label'] or u'Setanta Sports HD' in channel['label']:
				channel['url'] = plugin.get_url(action='tvchannel', **channel)
				channel['is_folder'] = False
				yield channel

@plugin.action()
def live(params):
	xbmcplugin.setContent(int(sys.argv[1]), 'files')

	return [ item for item in get_channels() ]

def jsonrpc(query):
	ret = json.loads(xbmc.executeJSONRPC(json.dumps(query)))	

@plugin.action()
def tvchannel(params):
	query = {
			"jsonrpc": "2.0",
			"id": 1,
			"method": "Player.Open",
			"params": {"item": {"channelid": int(params['channelid'])}}
			}
	res = jsonrpc(query) 