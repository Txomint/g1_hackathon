#!/usr/bin/env python3.10
"""
Robot camera subprocess.  ── FROZEN FILE, DO NOT EDIT ──

NOT meant to be run directly — core/camera.py spawns it.  Copied unchanged from
g1_control/camera/_video_fetcher.py.

Initialises the Unitree SDK, calls VideoClient.GetImageSample() in a tight
loop, and writes each JPEG frame to stdout as:
    [4-byte big-endian length][raw JPEG bytes]
"""
import struct
import sys
import time
from pathlib import Path

SDK = Path(__file__).resolve().parents[2] / "unitree_sdk2_python"
if str(SDK) not in sys.path:
    sys.path.insert(0, str(SDK))

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.video.video_client import VideoClient

iface = sys.argv[1] if len(sys.argv) > 1 else "enp3s0"

ChannelFactoryInitialize(0, iface)
client = VideoClient()
client.SetTimeout(3.0)
client.Init()
time.sleep(1.5)  # wait for DDS participant discovery before first RPC call

out = sys.stdout.buffer

# Call GetImageSample at maximum speed — the bridge's ROS2 timer controls
# the actual publish rate, so no sleep throttle is needed here.
while True:
    code, data = client.GetImageSample()
    if code == 0 and data:
        jpeg = bytes(data)
        out.write(struct.pack(">I", len(jpeg)))
        out.write(jpeg)
        out.flush()
    else:
        sys.stderr.write(f"GetImageSample error code={code}\n")
        sys.stderr.flush()
