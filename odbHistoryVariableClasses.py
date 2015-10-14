"""
Vincente Pericoli
UC Davis
10/08/2015

Classes for representing Abaqus ODB history variables.

verified to give accurate results on 10/14/2015
"""


#
# Import Modules
#

from odbAccess import *
from abaqusConstants import *
import numpy
import sys
import re
import string
from myFileOperations import *

#
# Classes
#

class CrackVariable(object):
    """ 
    a crack variable (currently only J-integral supported)
    
    Attributes:
    
    Dependent Attributes:
    
    Attributes set by :
    
    Methods:
    """
    #
    # Attributes (+ object initialization)
    #
    def __init__(self, odbName, stepName, crackName):
        """ return object with the desired attributes """
        
        # these attributes have properties (below) to protect the 
        # object from becoming unstable or broken
        self._odbName   = odbName
        self._stepName  = stepName
        self._crackName = crackName.upper()
    
        # these are set by getJintegral().
        # they are also pseudo-private because we don't want
        # to accidentally modify the data when we use it.
        self._description    = None
        self._runCompletion  = None
        self._contourLabels  = None
        self._contourNumbers = None
        self._resultData     = None
        return
        
    #
    # Getters and Setters for definition
    #
    @property
    def odbName(self):
        return self._odbName
    
    @odbName.setter
    def odbName(self,s):
        if not isinstance(s,str):
            raise TypeError('Must be a string!')
        self._odbName = s
        #changing the odbName will reset any results  
        #since they are not valid for a new ODB
        self.reset()
        return

    @property
    def stepName(self):
        return self._stepName
    
    @stepName.setter
    def stepName(self,s):
        if not isinstance(s,str):
            raise TypeError('Must be a string!')
        self._stepName = s
        #changing the stepName will reset any results
        #since they are not valid for a new step
        self.reset()
        return

    @property
    def crackName(self):
        return self._crackName
        
    @crackName.setter
    def crackName(self,s):
        # must be uppercase. don't need to explicitly 
        # check if string, since upper() only valid for strings
        self._crackName = s.upper()
        self.reset()
        return
    
    #
    # Getters for data
    #
    
    @property
    def description(self):
        return self._description
        
    @property
    def runCompletion(self):
        return self._runCompletion
        
    @property
    def contourLabels(self):
        return self._contourLabels
        
    @property
    def contourNumbers(self):
        return self._contourNumbers
        
    @property
    def resultData(self):
        return self._resultData
    
    
    #
    # Methods
    #
    
    def reset(self):
        """ resets any results to None """
        self._description    = None
        self._runCompletion  = None
        self._contourLabels  = None
        self._contourNumbers = None
        self._resultData     = None
        return

    
    def fetchJintegral(self):
        """ obtains the J-integral values for the crack """
        
        #open the output database. must be in same directory
        odb = openOdb(self.odbName,readOnly=True)
        
        #define description string (per ABAQUS, and for user-info)
        description = 'J-integral'
        
        #define history region to analyze. kind of a hack-ey work-around 
        #for if the ODB has been converted from a previous ABAQUS version
        try:
            # this is the histKey for a converted database
            histKey = 'ElementSet . PIBATCH'
            region_history = odb.steps[self.stepName].historyRegions[histKey].historyOutputs
        except:
            # this is the default histKey for CAE 6.14
            histKey = 'ElementSet . ALL ELEMENTS'
            region_history = odb.steps[self.stepName].historyRegions[histKey].historyOutputs
        
        #
        # obtain all of the relevant FRAME values
        #
        runCompletion = []
        for key in region_history.keys():
            if description in region_history[key].description:
                #implies this key is a J-integral
                for row in region_history[key].data:
                    runCompletion.append(row[0])
                break
        
        numframes = len(runCompletion)
        
        #
        # obtain number of requested contours
        #
        numcontours = int(0)
        for key in region_history.keys():
            if (description    in region_history[key].description) and \
               (self.crackName in region_history[key].name):
                #implies this key is a J-integral of the requested crack
                numcontours += 1
                
        #
        # loop through history output, obtaining data
        #
        
        #initialize
        contourIndex   = int(-1)
        contourLabels  = []
        contourNumbers = []
        resultData = numpy.zeros((numframes,numcontours),dtype=numpy.float64)
        
        for key in region_history.keys():
            if (description    in region_history[key].description) and \
               (self.crackName in region_history[key].name):
                #implies this key is a J-integral of the requested crack
                contourIndex += 1
                
                #save contour name and number
                name = string.split(region_history[key].name,'_')
                contourLabels.append(name[-2] + '_' + name[-1])
                contourNumbers.append(name[-1])
                
                #save contour data
                data = region_history[key].data
                for i in range(0,len(data)):
                    resultData[i,contourIndex] = data[i][1]

        # all relevant data for the step has been captured!
        self._description    = description
        self._runCompletion  = runCompletion
        self._contourLabels  = contourLabels
        self._contourNumbers = contourNumbers
        self._resultData     = resultData
        return
        
    def saveCSV(self):
        """
        saves resultData to a CSV file

        formatted so that each contour (contourLabels) is a column,
        and each frame value (runCompletion) is a row
        """
        odbName = os.path.splitext(self.odbName)[0]
        saveFileName = (odbName + '_' + self.description +
                        '_' + self.crackName + '.csv')
        #ensure filename is safe to write
        saveFileName = safe_filename(saveFileName)

        #delete any pre-existing file
        check_delete(saveFileName)

        #open file with write permissions
        saveFile = open(saveFileName,'w')

        #write contour name and number
        line1 = '""'
        line2 = '""'
        for i in range(0,len(self.contourLabels)):
            line1 += ', ' + self.contourLabels[i]
            line2 += ', ' + self.contourNumbers[i]
        line1 += '\n'
        line2 += '\n'
        saveFile.write(line1)
        saveFile.write(line2)

        #begin writing resultData, prepend lines with runCompletion:
        for i in range(0,len(self.runCompletion)):
            #for all frames
            line = str(self.runCompletion[i])

            for k in range(0,len(self.contourLabels)):
                #for all contours
                line += ', ' + str(self.resultData[i,k])
            line += '\n'

            #write line for this frame
            saveFile.write(line)

        #end program
        saveFile.close()
        return