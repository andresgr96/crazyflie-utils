import threading
import numpy as np
import logging
import time
import cflib.crtp
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.swarm import CachedCfFactory
import pygame
from pygame.locals import *
import matplotlib.pyplot as plt
from matplotlib import cm, colors
from matplotlib import patches
import json
import os

experiment_name = "camera_0"
# if not os.path.isdir(experiment_name):
#     os.mkdir(experiment_name)
#     print("The directory is created.")
# else:
#     print("The experiment directory already exists!!q!")
#     exit()

num_cf = 3
max_num_cf = 10
max_datapoint = 8000
data = []
id_list = []
log_all = np.zeros([max_datapoint*num_cf, 6])
steps_last = np.zeros([1, num_cf])
steps = np.zeros(max_num_cf)
xs = np.zeros(max_num_cf)
ys = np.zeros(max_num_cf)
zs = np.zeros(max_num_cf)
hxcs = np.zeros(max_num_cf)
hycs = np.zeros(max_num_cf)
hzcs = np.zeros(max_num_cf)

global config
config_file = "./config.json"
with open(config_file, "r") as f:
    config = json.loads(f.read())

def display(str):
    screen.fill((255, 128, 0))
    text = font.render(str, True, (255, 255, 255), (159, 182, 205))
    textRect = text.get_rect()
    textRect.centerx = screen.get_rect().centerx
    textRect.centery = screen.get_rect().centery

    screen.blit(text, textRect)
    pygame.display.update()

def decode_aggdata(noncoded):
    x = int(np.floor(noncoded/np.power(10, 7)))/10
    noncoded = noncoded - x*10*np.power(10, 7)
    y = int(np.floor(noncoded / np.power(10, 5))) / 10
    noncoded = noncoded - y * 10 * np.power(10, 5)
    h = int(np.floor(noncoded / np.power(10, 3))) / 10
    noncoded = noncoded - h * 10 * np.power(10, 3)
    l = noncoded
    return x, y, h, l


def logg_swarm(scf):
    log_config = LogConfig(name="synthLog", period_in_ms=500)
    log_config.add_variable("synthLog.agent_id", "uint8_t")
    log_config.add_variable("synthLog.log_pos_x", "uint8_t")
    log_config.add_variable("synthLog.log_pos_y", "uint8_t")
    log_config.add_variable("synthLog.log_pos_z", "uint8_t")
    log_config.add_variable("synthLog.log_hxc", "uint8_t")
    log_config.add_variable("synthLog.log_hyc", "uint8_t")
    log_config.add_variable("synthLog.log_hzc", "uint8_t")

    with SyncLogger(scf, log_config) as logger:
        for entry in logger:
            agent_id = entry[1]["synthLog.agent_id"]
            # print("Agent ID: ", agent_id)
            x = entry[1]["synthLog.log_pos_x"] * 6.5/255
            y = entry[1]["synthLog.log_pos_y"] * 4.5/255
            z = entry[1]["synthLog.log_pos_z"] * 2.0/255
            hxc = entry[1]["synthLog.log_hxc"] * 1/255
            hyc = entry[1]["synthLog.log_hyc"] * 1/255
            hzc = entry[1]["synthLog.log_hzc"] * 1/255
            xs[int(agent_id-1)] = x
            ys[int(agent_id-1)] = y
            zs[int(agent_id-1)] = z
            hxcs[int(agent_id-1)] = hxc
            hycs[int(agent_id-1)] = hyc
            hzcs[int(agent_id-1)] = hzc
            log_all[int((agent_id - 1) + steps[agent_id - 1] * max_num_cf), :] = x, y, z, hxc, hyc, hzc
            steps[agent_id - 1] = steps[agent_id - 1] + 1


def _take_off(scf):
    cf = scf.cf
    cf.param.set_value("fmodes.if_takeoff", 1)
    cf.param.set_value("fmodes.fmode", 2)
    time.sleep(0.1)


def take_off(swarm):
    swarm.parallel_safe(_take_off)


def _update_goal(scf):
    file_path = 'goal_loci.txt'
    with (open(file_path, 'r') as file):
        # Read the first line from the file
        line = file.readline()

        # Split the line by commas to get a list of number strings
        number_strings = line.strip().split(',')

        # Convert each number string to an integer
        goal_locations = [float(num) for num in number_strings]
        goal_locations = goal_locations * 20
        goal_locations = [int(num) for num in goal_locations]
        out_of_bounds = False

    print("Goal location is: ", goal_locations[0], goal_locations[1], goal_locations[2])

    for gl in goal_locations:
        if gl > 254 or gl < 0:
            out_of_bounds = True

    if out_of_bounds:
        print("Goal location is out of bound!")
    else:
        cf = scf.cf
        cf.param.set_value("fmodes.goal_x", goal_locations[0]*20)
        cf.param.set_value("fmodes.goal_y", goal_locations[1]*20)
        cf.param.set_value("fmodes.goal_z", goal_locations[2]*20)
        print("Goal location is updated to: ", goal_locations[0], goal_locations[1], goal_locations[2])
        cf.param.set_value("flockParams.update_params", 1)
        time.sleep(0.1)


def update_goal(swarm):
    swarm.parallel_safe(_update_goal)

def _land(scf):
    cf = scf.cf
    cf.param.set_value("fmodes.if_land",1)
    time.sleep(0.1)


def land(swarm):
    swarm.parallel_safe(_land)


def _terminate(scf):
    cf = scf.cf
    cf.param.set_value("fmodes.if_terminate",1)
    time.sleep(0.1)


def terminate(swarm):
    swarm.parallel_safe(_terminate)


