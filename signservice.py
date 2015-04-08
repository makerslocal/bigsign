#!/usr/bin/env python -u

import sys
import os.path
import time
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
import time
import alphasign


class SignFileEventHandler(LoggingEventHandler):
	def __init__(self, filename):
		#self.observer = observer
		self.filename = filename

	def on_modified(self, event):
		print "e=", event
		if not event.is_directory and event.src_path.endswith(self.filename):
			print "file modified: " + self.filename
			print "kicking sign"
			update_from_file(path)

def update_from_file(filename):
	f = open(filename, 'r')
	txt = f.read()
	f.close()
	update_from_signcode(txt)

def update_from_signcode(t):
	##handle inline commands.
	#legacy
	t=t.replace('{fill}','').replace('{hold}','') #legacy shit that we want to throw away
	t=t.replace('{decenders}', alphasign.charsets.TRUE_DESCENDERS_ON) #spelling mistake in legacy stuff lol
	t=t.replace('{slower}', alphasign.speeds.SPEED_1) #legacy for slowest speed
	t=t.replace('{faster}', alphasign.speeds.SPEED_5) #legacy for fastest speed
	#colors
	t=t.replace('{orange}', alphasign.colors.ORANGE)
	t=t.replace('{green}', alphasign.colors.GREEN)
	t=t.replace('{red}', alphasign.colors.RED)
	#finally, line feed.
	t=t.replace('\n', alphasign.constants.CR)
	
	update_sign(t)
	
def update_sign(stuff, lbl="A"): #default to updating normal file.
	normal_state = alphasign.Text(	label=lbl,
					data=stuff,
					size=192,
					mode=alphasign.modes.HOLD,
					position=alphasign.positions.FILL)
	sign.write(normal_state)

if __name__ == "__main__":

	print "sign init..."
	sign = alphasign.Serial(device="/dev/ttySign")
	sign.connect()
	#sign.clear_memory() #pretty sure we don't need this.
	tmp_normal = alphasign.Text(	label="A",
					data="bigsign init...",
					size=192,
					mode=alphasign.modes.HOLD,
					position=alphasign.positions.FILL)
	sign.allocate((tmp_normal,))
	sign.set_run_sequence((tmp_normal,))
	sign.write(tmp_normal)

	print "file init..."
	path = sys.argv[1]
	update_from_file(path)

	print "file watcher init..."
	event_handler = SignFileEventHandler(os.path.basename(path))
	observer = Observer()
	observer.schedule(event_handler, os.path.dirname(path), recursive=False)
	observer.start()
	try:
		while True:
			time.sleep(65535)
	except KeyboardInterrupt:
		observer.stop()
	observer.join()

