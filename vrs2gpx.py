#!/usr/bin/env python
"""
Usage:
    python vrs2gpx.py -q [icao] -p [path] -f [output filename]

Requirements:
    Written for python 3.6
    gpxpy [https://github.com/tkrajina/gpxpy]

Copyright:
    vrs2gpx Copyright 2017, Patrick Montalbano

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    "gpxpy" is Copyright 2011 Tomo Krajina
    "Virtual Radar Server (VRS)" is Copyright 2010 onwards, Andrew Whewell
"""

import gpxpy
import gpxpy.gpx
import json
import os
from multiprocessing import cpu_count, Pool
import datetime
import sys
import argparse
from functools import partial


class Vrs2gpx:
    def scan_icao(filename, query=None):
        """Return filename containing queried Icao from a list of vrs formatted json file list.
        """
        with open(os.path.join(path, filename)) as f:
            data = json.load(f)
        for point in data['acList']:
            if point['Icao'] == query:
                return filename
                break

    def write_gpx(path, filelist, query=None):
        """Return gpx format xml filtered for queried Icao from vrs formatted json file list.

         Short trails:
         Short trails are a list of values that represent the positions
         that the aircraft has been seen in over so-many seconds
         (by default 30 seconds).The array is an array of numbers. The
         numbers are arranged in groups of either 3 or 4, depending on
         whether just positions are being sent or whether the altitude
         or speed is also being sent. If just positions are being sent
         (TT is empty or missing) then the first value is latitude,
         the second value is longitude and the third is the server time
         that the position was seen at UTC in JavaScript ticks.
         If altitude or speeds are also being sent (TT is either 'a' for
         altitude or 's' for speed) then the first value is latitude, the
         second longitude, the third is server time and the fourth is
         either altitude or speed.
         The first group of values represents the earliest position in the
         trail while the last group represents the latest position in the
         trail. If ResetTrail is true then the array contains the entire
         trail over the last 30 seconds, otherwise it just holds the
         coordinates added to the trail since you last fetched the aircraft
         list.
        """
        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        for file in filelist:
            with open(os.path.join(path, file)) as f:
                        data = json.load(f)
            for locs in data['acList']:
                if locs['Icao'] == query:
                    # Use short trails if available
                    if 'Cos' in locs:
                        try:
                            l = int(len(locs['Cos'])/4)
                            for i in range(0, l):
                                elevation = None
                                speed = None

                                latitude = locs['Cos'][0::4][i]
                                longitude = locs['Cos'][1::4][i]
                                timestamp = datetime.datetime.fromtimestamp(locs['Cos'][2::4][i]/1000)
                                if locs['TT'] == 'a':
                                    elevation = locs['Cos'][3::4][i]
                                elif locs['TT'] == 's':
                                    speed = locs['Cos'][3::4][i]
                                else:
                                    pass
                                gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude,
                                                                                  longitude,
                                                                                  time=timestamp,
                                                                                  elevation=elevation,
                                                                                  speed=speed))
                        except:
                            pass
                    # Use Lat Long if available
                    else:
                        try:
                            latitude = locs['Lat']
                            longitude = locs['Long']
                            elevation = locs['alt']
                            timestamp = locs['PosTime']
                            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude,
                                                                              longitude,
                                                                              time=timestamp,
                                                                              elevation=elevation))
                        except:
                            pass
        return gpx.to_xml()

if __name__ == "__main__":
    """When run in terminal, vrs2gpx returns a gpx formatted xml file from a directory of Virtual Radar Server
    formatted .json files for a specified 6-digit Mode S ICAO.
    """
    # TODO: filter file list for json extension. Job will fail if non-json files are present.
    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--icao", default=None,
                        help="A 6 digit Mode 8 ID (required)")
    parser.add_argument("-p", "--path", default="./files",
                        help="Directory containing VRS formatted *.json files. Defaults to ./files.")
    parser.add_argument("-f", "--gpxfilename",
                        default=datetime.datetime.now().isoformat() + ".gpx",
                        help="Output GPX filename. Defaults to iso datetime format.")

    args = parser.parse_args()

    if args.icao != None:
        icao_query = args.icao
    else:
        print("No Icao argument entered. Type vrs2gpx --help for usage.")
        sys.exit()

    path = args.path
    gpxfilename = args.gpxfilename

    # Return a list of files containing the icao query
    cpus = cpu_count()
    print("Using " + str(cpus) + " CPUs. This will take a while...")

    # todo: Cannot get map to run while scan_icao has first argument self.
    with Pool(processes=cpus) as p:
        results = p.map(partial(Vrs2gpx.scan_icao, query=icao_query), os.listdir(path))
        filelist = [x for x in results if x is not None]
    print("Found " + icao_query + " in " + str(len(filelist)) + " files.")

    if len(filelist) > 0:
        # Write GPX
        gpx = Vrs2gpx.write_gpx(path, filelist, icao_query)
        f = open(gpxfilename, "w")
        f.write(gpx)
        f.close()
        print("Wrote " + gpxfilename)
