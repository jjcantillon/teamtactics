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

__author__ = "Robert Bausdorf"
__contact__ = "rbausdorf@gmail.com"
__copyright__ = "2020, bausdorf engineering"
#__credits__ = ["One developer", "And another one", "etc"]
__date__ = "2020/01/06"
__deprecated__ = False
__email__ =  "rbausdorf@gmail.com"
__license__ = "GPLv3"
#__maintainer__ = "developer"
__status__ = "Beta"
#__version__ = "0.5"

import logging
import sys
import requests
from google.cloud import firestore
from google.cloud import pubsub_v1

class Connector:
    firestore = None
    publisher = None
    messageTopic = ''
    postUrl = ''
    
    def __init__(self, config):
        print('Initializing connector')
        #self.firestore = firestore.Client()
        #self.publisher = pubsub_v1.PublisherClient()

        if config.has_option('connect', 'messageTopic'):
            self.messageTopic = str(config['connect']['messageTopic'])

        if config.has_option('connect', 'postUrl'):
            self.postUrl = str(config['connect']['postUrl'])
    
        if self.postUrl == '' and self.messageTopic == '':
            print('At least one option out of messageTopic and postUrl has to be configured, exiting')
            sys.exit(1)
        elif  self.postUrl != '' and self.messageTopic != '':
            print('At most one option out of messageTopic and postUrl has to be configured, exiting')
            sys.exit(1)
        elif self.postUrl != '':
            print('using postUrl ' + self.postUrl + ' to publish events')
        elif self.messageTopic != '':
            print('using messageTopic ' + self.messageTopic + ' to publish events')  

    def putDocument(self, collectionName, documentName, documentData):
        try:
            col_ref = self.firestore.collection(collectionName)
            col_ref.document(documentName).set(documentData)
            logging.info(documentName + '(' + str(documentData) + ')')
        except Exception as ex:
            print('Unable to write ' + documentName + ': ' + str(ex))

    def clearCollection(self, collectionName):
        col_ref = self.firestore.collection(collectionName)
        try:
            docs = list(col_ref.stream())
            if len(docs) > 0:
                for doc in docs:
                    doc.reference.delete()
            
        except Exception as ex:
            print('Firestore error: ' + str(ex))

    def getDocument(self, collectionName, documentName):
        doc = self.firestore.collection(collectionName).document(documentName).get()
        _docDict = None
        if doc.exists:
            _docDict = doc.to_dict()
        else:
            print('No ' + documentName + ' in ' + collectionName)

        return _docDict

    def updatePostUrl(self, config, teamName):
        if config.has_option('connect', teamName):
            self.postUrl = str(config['connect'][teamName])
            print('Post URL changed for team ' + teamName + ': ' + self.postUrl)
        else:
            print('No change of post URL for team ' + teamName)

    def publish(self, jsonData):
        try:
            if self.postUrl != '':
#                logging.info(jsonData)
                response = requests.post(self.postUrl, json=jsonData, timeout=10.0)
#                logging.info(str(response.status_code) + ': ' + response.content())
#                print(response.json())
                return response.json()
            else:
                self.publisher.publish(self.messageTopic, data=str(jsonData).encode('utf-8'))
        except Exception as ex:
            print('Unable to publish data: ' + str(ex))

