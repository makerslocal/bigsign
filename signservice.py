#!/usr/bin/env python -u

import datetime
import serial
import sys
import os.path
import time
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
import time
import alphasign
from threading import Timer
import couchdb
import ConfigParser

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

def update_from_signcode(t, lbl="A"):
	##handle inline commands.
	#sign commands
	t=t.replace('{descenders}', alphasign.charsets.TRUE_DESCENDERS_ON) #larger line height to allow characters to go below the bottom (gjq)
	#legacy
	t=t.replace('{fill}','').replace('{hold}','') #legacy shit that we want to throw away
	t=t.replace('{decenders}', alphasign.charsets.TRUE_DESCENDERS_ON) #spelling mistake in legacy stuff lol
	t=t.replace('{slower}', alphasign.speeds.SPEED_1) #legacy for slowest speed
	t=t.replace('{faster}', alphasign.speeds.SPEED_5) #legacy for fastest speed
	#formatting
	t=t.replace('{orange}', alphasign.colors.ORANGE)
	t=t.replace('{green}', alphasign.colors.GREEN)
	t=t.replace('{red}', alphasign.colors.RED)
	t=t.replace('{huge}', alphasign.charsets.DOUBLE_HIGH_ON + alphasign.charsets.DOUBLE_WIDE_ON)
	t=t.replace('{/huge}', alphasign.charsets.DOUBLE_HIGH_OFF + alphasign.charsets.DOUBLE_WIDE_OFF)
	#finally, line feed.
	t=t.replace('\n', alphasign.constants.CR)
	#parts
	now = datetime.datetime.now() #update clock first otherwise the date will never change, idiot
	t=t.replace('{clock}', str(now.day) + ' ' + now.strftime('%b') + ' ' + str(now.year) + ' ' + signtime.call() )
	t=t.replace('{blurb}', blurb_str.call())
	
	update_sign(t, lbl)
	
def update_sign(stuff, lbl="A"): #default to updating normal file.
	normal_state = alphasign.Text(	label=lbl,
					data=stuff,
					size=224,
					mode=alphasign.modes.HOLD,
					position=alphasign.positions.FILL)
	sign.write(normal_state)

def update_sign_alert(stuff="", source=None):
	if stuff != "":
		stuff = "{red}{huge}ALERT{/huge}\nfrom " + ( source if ( source != None ) else "IRC" ) + "\n{green}" + stuff
	return update_from_signcode(stuff, "0")

def update_light(doingit=False):
	if doingit:
		light.write("on")
	else:
		light.write("off")

if __name__ == "__main__":

	print "sign init..."
	sign = alphasign.Serial(device="/dev/ttySign")
	sign.connect()
	#sign.clear_memory() #pretty sure we don't need this.
	tmp_normal = alphasign.Text(	label="A",
					data="bigsign init...",
					size=224,
					mode=alphasign.modes.HOLD,
					position=alphasign.positions.FILL)
	blurb_str = alphasign.String(label="b", size=64)
	#blurb_str.data = "Since 1983!" + alphasign.constants.CR + "(not really)"
	blurb_str.data = "Share it" + alphasign.constants.CR + "with a bro!"
	sign.allocate((tmp_normal,blurb_str))
	sign.set_run_sequence((tmp_normal,))
	for obj in (tmp_normal,blurb_str):
		sign.write(obj)
	now = datetime.datetime.now()
	signtime = alphasign.Time()
	sign.write(signtime.set_format(1)) #24-hour clock
	sign.write(signtime.set(now.hour, now.minute))
	update_sign_alert() #clear any alert

	print "light init..."
	light = serial.Serial("/dev/ttyLight")
	print light.name + " open"

	print "file init..."
	path = sys.argv[1]
	update_from_file(path)

	print "file watcher init..."
	event_handler = SignFileEventHandler(os.path.basename(path))
	observer = Observer()
	observer.schedule(event_handler, os.path.dirname(path), recursive=False)
	observer.start()

	print "rq init..."
	config = ConfigParser.ConfigParser()
	config.read("rqsettings.ini")
	server = couchdb.Server(url=config.get("Server", "url"))
	message_db = server[config.get("Server", "message_db")]
	project_name = config.get("Project", "name")
	def parse_message(message):
		try:
			data = message['data']
		except KeyError:
			print "Message did not have 'data' field."
			return
		nolight = data.get('nolight', False)
		nosound = data.get('nosound', False)
		sender = data.get('sender',None)
		text = data.get('text', None)
		print "got '{text}' from '{fr}'. (nosound={ns}, nolight={nl})".format(text=text, ns=nosound, nl=nolight, fr=sender)
		update_sign_alert(text,sender)
		if not nolight:
			update_light(True)
			t = Timer(10.0, update_light)
			t.start()
		if not nosound:
			sign.beep(	duration=0.1,
					frequency=250, #anything above 0 just means the same freq on our sign
					repeat=1) #that is, do not repeat - just do it once
		tt = Timer(30.0, update_sign_alert)
		tt.start()
		return

	print "ok"
	#observer.join() #what does this do? I just cargo culted it

	for change in message_db.changes(feed='continuous', since='now', heartbeat=1000, filter='project/by_name', name=project_name, include_docs=True):
		parse_message(change['doc'])

