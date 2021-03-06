#!/usr/bin/env python

### Author: Matt Buchovecky - mbuchove@ucla.edu
# script that takes an optional argument for the date and target collection and calculates angular separation and elevation of each target from the moon. 

# written for python2 - python3 will require editing of print statements 
# e.g. print("text"), -> print("text",end="")

import sys, operator, argparse
import ephem, subprocess
from math import ceil 
#import inspect

#host & port info 
#hostName="veritase.sao.arizona.edu"
hostName="romulus.ucsc.edu"
portNum=''

#setting up ephem observer object for veritas
veritas = ephem.Observer()
veritas.lat = '31:40.51'
veritas.lon = '-110:57.132'
veritas.elevation = 1268

#def main()
def is_number(s):
    try: 
        float(s)
        return True
    except ValueError:
        return False

#argument parser
parser = argparse.ArgumentParser(description="Takes optional arguments to specify date and source collection, and min / max moon distances. If no arguments are specified, will choose from all psf sources to make an ordered list appropriate for taking a PSF measurement, as well as suggested exposure times for each source. For a more general look at elevation and moon distance, see moonDist.py..")

parser.add_argument('--date', default=veritas.date, help="Specify DATE (in UT) in the format \"YYYY/MM/DD HH:MM:SS\"   don\'t forget the quotation marks. The default value is today's date.")

parser.add_argument('--minMoonDist', default=0., type=float, help="The minimum distance in degrees that a source should be from the moon to include it in the list. The default value is 30 degrees.") 

parser.add_argument('--maxMoonDist', default=180., type=float, help="The maximum distance in degrees that a source should be from the moon, to prevent backlighting and arm shadows. The default value is 90 degrees.")

parser.add_argument('--minElevation', default=20., type=float, help="The minimum elevation in degrees you would like to look at. The default is 20 degrees")

parser.add_argument('--maxElevation', default=90., type=float, help="The minimum elevation in degrees you would like to look at. The default is 90 degrees")

parser.add_argument('--sortBy',default='elevation', help="The parameter by which to sort. The allowable values are elevation (default), moonDist, magnitude, azimuth")

parser.add_argument('--mag',default=5.0, type=float, help="The minimum desired brightness, default magnitude of 5.0")

parser.add_argument('--targets', default='primary_targets', help="Specifies collection of targets in the database. Allowed values for TARGETS (or any list of multiple lists separated by commas): psf_stars (default), yale_bright_star, yale_bright_stars_5.0 -- or any valid VERITAS source collection\nOther collections: moonlight_targets, moonlight_bright, primary_targets, secondary_targets, blazar_filler_targetsGRB, filler_targets, blank_sky, next_day_analysis, lat_highe, reduced_HV_targets, snapshot_targets, survey_crab, survey_cygnus, UV_filter_targets, all")

parser.add_argument('--print-doublets', dest='printDoublets', action='store_true', help="print occurrences of doublet stars")
parser.set_defaults( printDoublets = True )

parser.add_argument('--suppress', dest='suppress', action='store_true', help="suppress additional messages and columns")
parser.set_defaults( suppress = False )

parser.add_argument('--reverse', dest='reverseSort', type=bool, default=True, help="Reverse the order of your sort, true by default.")

parser.add_argument('--noCuts',help = 'displays results for all targets in the list, even if they fail the moon distance and elevation cuts', action = "store_true")

parser.add_argument('--checkProximity', type=float, default=-0.1, help="Prints out a warning if another source is closer than this value in degrees. Not very useful when using all target lists")

args = parser.parse_args()

# setting date/time to user-spefied value (or default to current date/time)
veritas.date = args.date
# letting user know the date and target collection used.
print
print "Date and time used (in UT): %s" %veritas.date
if not args.suppress:
    print "Will select sources between %s and %s degrees from the moon and above %s degrees elevation.." %(args.minMoonDist, args.maxMoonDist, args.minElevation)
    print "Generating an ordered list of sources to use for specified measurement using targets in %s collection..." %args.targets
    print "All parameters listed in degrees except for the exposure (recommended time in seconds, for PSF measurement)"

