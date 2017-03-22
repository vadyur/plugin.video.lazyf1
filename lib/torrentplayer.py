# -*- coding: utf-8 -*-
import log
from log import debug
import os, re, filesystem

class TorrentPlayer(object):

	@staticmethod
	def is_playable(name):
		filename, file_extension = os.path.splitext(name)
		return file_extension in ['.mkv', '.mp4', '.ts', '.avi', '.m2ts', '.mov']

	def AddTorrent(self, path):
		#raise NotImplementedError("def ###: not imlemented.\nPlease Implement this method")
		self.path = path

	def CheckTorrentAdded(self):
		#raise NotImplementedError("def ###: not imlemented.\nPlease Implement this method")
		return filesystem.exists(self.path)

	@staticmethod
	def Name(name):
		try:
			return name.decode('utf-8')
		except UnicodeDecodeError:
			import chardet
			enc = chardet.detect(name)
			#debug('UnicodeDecodeError detected', log.lineno())
			# debug(enc['confidence'])
			# debug(enc['encoding'])
			if enc['confidence'] > 0.7:
				try:
					name = name.decode(enc['encoding'])
				except UnicodeDecodeError:
					pass
				return name
			else:
				log.print_tb()

	def GetLastTorrentData(self):
		#raise NotImplementedError("def ###: not imlemented.\nPlease Implement this method")

		data = None
		with filesystem.fopen(self.path, 'rb') as torr:
			data = torr.read()

		if data is None:
			return None

		from bencode import BTFailure
		try:
			from bencode import bdecode
			decoded = bdecode(data)
		except BTFailure:
			debug("Can't decode torrent data (invalid torrent link?)")
			return None

		info = decoded['info']

		import hashlib
		from bencode import bencode
		self.info_hash = hashlib.sha1(bencode(info)).hexdigest()
		#debug(self.info_hash)

		name = '.'
		playable_items = []
		try:
			if 'files' in info:
				for i, f in enumerate(info['files']):
					# debug(i)
					# debug(f)
					name = os.sep.join(f['path'])
					size = f['length']
					#debug(name)
					if TorrentPlayer.is_playable(name):
						playable_items.append({'index': i, 'name': TorrentPlayer.Name(name), 'size': size})
					name = TorrentPlayer.Name(info['name'])
			else:
				playable_items = [ {'index': 0, 'name': TorrentPlayer.Name(info['name']), 'size': info['length'] } ]
		except UnicodeDecodeError:
			return None

		return { 'info_hash': self.info_hash, 'announce': decoded['announce'], 'files': playable_items, 'name': name }

	def StartBufferFile(self, fileIndex):
		pass

	def CheckBufferComplete(self):
		pass

	def GetBufferingProgress(self):
		pass

	def GetStreamURL(self, playable_item):
		pass

	def loop(self):
		pass

