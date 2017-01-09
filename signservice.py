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
import ConfigParser
import paho.mqtt.client as mqtt
import json

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
	#parts
	now = datetime.datetime.now() #update clock first otherwise the date will never change, idiot
	t=t.replace('{clock}', str(now.day) + ' ' + now.strftime('%b') + ' ' + str(now.year) + ' ' + signtime.call() )
	#t=t.replace('{clock}', str(now.day) + ' ' + now.strftime('%b') + ' ' + str(1999) + ' ' + signtime.call() ) #RGN
	t=t.replace('{blurb}', blurb_str.call())
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
	
	update_sign(t, lbl)
	
def update_sign(stuff, lbl="A"): #default to updating normal file.
	normal_state = alphasign.Text(	label=lbl,
					data=stuff,
					size=224,
					mode=alphasign.modes.HOLD,
					position=alphasign.positions.FILL)
	sign.write(normal_state)

def update_sign_alert(stuff="", source=None, type="ALERT"):
	if stuff != "" and type == "ALERT":
		j = json.dumps({'message':stuff,'source':source})
		print j
		if type == "ALERT":
			client.publish(config.get("MQTT","pub"),j)
	if stuff != "" or type != "ALERT":
		stuff = "{red}{huge}" + type + "{/huge}\n" + ( source if ( source != None ) else "IRC" ) + "\n{green}" + stuff
	return update_from_signcode(stuff, "0")

def update_sign_notify(stuff="", source=None, type="NOTICE"):
	if stuff != "" or source != None:
		stuff = "{orange}{huge}" + type + "{/huge}\n" + source + "\n{green}" + stuff
	return update_from_signcode(stuff,"0")

def update_light(doingit=False):
	if doingit:
		light.write("on")
	else:
		light.write("off")

if __name__ == "__main__":

	print "config init..."
	config = ConfigParser.ConfigParser()
	config.read("settings.ini")
	
	print "sign init..."
	sign = alphasign.Serial(device="/dev/ttySign")
	sign.connect()
	#sign.beep(duration=0.1, frequency=250)
	#sign.clear_memory() #pretty sure we don't need this.
	tmp_normal = alphasign.Text(	label="A",
					data="bigsign init...",
					size=224,
					mode=alphasign.modes.HOLD,
					position=alphasign.positions.FILL)
	blurb_str = alphasign.String(label="b", size=64)
	#blurb_str.data = "Forever and ever, a hundred years," # makerslocal.org!"
	blurb_str.data = config.get("Sign","blurb").replace('\\n', alphasign.constants.CR)
	#blurb_str.data = alphasign.colors.COLOR_MIX + "PIG ROAST" + alphasign.constants.CR + alphasign.colors.YELLOW + "@makerslocal256"
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
	def on_connect(client, userdata, flags, rc):
		print("Connected to RQ with result code "+str(rc))
		client.subscribe(config.get("MQTT","alert_sub"))
		client.subscribe(config.get("MQTT","info_sub"))
		client.subscribe(config.get("MQTT","cascade_withdrawal_sub"))
		client.subscribe(config.get("MQTT","cascade_error_sub"))
	def on_alert_message(client, userdata, msg):
		print(msg.topic+" "+str(msg.payload))
		j = json.loads(msg.payload)
		print j
		light = True
		sound = True
		sender = j["nick"]
		text = j["message"]
		print "got '{text}' from '{fr}'. (sound={s}, light={l})".format(text=text, s=sound, l=light, fr=sender)
		update_sign_alert(text,sender)
		if light:
			update_light(True)
			t = Timer(10.0, update_light)
			t.start()
		if sound:
			sign.beep(	duration=0.1,
					frequency=250, #anything above 0 just means the same freq on our sign
					repeat=1) #repeat once - total of 2 beeps
		tt = Timer(30.0, update_sign_alert)
		tt.start()
		return
	def on_info_message(client, userdata, msg):
		print(msg.topic+" "+str(msg.payload))
		j = json.loads(msg.payload)
		update_sign_alert(j["message"], "", "Info")
		sign.beep(duration=0.1,frequency=250,repeat=0)
		tt = Timer(30.0, update_sign_alert)
		tt.start()
		return
	def on_cascade_withdrawal_message(client,userdata,msg):
		print(msg.topic+" "+str(msg.payload))
		j=json.loads(msg.payload)
		print j
		try:
			update_sign_notify("Remaining balance: $" + str(format(j["balance"],'.2f')), j["user"], "KACHUNK")
			if j["balance"] <= 2:
				sign.beep(duration=0.1,frequency=250)
		except:
			pass
		tt = Timer(30.0, update_sign_notify)
		tt.start()
		return
	def on_cascade_error_message(client,userdata,msg):
		print(msg.topic + " " + str(msg.payload))
		j = json.loads(msg.payload)
		print j
		try:
			detail = j["message"] + " :("
			if j["error"] == "NO_USER_FUNDS":
				detail = "I know who you are, " + j["user"] + ", you just don't have any money!"
			update_sign_notify(detail,"","NOT KACHUNK")
			sign.beep(duration=0.1,frequency=250)
		except:
			pass
		tt = Timer(30.0,update_sign_notify)
		tt.start()
		return
		
	client = mqtt.Client()
	client.on_connect = on_connect
	client.message_callback_add(config.get("MQTT","alert_sub"),on_alert_message)
	client.message_callback_add(config.get("MQTT","info_sub"),on_info_message)
	client.message_callback_add(config.get("MQTT","cascade_withdrawal_sub"),on_cascade_withdrawal_message)
	client.message_callback_add(config.get("MQTT","cascade_error_sub"),on_cascade_error_message)
	client.connect(config.get("MQTT","host"))

	print "ok"
	client.loop_forever()

