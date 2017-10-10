import sys
import os
import time
from telepot.loop import MessageLoop

# Change the current directory
cwd = os.path.dirname(sys.argv[0])
os.chdir(cwd)
sys.path.append('../resources/modules')
import BotClass as bc
import HelperClass as hc

test=hc.splintergetdata()
test.start('CZ1003','F')
