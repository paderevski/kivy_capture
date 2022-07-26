#!/usr/bin/env bash
cd ~/github/projects/kivy_capture
source ./env/bin/activate
KIVY_METRICS_DENSITY=2 python StopMotionApp.py --size 3840x2160

