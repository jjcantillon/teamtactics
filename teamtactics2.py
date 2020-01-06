#!python3
""" Daemon that can publishes iRacing telemetry values at MQTT topics.

Configure what telemery values from iRacing you would like to publish at which
MQTT topic.
Calculate the geographical and astronomical correct light situation on track. 
Send pit service flags and refuel amount to and receive pit commands from
a buttonbox using a serial connection.
 
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.
This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
"""
from distutils.log import info

__author__ = "Robert Bausdorf"
__contact__ = "rbausdorf@gmail.com"
__copyright__ = "2019, bausdorf engineering"
#__credits__ = ["One developer", "And another one", "etc"]
__date__ = "2019/06/01"
__deprecated__ = False
__email__ =  "rbausdorf@gmail.com"
__license__ = "GPLv3"
#__maintainer__ = "developer"
__status__ = "Beta"
__version__ = "0.95"

import sys
import configparser
import irsdk
import os
import time
import json
import logging
from google.cloud import firestore
from datetime import datetime
from datetime import timedelta

from iracing.IrTypes import SyncState

# this is our State class, with some helpful variables
class State:
    ir_connected = False
    date_time = -1
    tick = 0
    lap = 0
    sessionType = ''
    driverIdx = -1
        
# here we check if we are connected to iracing
# so we can retrieve some data
def check_iracing():        
    
    if state.ir_connected and not (ir.is_initialized and ir.is_connected):
        state.ir_connected = False
        # don't forget to reset all your in State variables
        state.date_time = -1
        state.tick = 0
        state.fuel = 0
        state.lap = 0
        state.sessionType = ''
        state.driverIdx = -1

        # we are shut down ir library (clear all internal variables)
        ir.shutdown()
        print('irsdk disconnected')

    elif not state.ir_connected:
        # Check if a dump file should be used to startup IRSDK
        if config.has_option('global', 'simulate'):
            is_startup = ir.startup(test_file=config['global']['simulate'])
            print('starting up using dump file: ' + str(config['global']['simulate']))
        else:
            is_startup = ir.startup()
            if debug:
                print('DEBUG: starting up with simulation')

        if is_startup and ir.is_initialized and ir.is_connected:
            state.ir_connected = True
            # Check need and open serial connection

            print('irsdk connected')

            checkSessionChange()

            collectionName = getCollectionName()
            col_ref = db.collection(collectionName)
            if state.sessionType == 'single':
                try:
                    docs = list(col_ref.stream())
                    if len(docs) > 0:
                        print('Single session, deleting all data in collection ' + collectionName)
                        for doc in docs:
                            doc.reference.delete()
                    
                    col_ref.document('Info').set(getInfoDoc())
                except Exception as ex:
                    print('Firestore error: ' + str(ex))

def checkDriver():
    currentDriver = ir['DriverInfo']['Drivers'][state.driverIdx]['UserName']

    if syncState.currentDriver != currentDriver:
        print('Driver: ' + currentDriver)
        syncState.currentDriver = currentDriver

        # sync state on self driving
        if iracingId == str(ir['DriverInfo']['Drivers'][state.driverIdx]['UserID']):
            collectionName = getCollectionName()
            doc = db.collection(collectionName).document('State').get()
            
            if doc.exists:
                print('Sync state on driver change')
                syncState.fromDict(doc.to_dict())
                # re-set current driver
                syncState.currentDriver = currentDriver
                if debug:
                    print('State: ' + str(syncState.toDict()))
            else:
                print('No state in ' + collectionName)


def getCollectionName():
    teamName = ir['DriverInfo']['Drivers'][state.driverIdx]['TeamName']

    if state.sessionType == 'single':
        car = ir['DriverInfo']['Drivers'][state.driverIdx]['CarPath']
        return str(teamName) + '@' + str(car) + '#' + ir['WeekendInfo']['TrackName'] + '#' + str(syncState.sessionNum)
    else:
        return str(teamName) + '@' + syncState.sessionId + '#' + syncState.subSessionId + '#' + str(syncState.sessionNum)

