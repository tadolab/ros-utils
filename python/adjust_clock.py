#!/usr/bin/env python2

import rosbag

import sys
from os.path import basename, dirname, sep

# Script for the Fire Fighter Robot project that allows us to adjust the
# timestamp of topics so that it matches the clock.
# For example, if the topic was recorded at ROS time 10 but the timestamp is
# set to 5, the script subtracts 5 from all the timestamp in the topics
# (including tf). The script only looks for topic names and tf child_frame_id
# with a 'hose' or 'shoot' prefix. Leading slashes (such as '/hose') are ignored.
# After adjusting, a file with the 'new_' prefix is created in the same
# directory as the original bag file.
#
# Usage:
#   ./change_clock.py <bag file> [bag file...]

def normalize_topic(topic, msg):
    if topic == '/tf':
        name = msg.transforms[0].child_frame_id
        stamp = msg.transforms[0].header.stamp
    else:
        name = topic
        try:
            stamp = msg.header.stamp
        except:
            return (None, None)

    name = name.lstrip('/')
    if name.startswith('hose'):
        name = 'hose'
    elif name.startswith('shoot'):
        name = 'shoot'
    else:
        return (None, None)

    return (name, stamp)

def get_clock_stamp(fn):
    clock_stamp = {
        'shoot': {
            'clock': None,
            'stamp': None,
        },
        'hose': {
            'clock': None,
            'stamp': None,
        }
    }

    orig_bag = rosbag.Bag(fn)

    found = False
    for topic, msg, t in orig_bag.read_messages():
        if clock_stamp['shoot']['clock'] and clock_stamp['hose']['clock']:
            found = True
            break

        name, stamp = normalize_topic(topic, msg)

        if name == 'hose' or name == 'shoot':
            clock_stamp[name]['clock'] = t
            clock_stamp[name]['stamp'] = stamp

    return (clock_stamp, found)

def adjust_bag(orig_fn, new_fn):
    clock_stamp, found = get_clock_stamp(orig_fn)

    if not found:
        sys.stderr.write('Clock not found. Are you sure it\'s the right data?\n')
        sys.exit(1)

    print('Diff')
    print('  Hose:  {0:>4}s'.format((clock_stamp['hose']['clock'] -
                                    clock_stamp['hose']['stamp']) / 1e9))
    print('  Shoot: {0:>4}s'.format((clock_stamp['shoot']['clock'] -
                                    clock_stamp['shoot']['stamp']) / 1e9))

    orig_bag = rosbag.Bag(orig_fn)
    new_bag = rosbag.Bag(new_fn, 'w')

    for topic, msg, t in orig_bag.read_messages():
        name, stamp = normalize_topic(topic, msg)

        if name == 'hose' or name == 'shoot':
            diff = clock_stamp[name]['clock'] - clock_stamp[name]['stamp']
        else:
            continue

        if topic == '/tf':
            for transform in msg.transforms:
                transform.header.stamp += diff
        else:
            # Some other topic such as (/hose/scan : LaserScan)
            try:
                msg.header.stamp += diff
            except:
                sys.stderr.write('No header.stamp found for {0}\n'.format(topic))
                continue

        new_bag.write(topic, msg, t)

    new_bag.close()

if len(sys.argv) < 2:
    sys.stderr('Not enough arguments\n')
    sys.exit(1)

for orig_fn in sys.argv[1:]:
    new_fn = dirname(orig_fn) + sep + 'new_' + basename(orig_fn)
    print(basename(orig_fn))
    print('  -> ' + basename(new_fn))
    adjust_bag(orig_fn, new_fn)