def _update_param(scf):
    global config
    cf = scf.cf
    #####################
    sigma_base = config["sigma_base"]
    sigma_var = config["sigma_var"]
    k1 = config["k1"]
    k2 = config["k2"]
    alpha = config["alpha"]
    beta = config["beta"]
    kappa = config["kappa"]
    light_max = config["light_max"]
    light_min = config["light_min"]
    flight_height = config["flight_height"]
    umax = config["umax"]
    wmax = config["wmax"]
    u_add = config["u_add"]
    update_params = 1
    #####################
    cf.param.set_value("flockParams.sb_param", sigma_base)
    cf.param.set_value("flockParams.sv_param", sigma_var)
    cf.param.set_value("flockParams.k1_param", k1)
    cf.param.set_value("flockParams.k2_param", k2)
    cf.param.set_value("flockParams.alpha_param", alpha)
    cf.param.set_value("flockParams.beta_param", beta)
    cf.param.set_value("flockParams.kappa_param", kappa)
    cf.param.set_value("flockParams.lmx_param", light_max)
    cf.param.set_value("flockParams.lmn_param", light_min)
    cf.param.set_value("flockParams.fh_param", flight_height)
    cf.param.set_value("flockParams.umax_param", umax)
    cf.param.set_value("flockParams.wmax_param", wmax)
    cf.param.set_value("flockParams.u_add_param", u_add)
    cf.param.set_value("flockParams.update_params", update_params)
    print("update finished")


def update_param(swarm):
    swarm.parallel_safe(_update_param)

def log_swarm(swarm):
    swarm.parallel_safe(logg_swarm)


if __name__ == "__main__":

    uris = {
        # 'radio://0/100/2M/E7E7E7E701',
        # 'radio://0/100/2M/E7E7E7E702',
        # 'radio://0/100/2M/E7E7E7E703',
        # 'radio://0/100/2M/E7E7E7E704',
        # 'radio://0/100/2M/E7E7E7E705',
        # 'radio://0/100/2M/E7E7E7E706',
        'radio://0/100/2M/E7E7E7E704',
        'radio://0/100/2M/E7E7E7E70A',
        # 'radio://0/100/2M/E7E7E7E709',
        'radio://0/100/2M/E7E7E7E708',
    }

    # size_x = 8.0
    # size_y = 6.0
    # norm = colors.Normalize(vmin=50.0, vmax=600.0, clip=True)
    # mapper = cm.ScalarMappable(norm=norm, cmap=cm.inferno)
    #
    # plt.ion()
    # plt.show()

    pygame.init()
    screen = pygame.display.set_mode((320, 240))
    pygame.display.set_caption('Python numbers')
    screen.fill((255, 128, 0))
    font = pygame.font.Font(None, 45)
    done = False
    # for aaa in range(10000):
    #     print(aaa)
    #     time.sleep(0.0005)

    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)
    factory = CachedCfFactory(rw_cache='./cache')
    display_msg = "No key is pressed!"
    last = time.time()
    last_pressed = time.time()
    with Swarm(uris, factory=factory) as swarm:
        thread_1 = threading.Thread(target=log_swarm, args=([swarm]))
        thread_1.start()
        log_index = 0
        # fig = plt.figure()
        # ax = fig.add_subplot(projection='3d')
        # # Initialize scatter plot
        # scat = ax.scatter([], [], [], color="black", s=15)
        # # Initialize quiver plot
        # quiv = ax.quiver([], [], [], [], [], [], color="black")
        # ax.set_xlim(0, 6.5)
        # ax.set_ylim(0, 4.5)
        # ax.set_zlim(0, 2.0)
        while not done:
            pygame.event.pump()
            keys = pygame.key.get_pressed()
            display(display_msg)
            if time.time() - last > 0.5:
                last = time.time()
                ##PLOT##
                # scat._offsets3d = (xs, ys, zs)
                # # Update quiver plot data
                # quiv.remove()  # Currently necessary due to Matplotlib's limitations with 3D quiver updates
                # quiv = ax.quiver(xs, ys, zs, hxcs, hycs, hzcs,
                #                            color="black", length=0.2)
                # # plt.pause(0.0000001)  # Adjust this value as needed for your visualization needs
                # plt.pause(0.1)
                steps_last = steps
                log_index += 1
                ###
            if keys[K_ESCAPE]:
                done = True
            if keys[K_t] and ((time.time() - last_pressed) > 0.5):
                take_off(swarm)
                display_msg = "Takeoff command is sent!"
                last_pressed = time.time()
            elif keys[K_g] and ((time.time() - last_pressed) > 0.5):
                update_goal(swarm)
                display_msg = "Goal location is updated!"
                last_pressed = time.time()
            elif keys[K_l] and ((time.time() - last_pressed) > 0.5):
                land(swarm)
                display_msg = "Land command is sent!"
                last_pressed = time.time()
            elif keys[K_e] and ((time.time() - last_pressed) > 0.5):
                terminate(swarm)
                display_msg = "Emergency terminate command is sent!"
                last_pressed = time.time()
            elif keys[K_u] and ((time.time() - last_pressed) > 0.5):
                with open(config_file, "r") as f:
                    config = json.loads(f.read())
                    print("New config file loaded")
                time.sleep(0.5)
                update_param(swarm)
                display_msg = "Parameters are updated!"
                last_pressed = time.time()
            elif keys[K_q] and ((time.time() - last_pressed) > 0.5):
                display_msg = "Terminate the experiment!"
                last_pressed = time.time()
                np.save(experiment_name + "/log_data_1.npy", log_all)
                np.save(experiment_name + "/steps_last.npy", steps_last)
                exit()