def getInfoDoc():
    info = {}
    info['Version'] = __version__
    info['Track'] = ir['WeekendInfo']['TrackName']
    info['SessionLaps'] = ir['SessionInfo']['Sessions'][syncState.sessionNum]['SessionLaps']
    info['SessionTime'] = ir['SessionInfo']['Sessions'][syncState.sessionNum]['SessionTime']
    if info['SessionTime'] != 'unlimited':
        info['SessionTime'] = float(ir['SessionInfo']['Sessions'][syncState.sessionNum]['SessionTime'][:-4]) / 86400
    info['SessionType'] = ir['SessionInfo']['Sessions'][syncState.sessionNum]['SessionType']
    info['TeamName'] = ir['DriverInfo']['Drivers'][state.driverIdx]['TeamName']

    return info

def checkPitRoad():
    syncState.updatePits(state.lap, ir['CarIdxTrackSurface'][state.driverIdx], ir['SessionTime'])
    if syncState.exitPits > 0:
        pitstopData = syncState.pitstopData()

def checkSessionChange():
    sessionChange = False
    
    if state.driverIdx == -1:
        state.driverIdx = ir['DriverInfo']['DriverCarIdx']

    if syncState.sessionId != str(ir['WeekendInfo']['SessionID']):
        syncState.sessionId = str(ir['WeekendInfo']['SessionID'])
        state.driverIdx = ir['DriverInfo']['DriverCarIdx']
        sessionChange = True
                
    if syncState.subSessionId != str(ir['WeekendInfo']['SubSessionID']):
        syncState.subSessionId = str(ir['WeekendInfo']['SubSessionID'])
        state.driverIdx = ir['DriverInfo']['DriverCarIdx']
        sessionChange = True

    if syncState.sessionNum != ir['SessionNum']:
        syncState.sessionNum = ir['SessionNum']
        state.driverIdx = ir['DriverInfo']['DriverCarIdx']
        sessionChange = True

    if sessionChange:
        if syncState.sessionId == '0' or ir['DriverInfo']['Drivers'][state.driverIdx]['TeamID'] == 0:
            state.sessionType = 'single'
        else:
            state.sessionType = 'team'

        collectionName = getCollectionName()
        print('SessionType: ' + state.sessionType)
        print('SessionId  : ' + collectionName)
        infodoc = getInfoDoc()
        if debug:
            print('infodoc: ' + str(infodoc))
        
        try:
            col_ref = db.collection(collectionName).document('Info')
            col_ref.set(infodoc)
        except Exception as ex:
            print('Unable to write info document: ' + str(ex))

