# Getting started

This document guides you how to [install the SurroRTG SDK](#sdk-installation), [configure the Admin panel](#admin-panel-configuration) and running a [simple game](simple_game).

To get everything running smoothly you should follow the order in which you do the steps

1. [setup raspberry pi](#SDK-installation)
2. [install streamer](#Installing-Surrogate-Streamer)
3. [install controller sdk](#Installing-Surrogate-Controller)
4. [create a game on surrogate.tv](#Admin-panel-configuration)
5. [configure your streamer and controller](#Configuration-file)
6. [test simple game](#Running-template-game)
7. [create systemd unit from controller](#Creating-systemd-unit-for-your-code)

You might need to jump betweens steps 5-7 in case you missed something so remember to look around if you run in trouble. Also take a look at the [troubleshooting](troubleshooting).

you should also checkout our help for using some related [linux tools](systemctl_and_journalctl)

## Requirements

To get started with installation and running a sample game, these are the hardware requirements:

1. [Rasperry Pi](https://www.raspberrypi.org/) single board computer,
   for example model 3B+ or 4
2. A +16GB micro SD card
3. An official [Raspberry Pi Camera](https://www.raspberrypi.org/products/camera-module-v2/)
   or some USB camera, check the [support list](camera_support)

## SDK installation

The SDK installation can be done with two different ways:  
[Method 1:](#method-1-installing-a-pre-made-image)
flashing a premade image file to a sd card
(recommended)  
[Method 2:](#method-2-manual-installation)
manual installation on top of an existing raspbian image
(for advanced users only)

### Method 1: installing a pre made image

<strong>Not yet supported, please follow manual installation</strong>

### Method 2: manual installation

#### Setting up Raspberry Pi

First follow Raspberry Pi's [general setup](https://projects.raspberrypi.org/en/projects/raspberry-pi-setting-up). <strong>Note: Choose Raspberry Pi OS (other) -> Raspberry Pi OS Lite (32-bit) as the operating system </strong>
to install official Raspian image. We recommend setting up your internet connection and enabling ssh-connection via sudo raspi-config by following [raspi-config](https://www.raspberrypi.org/documentation/configuration/raspi-config.md#) setup. Alternatively, you can do everything on your host computer after flashing the image to an sd card by following [headless-wifi-setup](https://www.raspberrypi.org/documentation/configuration/wireless/headless.md#) and [headless-ssh-setup](https://www.raspberrypi.org/documentation/remote-access/ssh/README.md#) to modify the boot-partition of the sd card with ssh and wpa_supplicant.conf files.

If you are going to use ssh connection to control the raspberrypi, please get the ip-address of the raspberrypi by running on the raspberrypi terminal

```
ip addr
```

or by some other means (nmap tool or similar)

When done, open up the terminal (`ctrl + alt + t`) or connect via ssh to the raspberry pi and first let's make sure that everything is up to date by running

```
sudo apt update
sudo apt full-upgrade
sudo reboot
```

#### Installing Surrogate Streamer

Next we will install Surrogate streamer module and configuration files. The following commands add our custom repository and its key to your apt-sources and installs our srtg-streamer apt-package.

```
sudo sh -c 'echo deb https://apt.surrogate.tv/ streamer main >> /etc/apt/sources.list'

sudo apt-key adv --keyserver hkps://keys.openpgp.org --recv-keys 8C794AFF2B546ADC

sudo apt-get update

sudo apt install srtg-streamer
```

Now you should have our streamer installed on your raspberry pi. However it is not yet running as you haven't configured the settings and started it. You can see that the installation was succesful by checking the status of the streamer module.

```
sudo systemctl status srtg
```

The installed configuration file is located in /etc/srtg/srtg.toml, you can edit it with the following commands, or with your favorite text editor.

```
sudo nano /etc/srtg/srtg.toml
```

We will get back to the configurations and getting the streamer to work after we have installed the Surrogate Controller SDK.

#### Installing Surrogate Controller

First we need to install git and some other depencies.

```
sudo apt-get install python3-setuptools python3-pip pigpio python3-pigpio libatlas-base-dev git

sudo systemctl enable pigpiod

sudo systemctl daemon-reload

sudo systemctl start pigpiod
```

After this we can clone the github repository. If you specify a folder name the folder will be used instead of the default folder name from github.

```
cd <folder you want to download the git folder>
git clone GIT_URL_HERE <optional_folder_name>
```

Now before installing required python packages. Let's make sure we are using the correct python and pip versions.

```
python --version
```

if this returns "Python 2.7.16" then try running:

```
python3 --version
```

this should return "Python 3.7.X". Our SDK requires Python 3.7 or later to run. Next lets confirm that pip is using the correct version

```
pip3 --version
```

this should return version and python version that is bound to it should state "(python 3.7).

Now that python/python3 and pip/pip3 are using python 3.7 or greater version. We will install sdk dependiencies by running

```
sudo pip3 install -r requirements.txt
```

this will install all required packages that are defined in requirements.txt. If you will later add your own packages, you will need to install them manuall by running

```
sudo pip3 install <package>
```

The reason we are installing the python packages as super-user (sudo) is that your controller code will be running as systemd unit that is executed as sudo and thus needs to have the packages installed in the correct location. This will be later changed to use python virtual enviroments but at the moment this is the only approach supported out-of-the-box.

## Admin panel configuration

Your own game can be controlled from the game's Admin panel.

To get one, you must first create a new game. Create a new game by going to
[surrogate.tv's Admin page](https://www.surrogate.tv/admin/)
and click `Create a new game`. <strong>Note: you must have an account and login to create the game</strong>

After that choose game name, title and short ID. Then choose the type of game.
For now, choose a game type of `arcade`. All of these can be edited later.

This will create you a new Surrogate game, with Admin panel to
`www.surrogate.tv/admin/game/<SHORT_ID_YOU_CHOSE>`. From the Admin panel,
you can turn the game online from the switch on the top left corner.
Now the game should be online on `www.surrogate.tv/game/<SHORT_ID_YOU_CHOSE>`

Next you will need to copy your robot token from the admin panel to the [configuration file](#configuration-file).

<strong>You will need to continue the tutorial to get your streamer and controller connected to the game.</strong>

## Configuration file

As mentioned, the configuration file that is used both by the srtg and the controller is located at /etc/srtg/srtg.toml. You need sudo privilidges to edit the file. <strong>Note: you will need to restart the systemd units to activate the changes</strong>

As a reminder, you can restart the systemd modules by running:

```
sudo systemctl restart srtg
sudo systemctl restart controller
```

you can see how to create the systemd unit for controller [here](#Creating-systemd-unit-for-your-code)

Here is how your config file should look like.

```toml
device_id = "<INSERT ROBOT NAME HERE>"

[game_engine]
url = ""https://ge.surrogate.tv/signaling""

token = "<INSERT TOKEN HERE>"



[rtc_config]
[[rtc_config.ice_servers]]
urls = "stun:stun.l.google.com:19302,stun:stun1.l.google.com:19302,stun:stun2.l.google.com:19302,stun:stun3.l.google.com:19302,stun:stun4.l.google.com:19302"

[[sources]]
kind = "video"
label = "main"

[sources.video_params]
#possible values v4l2, h264_passthrough, csi-rpi
type = "v4l2"
width = 1920
height = 1080
framerate = 30
#v4l2_dev = "path to your video device: /dev/videoX" needed if you have multiple cameras connected
#optional capture format: raw, mpjeg. Defaults to mpjeg or available one
#capture_format = mpjeg

#Audio optional, requires knowledge of alsa
#[[sources]]
#kind = "audio"
#label = "main"

```

If you want to know what resolutions and formats your camera supports use v4l2-utils (you need to install v4l2-utils first):

```
v4l2-utils -d /dev/video<ID> --list-formats-ext
```

## Running template game

At this point we should have the `streamer` working if you have a camera connected and configured properly.

Now that you have everything installed and a game
with Admin panel configured correctly, we are ready to run the [simple-game-template](simple_game).

For testing we can run the python code manually on the terminal.

```
sudo python3 -m game_templates.simple_game
```

This game creates you a switch and joystick inputs that can be used to control a device. You should be able to test the inputs from the admin panel preview.

<strong>Note: if you want that your code runs constantly and starts automatically after boots, you should setup a systemd unit [this way](#creating-systemd-unit-for-your-code). </strong>
Now you are ready to move to beginner friendly [easy games to hook up](easy_games_to_hook_up)
section or to more advanced [custom game creation](custom_game_creation), where we explain in
detail how the games work!

## Creating systemd unit for your code

Below is example contents of the existing "controller-rpi.service" file that is located in the sdk root folder. You will need to make sure that the following options are correct:
<strong>WorkingDirectory:</strong> has absolute path to your sdk root folder, <strong>ExecStart</strong> has the correct python path inside the sdk folder.

```
[Unit]
Description=Surrogate robot control software
After=network.target pigpiod.service
Wants=pigpiod.service
StartLimitIntervalSec=0
[Service]
Type=simple
Restart=always
RestartSec=10
WorkingDirectory=/home/pi/srtg-python
ExecStart=/usr/bin/python3 -m game_templates.simple_game
[Install]
WantedBy=multi-user.target
```

then run the setup-system.sh script to update and reload your new systemd module. If you have already created the systemd unit and you have not changed the file you are running (ExecStart), you can just reload the systemd unit with

```
sudo systemctl restart controller
```

otherwise, you must run

```
./setup-systemd
```

to start the systemd unit for the first time.