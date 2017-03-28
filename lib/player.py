# coding: utf-8

import torrent2httpplayer, aceplayer, yatpplayer
import time, sys
import xbmc, xbmcgui, xbmcplugin
from log import debug

def play_torrent(path, settings, info_dialog, title_dialog):
	player = None
	try:
		debug(path)

		if settings.torrent_player == 'torrent2http':
			player = torrent2httpplayer.Torrent2HTTPPlayer(settings)
		elif settings.torrent_player == 'YATP':
			player = yatpplayer.YATPPlayer()
		elif settings.torrent_player == 'Ace Stream':
			player = aceplayer.AcePlayer(settings)

		if not player:
			return

		player.AddTorrent(path)
		while not player.CheckTorrentAdded():
			info_dialog.update(0, u'Проверяем файлы', ' ', ' ')
			time.sleep(1)

		files = player.GetLastTorrentData()['files']
		playable_item = files[0]

		player.StartBufferFile(0)

		if not player.CheckTorrentAdded():
			info_dialog.update(0, u'%s: проверка файлов' % title_dialog)

		while not info_dialog.iscanceled() and not player.CheckTorrentAdded():
			xbmc.sleep(1000)

		info_dialog.update(0, u'%s: буфферизация' % title_dialog)

		while not player.CheckBufferComplete():
			percent = player.GetBufferingProgress()
			if percent >= 0:
				player.updateDialogInfo(percent, info_dialog)

			time.sleep(1)

		info_dialog.update(0)
		info_dialog.close()

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
		if player:		
			player.close()
	#return url	