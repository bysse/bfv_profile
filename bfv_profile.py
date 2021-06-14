#!/usr/bin/python3

import sys
import json
import urllib.request 
import time
import os.path

TIME_FORMAT_LONG = "%Y-%m-%d %H:%M:%S"
TIME_FORMAT = "%Y-%m-%d %H:%M"

def load(filename):
    with open(filename, "r") as fd:
        return fd.read()

def store(filename, data):
    with open(filename, "w") as fd:
        fd.write(data.decode("utf-8"))

def fetch(profile):
    profile_url = f"https://api.tracker.gg/api/v2/bfv/standard/profile/origin/{profile}?forceCollect=true"
    request = urllib.request.Request(
        profile_url, 
        data=None, 
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
        }
    )
    response = urllib.request.urlopen(request)
    return response.read()

def show_snapshot(snapshot):    
    print("=====", time.strftime(TIME_FORMAT_LONG, snapshot['lastUpdated']), "=====")
    display = lambda x, y: print("  {0:10} {1:>10}".format(x+":", y))

    for k,v in snapshot.items():
        if k == 'lastUpdated':
            continue
        display(k,v)

def duration(seconds):
    h = int(seconds / 3600)
    seconds -= h * 3600
    m = int(seconds / 60)
    seconds -= m * 60
    return f"{h}h {m}m {seconds}s"

def show_diff(profile, s1, s2):
    diff = lambda x: s1[x] - s2[x]
    ratio = lambda x, y: x if y == 0 else x / y
    display = lambda x, y, z: print("  {0:10} {1:>10.4f} [{2:>10.4f}]".format(x+":", y, z))
    displayx = lambda x, y, z: print("  {0:10} {1:>10} [{2:>10}]".format(x+":", y, z))

    dt = time.mktime(s2['lastUpdated']) - time.mktime(s1['lastUpdated'])
    if dt == 0:
        return False

    print("=====", time.strftime(TIME_FORMAT_LONG, s2['lastUpdated']), "=====")
    print("  {0:10} {1:>10} [{2:>10}]".format("Attribute", "Current", "Overall"))
    display("K/D", ratio(diff('kills'), diff('deaths')), ratio(s2['kills'], s2['deaths']))
    display("K/D (assists)", ratio(diff('kills_tot'), diff('deaths')), ratio(s2['kills_tot'], s2['deaths']))
    display("Accuracy", ratio(diff('shots_hit'), diff('shots')), ratio(s2['shots_hit'], s2['shots']))
    displayx("Headshots", diff('headshots'), s2['headshots'])
    displayx("Damage", diff('damage'), s2['damage'])
    print("  {0:10} {1:>10}".format("Playtime:", duration(s2['playtime'])))

    with open(f"history-{profile}.csv", "a") as fd:
        o_time = time.strftime(TIME_FORMAT_LONG, s2['lastUpdated'])
        o_kd = ratio(diff('kills'), diff('deaths'))
        o_kda = ratio(diff('kills_tot'), diff('deaths'))
        o_acc = ratio(diff('shots_hit'), diff('shots'))
        o_hs = s2['headshots']
        o_dmg = s2['damage']
        fd.write(f"{o_time}, {o_kd}, {o_kda}, {o_acc}, {o_hs}, {o_dmg}\n")

    return True

def parse(data):
    try:        
        row = {
            'lastUpdated': time.strptime(data['data']['metadata']['lastUpdated']['value'], "%Y-%m-%dT%H:%M:%S%z")
        }
        
        for segment in data['data']['segments']:
            if segment['type'] != "overview":
                continue
            stats = segment['stats']
            value = lambda x: int(stats[x]['value'])

            row['kills'] = value('kills')
            row['kills_tot'] = value('killsAggregated')
            row['deaths'] = value('deaths')
            row['damage'] = value('damage')
            row['shots'] = value('shotsTaken')
            row['shots_hit'] = value('shotsHit')
            row['headshots'] = value('headshots')
            row['playtime'] = value('timePlayed')

        return row
    except KeyError as e:
        print("ERROR: Unknown data key", e)
        return None


def main(profile, interval=300):
    previous = None
    try:
        if os.path.exists(f"data-{profile}.json"):
            print("# Loading cached data")
            previous = parse(json.loads(load(f"data-{profile}.json")))
        else:
            print("# Fetching profile statistics")
            data = fetch(profile)
            store(f"data-{profile}.json", data)
            previous = parse(json.loads(data))
    except:
        pass        
    print(f"# Loading profile statistcs every {interval} seconds")

    try:
        while True:
            time.sleep(interval)

            # fetch and store the profile on disk
            data = fetch(profile)
            store(f"data-{profile}.json", data)
            current = parse(json.loads(data))

            if current == None:
                print("# ERROR: Failed to fetch profile statistics")
                continue

            if not previous:            
                previous = current            
                continue
            
            if show_diff(profile, previous, current):
                # only switch if the data was updated
                previous = current        
    except KeyboardInterrupt:
        print("Exit")

def syntax():
    print("Syntax: bfv_profile.py (-i <seconds>) <BFV profile>")
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) <= 2:
        syntax()

    interval = 300
    profile = None
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '-i':
            i += 1
            if i >= len(sys.argv):
                print("ERROR: Missing interval")
                syntax()
            interval = int(sys.argv[i])
        else:
            profile = arg
        i += 1

    if not profile:
        print("ERROR: Missing profile name")
        syntax()

    main(profile, interval)

