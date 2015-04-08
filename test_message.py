# thanks to http://stackoverflow.com/questions/279237/import-a-module-from-a-relative-path for these next bits.
import os, sys, inspect
# realpath() will make your script run, even if you symlink it :)
cmd_folder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile( inspect.currentframe() ))[0]))
if cmd_folder not in sys.path:
	sys.path.insert(0, cmd_folder)

# use this if you want to include modules from a subfolder
cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"alphasign")))
if cmd_subfolder not in sys.path:
	sys.path.insert(0, cmd_subfolder)



import time
import alphasign
from collections import defaultdict


def main():
  sign = alphasign.Serial(device="/dev/ttySign")
  sign.connect()
  #sign.clear_memory()
  #return #if you are just clearing the sign's memory this is enough.

#  sign.beep(	duration=0.8,
#		frequency=250, #anything above 0 just means the same freq on our sign
#		repeat=0) #that is, do not repeat - just do it once

  t = ' '.join(sys.argv[1:])

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
  
  #print len(t)
  #t = "12345678901234567890123456789012345678901234567890"
  #t=t[:47]
  #print t
  #t = "fuck"
 
  print "about to burn this:"
  print t

  normal_state = alphasign.Text(	label="A",
					data=t,
					size=192,
					mode=alphasign.modes.HOLD,
					position=alphasign.positions.FILL)

  # allocate memory for these objects on the sign
  #sign.allocate((normal_state,))

  # tell sign to only display the counter text
  #sign.set_run_sequence((normal_state,))

  # write objects
  for obj in (normal_state,):
    sign.write(obj)

if __name__ == "__main__":
  main()
