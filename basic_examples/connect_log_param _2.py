import logging
import time

import cflib
import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger

# URI to the Crazyflie to connect to
uri = 'radio://0/80/2M/E7E7E7E701'

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

def simple_log(scf, logconf):

    with SyncLogger(scf, logconf) as logger:

        for log_entry in logger:

            timestamp = log_entry[0]
            data = log_entry[1]
            logconf_name = log_entry[2]

            print('[%d][%s]: %s' % (timestamp, logconf_name, data))

            break
...

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    lg_stab = LogConfig(name='Stabilizer', period_in_ms=10)
    lg_stab.add_variable('stabilizer.roll', 'float')
    lg_stab.add_variable('stabilizer.pitch', 'float')
    lg_stab.add_variable('stabilizer.yaw', 'float')

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:

        # simple_connect()

        simple_log(scf, lg_stab)

# check crazyflie is on
# check crazyradio PA is connected to computer
# check crazyflie is not connected to anything else (like the cfclient)

#[1486704][<cflib.crazyflie.log.LogConfig object at 0x7ffb3384a1d0>]: {'stabilizer.roll': -0.054723262786865234, 'stabilizer.pitch': 0.006269464734941721, 'stabilizer.yaw': -0.008503230288624763}