import urlparse
import sys
#from lib.interface import *

"""
def get_params():
	if len(sys.argv) > 2:
		p = urlparse.urlsplit(sys.argv[0]+sys.argv[2])
		print p
		
	return {}
	
	

if True: # len(sys.argv) < 2:
	p = get_params()
	print p
	
	i = Interface()
	i.show_root()
"""

if __name__ == '__main__':
	import lib.interface
	lib.interface.plugin.run()