# MySQL command, runs on command line through subprocess
targetList = args.targets.split(",")
#for collection in args.targets.split(","):
for n in range(0, len(targetList) ):
    if n == 0:
        execCMD = "SELECT tblObserving_Collection.source_id,ra,decl,epoch FROM tblObserving_Sources JOIN tblObserving_Collection ON tblObserving_Sources.source_id = tblObserving_Collection.source_id  WHERE tblObserving_Collection.collection_id='%s'" %targetList[n]
    else:
        execCMD = execCMD + " OR tblObserving_Collection.collection_id='%s'" %targetList[n]


sqlOut = subprocess.Popen(["mysql","-h","%s" %(hostName),"-P","%s" %(portNum),"-u", "readonly", "-D","VERITAS", "--execute=%s" %(execCMD)], stdout=subprocess.PIPE)

# stores query results
QUERY, err = sqlOut.communicate()
if QUERY == "":
    print
    print "Query result is empty. Make sure date and target collection provided are valid. Going to crash now :'("
    exit(1)

# dict for sorting/writing stars and their info 
moonlightSources = {} 
maxNameLength = 0 
# loop through all objects in the bright moonlight list
# calculating and printing out angular separation from moon
for count,source in enumerate(QUERY.rstrip().split("\n")):
    # skip header in query results
    if count == 0:
        continue
        # parsing through query results
        sourceName = source.split("\t")[0]
        sourceRA = float( source.split("\t")[1] ) # if is_number(sourceRA) else sourceRA = '-'
        sourceDEC = float ( source.split("\t")[2] ) 
        sourceEpoch = source.split("\t")[3]
        splitName = sourceName.split()
        if len(splitName) > 2 and is_number(splitName[1]) == True:
            magnitude =  float( splitName[1] ) 
        else:
            magnitude = '-'
            
  if len(sourceName) > maxNameLength:
      maxNameLength = float(len(sourceName))

  # makes sure same epoch is used
  veritas.epoch = float(sourceEpoch)

  # Define ephem moon object and calculate position (ra, dec) and phase
  TheMoon = ephem.Moon(veritas)
  TheMoon.compute(veritas)
  illum = TheMoon.moon_phase*100.

  moonReflection = ephem.FixedBody(TheMoon.ra,TheMoon.dec)

  # Get angular separation of moon and target
  degFromMoon = 180./ephem.pi * ephem.separation((TheMoon.ra,TheMoon.dec),(sourceRA,sourceDEC))

  # Define ehpem object for source, to get elevation
  sourceObj = ephem.FixedBody()
  sourceObj._ra = sourceRA
  sourceObj._dec = sourceDEC
  sourceObj.compute(veritas)

  # check for any sources that are too close to another bright source to be distinguished
  if args.printDoublets:
      minSourceDist = float("inf")
      for count2,sourceComp in enumerate(QUERY.rstrip().split("\n")):
          if count2 == 0: 
              continue
              sourceCmpName = sourceComp.split("\t")[0]    
              sourceCmpRA = float( sourceComp.split("\t")[1] )
              sourceCmpDEC = float( sourceComp.split("\t")[2] )
              sourceCmpEpoch = sourceComp.split("\t")[3]
              sourceCmpObjCmp = ephem.FixedBody()
              sourceCmpObjCmp._ra = sourceCmpRA
              sourceCmpObjCmp._dec = sourceCmpDEC
              sourceCmpObjCmp.compute(veritas)
              sourceDist = 180./ephem.pi * ephem.separation((sourceRA,sourceDEC),(sourceCmpRA,sourceCmpDEC))
              if sourceCmpName != sourceName:
                  if sourceDist < minSourceDist: 
                      minSourceDist = sourceDist 
                      if sourceDist < args.checkProximity: # used to print out bright sources that are too close to each other, less than half a degree apart
                          sourceDistString = "WARNING! These sources are very close! "+sourceName+" and "+sourceCmpName+" are "+str(sourceDist)+" degrees from each other!\nRA: "+str(sourceRA)+" DEC: "+str(sourceDEC)+" RA: "+str(sourceCmpRA)+" DEC: "+str(sourceCmpDEC)
                          print(sourceDistString)
                          
  sourceEl = sourceObj.alt*180./ephem.pi # elevation of source
  sourceAz = sourceObj.az*180./ephem.pi # azimuth of source 

  moonlightSources[sourceName]=(sourceEl, sourceAz, degFromMoon, magnitude, minSourceDist)
  #moonlightSources[sourceName]=[(sourceEl, sourceAz, degFromMoon, magnitude)]

