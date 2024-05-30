import logging
import time

import cflib.crtp
#connect receive send data from Crazyflie
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
#logging, recording of internal states info 
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger

# radio URI of the crazyflie
uri = 'radio://0/100/2M/E7E7E7E708'

def simple_connect():
    """Function to connect with Crazyflie."""
    print("Yeah, I'm connected! :D")
    time.sleep(3)
    print("Now I will disconnect :'(")

if __name__ == '__main__':
    # Initializes low-lev communication drivers for the Crazyflie 
    cflib.crtp.init_drivers()

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
       
        simple_connect()

# check crazyflie is on
# check crazyradio PA is connected to computer
# check crazyflie is not connected to anything else (like the cfclient)