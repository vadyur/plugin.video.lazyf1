# coding: utf-8

import torrent2httpplayer, aceplayer, yatpplayer
import time, sys
import xbmc, xbmcgui, xbmcplugin
from log import debug
import pyxbmct

class MyWindow(pyxbmct.AddonDialogWindow):

	def __init__(self, title, data):
		# Вызываем конструктор базового класса.
		super(MyWindow, self).__init__(title)
		# Устанавливаем ширину и высоту окна, а также разрешение сетки (Grid):
		self.setGeometry(850, 550, 1, 1)

		self.has_select_file = False

		self.files = pyxbmct.List('font14', _itemHeight=100)
		self.placeControl(self.files, 0, 0)

		# Связываем клавиатурное действие с методом.
		self.connect(pyxbmct.ACTION_NAV_BACK, self.close)

		self.show_files(data)


	def show_files(self, data):
		self.files = pyxbmct.List('font14')
		self.placeControl(self.files, 0, 0)

		if data:
			for f in data:
				try:
					li = xbmcgui.ListItem(str(f['size'] / 1024 / 1024) + u' МБ | ' + f['name'])
				except:
					li = xbmcgui.ListItem(f['name'])
				li.setProperty('index', str(f['index']))
				self.files.addItem(li)

		self.setFocus(self.files)
		self.connect(self.files, self.select_file)

	def select_file(self):
		debug('select_file')
		self.has_select_file = True
		self.close()


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

		index = 0
		if len(files) == 1:
			playable_item = files[0]
		elif len(files) > 1:
			window = MyWindow(title_dialog, files)
			window.doModal()

			if window.has_select_file:

				# tcp://localhost:6665
				"""
				import ptvsd
				ptvsd.enable_attach(secret=None, address = ('0.0.0.0', 6665))	
				ptvsd.wait_for_attach()
				# """

				cursel = window.files.getSelectedItem()
				index = cursel.getProperty('index')
				for f in files:
					if f['index'] == int(index):
						playable_item = f
			else:
				return
		else:
			return

		player.StartBufferFile(playable_item.get('index'))

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