# end of for loop


# sort the sources by selected criteria 
sortChoiceDict = {'elevation': 0, 'azimuth': 1, 'moonDist': 2, 'magnitude': 3}
sortIndex = sortChoiceDict.get(args.sortBy, None)
sorted_sources = moonlightSources.items()
if sortIndex != None:
    sorted_sources.sort( key = lambda x:x[1][int(sortIndex)], reverse=args.reverseSort ) 
else:
    else:
        print ( "sortBy argument %s not recognized, not sorting!" % args.sortBy )

# the dictionary could be directly sorted, or 
#sorted_sources = sorted(moonlightSources.iteritems(), key=operator.itemgetter(1), reverse=args.reverseSort)
#def getKey(item):
#  return item[sortIndex]
#sorted_sources = sorted(moonlightSources, key=getKey, reverse=args.reverseSort)

# for first column 
columnTitle = "Source"
columnLength = ceil(maxNameLength/8.)*8.
columnTabs = int( ceil( (columnLength-len(columnTitle))/8.) )
print("")
#sys.stdout.write( columnTitle )
print(columnTitle),
for x in range(0, columnTabs):
    print('\t'),
    col_string = "Elevation\tAzimuth\t\tMoonDist"
    if not args.suppress:
        col_string = col_string + "\tExp.\tSdist"
        print(col_string)
        print("-----------------------------------------------------------------")
        #print sorted_sources
        for source in sorted_sources:
            name = source[0] 
            el = source[1][0] # distance from moon 
            az = source[1][1] # azimuth 
            dist = source[1][2] # elevation 
            magnitude =  source[1][3]
            sourceDist = source[1][4]

# check that source meets parameters 
if el > args.minElevation and el < args.maxElevation and dist > float(args.minMoonDist) and dist < float(args.maxMoonDist) and ( magnitude == '-' or magnitude < args.mag ) or args.noCuts == True:
    # recommend time for exposure based on source magnitude 
    if type(magnitude) is not float:
        exposure = '-'
    elif magnitude > 4.:
        exposure = 2.0 
    elif magnitude > 3.:
        exposure = 1.5
    elif magnitude > 2.:
        exposure = 1.0
    else:
        exposure = 0.5
        
    length = len(name)
    numTabs = int( ceil( (columnLength-length-1)/8. ) ) 
    print(name),
    for i in range (0, numTabs):
        print("\t"),
        row_string = "%0.2f\t\t%0.2f\t\t%0.2f" %(el, az, dist)
        if not args.suppress:
            row_string = row_string + "\t\t%s\t%0.2f" %(exposure, sourceDist)
            print(row_string)

print("-----------------------------------------------------------------")
print("The Moon is %0.2f%% illuminated" % illum)
print(TheMoon.dec) 

sys.exit(0) # great job 

#if __name__ == '__main__':
#main()

# some unused code for finding available functions 
#fbdy = ephem.FixedBody()
#l = dir(fbdy)
#print l 