# our main loop, where we retrieve data
# and do something useful with it
def loop():
    # on each tick we freeze buffer with live telemetry
    # it is optional, useful if you use vars like CarIdxXXX
    # in this way you will have consistent data from this vars inside one tick
    # because sometimes while you retrieve one CarIdxXXX variable
    # another one in next line of code can be changed
    # to the next iracing internal tick_count
    ir.freeze_var_buffer_latest()

    state.tick += 1
    lap = ir['LapCompleted']
    lastLaptime = 0
    if ir['LapLastLapTime'] > 0:
        lastLaptime = ir['LapLastLapTime']
    else:
        print('no last laptime')

    collectionName = getCollectionName()
    col_ref = db.collection(collectionName)
    
    # check for driver change
    checkDriver()

    # check for pit enter/exit
    checkPitRoad()

    data = {}
    #if lap != state.lap and lastLaptime != state.lastLaptime:
    if lastLaptime > 0 and syncState.lastLaptime != lastLaptime:
        state.lap = lap
        syncState.updateLap(lap, lastLaptime)

        data['Lap'] = lap
        data['StintLap'] = syncState.stintLap
        data['StintCount'] = syncState.stintCount
        data['Driver'] = syncState.currentDriver
        data['Laptime'] = syncState.lastLaptime 
        data['FuelUsed'] = state.fuel - ir['FuelLevel']
        state.fuel = ir['FuelLevel']
        data['FuelLevel'] = ir['FuelLevel']
        data['TrackTemp'] = ir['TrackTemp']
        data['PitServiceFlags'] = ir['PitSvFlags']
        data['SessionTime'] = ir['SessionTime'] / 86400

        if ir['OnPitRoad']:
            syncState.stintCount = syncState.stintCount + 1
            syncState.stintLap = 0

        if syncState.enterPits:
            data['PitEnter'] = syncState.enterPits / 86400
            syncState.enterPits = 0
        else:
            data['PitEnter'] = 0

        if syncState.exitPits:
            data['PitExit'] = syncState.exitPits / 86400
            syncState.exitPits = 0
        else:
            data['PitExit'] = 0

        if syncState.stopMoving:
            data['StopMoving'] = syncState.stopMoving / 86400
            syncState.stopMoving = 0
        else:
            data['StopMoving'] = 0

        if syncState.startMoving:
            data['StartMoving'] = syncState.startMoving / 86400
            syncState.startMoving = 0
        else:
            data['StartMoving'] = 0

        if syncState.repairTime > 0:
            data['PitRepair'] = syncState.repairTime / 86400
            syncState.repairTime = 0
        else:
            data['PitRepair'] = 0
        
        if syncState.optRepairTime > 0:
            data['PitOptRepair'] = syncState.optRepairTime / 86400
            syncState.optRepairTime = 0
        else:
            data['PitOptRepair'] = 0

        if syncState.towingTime > 0:
            data['TowingTime'] = syncState.towingTime / 86400
            syncState.towingTime = 0
        else:
            data['TowingTime'] = 0

        if iracingId == str(ir['DriverInfo']['Drivers'][state.driverIdx]['UserID']):
            try:
                col_ref.document(str(lap)).set(data)
            except Exception as ex:
                print('Unable to write lap data for lop ' + str(lap) + ': ' + str(ex))
            try:
                col_ref.document('State').set(syncState.toDict())
            except Exception as ex:
                print('Unable to write state document: ' + str(ex))

        if debug:
            logging.info(collectionName + ' lap ' + str(lap) + ': ' + json.dumps(data))

    else:
        checkSessionChange()

         
        try:
            doc = col_ref.document('State').get()
            
            if doc.exists:
                if debug:
                    data = doc.to_dict()
                    print('State: ' + str(data))
            else:
                if debug:
                    print('No state document found - providing it')

                col_ref.document('State').set(syncState.toDict())

        except Exception as ex:
            print('Unable to write state document: ' + str(ex))

        if syncState.fuel == -1:
            syncState.fuel = ir['FuelLevel']


        
            
    # publish session time and configured telemetry values every minute
    
    # read and publish configured telemetry values every second - but only
    # if the value has changed in telemetry

def banner():
    print("=============================")
    print("|   iRacing Team Tactics    |")
    print("|           " + str(__version__) + "            |")
    print("=============================")


# Here is our main program entry
if __name__ == '__main__':
    # Read configuration file
    config = configparser.ConfigParser()    
    try: 
        config.read('irtactics.ini')
    except Exception as ex:
        print('unable to read configuration: ' + str(ex))
        sys.exit(1)

    # Print banner an debug output status
    banner()
    if config.has_option('global', 'debug'):
        debug = config.getboolean('global', 'debug')
    else:
        debug = False
    
    if debug:
        print('Debug output enabled')

    if config.has_option('global', 'proxy'):
        proxyUrl = str(config['global']['proxy'])
        os.environ['http_proxy'] = proxyUrl
        os.environ['https_proxy'] = proxyUrl

    if config.has_option('global', 'firebase'):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './' + str(config['global']['firebase'])
        if debug:
            print('Use Google Credential file ' + os.environ['GOOGLE_APPLICATION_CREDENTIALS'])

        try:
            db = firestore.Client()
        except Exception as ex:
            print('Unable to connect to Firebase: ' + str(ex))
            sys.exit(1)

    else:
        print('option firebase not configured or irtactics.ini not found')
        sys.exit(1)
        
    if config.has_option('global', 'logfile'):
        logging.basicConfig(filename=str(config['global']['logfile']),level=logging.INFO)

    if config.has_option('global', 'iracingId'):
        iracingId = config['global']['iracingId']
        print('iRacing ID: ' + str(iracingId))
    else:
        print('option iRacingId not configured or irtactics.ini not found')
        sys.exit(1)

    # initializing ir and state
    ir = irsdk.IRSDK()
    state = State()
    syncState = SyncState()
    # Project ID is determined by the GCLOUD_PROJECT environment variable

    try:
        # infinite loop
        while True:
            # check if we are connected to iracing
            check_iracing()
                
            # if we are, then process data
            if state.ir_connected:
                loop()

            # sleep for half a second
            # maximum you can use is 1/60
            # cause iracing update data with 60 fps
            time.sleep(0.5)
    except KeyboardInterrupt:
        # press ctrl+c to exit
        print('exiting')
        time.sleep(1)
        pass