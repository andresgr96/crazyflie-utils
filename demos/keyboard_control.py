import threading
import numpy as np
import logging
import time
import cflib.crtp
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.swarm import CachedCfFactory
import pygame
from pygame.locals import *
import matplotlib.pyplot as plt
from matplotlib import cm, colors
from matplotlib import patches
# from PyP100 import PyP100
import os
import json

uri = 'radio://0/100/2M/E7E7E7E708'
global pos_xs, pos_ys, pos_ls
pos_xs = np.array([])
pos_ys = np.array([])
pos_ls = np.array([])

def display(str):
    screen.fill((255, 128, 0))
    text = font.render(str, True, (255, 255, 255), (159, 182, 205))
    textRect = text.get_rect()
    textRect.centerx = screen.get_rect().centerx
    textRect.centery = screen.get_rect().centery

    screen.blit(text, textRect)
    pygame.display.update()


def log_cf(scf):
    global pos_xs, pos_ys, pos_ls
    log_config = LogConfig(name='Light values', period_in_ms=50)
    # log_config.add_variable('synthLog.light_intensity', 'float')
    log_config.add_variable('stateEstimate.x', 'float')
    log_config.add_variable('stateEstimate.y', 'float')

    with SyncLogger(scf, log_config) as logger:
        for log_entry in logger:
            data = log_entry[1]

            pos_xs = np.append(pos_xs, data['stateEstimate.x'])
            pos_ys = np.append(pos_ys, data['stateEstimate.y'])
            # pos_ls = np.append(pos_ls, data['synthLog.light_intensity'])


def activate_high_level_commander(cf):
    cf.param.set_value('commander.enHighLevel', '1')


def reset_estimator(cf):
    cf.param.set_value('kalman.resetEstimation', '1')
    time.sleep(0.1)
    cf.param.set_value('kalman.resetEstimation', '0')
    time.sleep(1.0)


def takeoff_land(cf, _command):
    commander = cf.high_level_commander
    if _command == 1:
        commander.takeoff(0.5, 2.0)
        time.sleep(3.0)
    elif _command == 2:
        commander.land(0.0, 2.0)
        time.sleep(2.0)
        commander.stop()
    # if _command == 2:
    #     commander.land(0.0, 2.0)
    #     time.sleep(2.0)
    #     commander.stop()
    # if _command == 1:
    #     cf.param.set_value('motorPowerSet.enable', '1')
    #     cf.param.set_value('motorPowerSet.m1', '65000')
    #     cf.param.set_value('motorPowerSet.m2', '65000')
    #     cf.param.set_value('motorPowerSet.m3', '65000')
    #     cf.param.set_value('motorPowerSet.m4', '65000')


def cmd_hover(cf, vx, vy, vyaw, z):
    cf.commander.send_hover_setpoint(vx, vy, vyaw, z)
    time.sleep(0.3)


if __name__ == '__main__':
    cflib.crtp.init_drivers()
    done = False
    altitude = 0.5
    trajectory_id = 1

    start = time.time()
    last_pressed = time.time()

    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    pygame.display.set_caption('Python numbers')
    screen.fill((255, 128, 0))
    font = pygame.font.Font(None, 45)
    display_msg = "No key is pressed!"
    took_off = False
    landed = True

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        cf = scf.cf
        thread_1 = threading.Thread(target=log_cf, args=([scf]))
        thread_1.start()
        activate_high_level_commander(cf)
        reset_estimator(cf)
        while not done:
            pygame.event.pump()
            keys = pygame.key.get_pressed()
            display(display_msg)
            # print("Pos X: ", pos_xs[-1], " Pos Y: ", pos_ys[-1])
            if time.time() - start > 0.5:
                # print(pos_ls[-1])
                start = time.time()
            if keys[K_ESCAPE]:
                done = True
                # takeoff_land(cf, 2)
                # np.save('./light_histogram/log_xs.py', pos_xs)
                # np.save('./light_histogram/log_ys.py', pos_ys)
                # np.save('./light_histogram/log_ls.py', pos_ls)
            if keys[K_UP]:
                cmd_hover(cf, 0.5, 0.0, 0.0, altitude)
                display_msg = "+ X"
                last_pressed = time.time()
            elif keys[K_DOWN]:
                cmd_hover(cf, -0.5, 0.0, 0.0, altitude)
                display_msg = "- X"
                last_pressed = time.time()
            elif keys[K_LEFT]:
                cmd_hover(cf, 0.0, 0.5, 0.0, altitude)
                display_msg = "+ Y"
                last_pressed = time.time()
            elif keys[K_RIGHT]:
                cmd_hover(cf, 0.0, -0.5, 0.0, altitude)
                display_msg = "- Y"
                last_pressed = time.time()
            elif keys[K_q]:
                cmd_hover(cf, 0.0, 0.0, 0.0, altitude+0.2)
                altitude = altitude + 0.2
                display_msg = "+ Z"
                last_pressed = time.time()
            elif keys[K_e]:
                cmd_hover(cf, 0.0, 0.0, 0.0, altitude-0.2)
                altitude = altitude - 0.2
                display_msg = "- Z"
                last_pressed = time.time()
            elif keys[K_t] and ((time.time() - last_pressed) > 0.1):
                takeoff_land(cf, 1)
                took_off = True
                landed = False
                display_msg = "Takeoff"
                print("here")
                last_pressed = time.time()
            elif keys[K_l] and ((time.time() - last_pressed) > 0.1):
                takeoff_land(cf, 2)
                landed = True
                display_msg = "Land"
                last_pressed = time.time()
            elif took_off and not landed:
                cmd_hover(cf, 0.0, 0.0, 0.0, altitude)