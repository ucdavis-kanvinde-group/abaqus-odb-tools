"""
Vincente Pericoli
14 July 2015
UC Davis

"""


#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Import Modules

from odbAccess import *
from abaqusConstants import *
import numpy
import sys
import re
import string
from myFileOperations import *

#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Define Class
class CrackVariable(object):
    """ a crack variable (currently only J-integral supported)
    
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
        self.__odbName   = odbName
        self.__stepName  = stepName
        self.__crackName = crackName.upper()
    
        # these are set by getJintegral()
        self.description    = None
        self.runCompletion  = None
        self.contourLabels  = None
        self.contourNumbers = None
        self.resultData     = None
        return
        
    #
    # Getters and Setters
    #
    @property
    def odbName(self):
        return self.__odbName
    
    @odbName.setter
    def odbName(self,s):
        if not isinstance(s,str):
            raise TypeError('Must be a string!')
        self.__odbName = s
        #changing the odbName will reset results since 
        #they are not valid for a new ODB
        self.reset()
        return

    @property
    def stepName(self):
        return self.__stepName
    
    @stepName.setter
    def stepName(self,s):
        if not isinstance(s,str):
            raise TypeError('Must be a string!')
        self.__odbName = s
        #changing the odbName will reset results since 
        #they are not valid for a new ODB
        self.reset()
        return

    @property
    def crackName(self):
        return self.__crackName
        
    @crackName.setter
    def crackName(self,s):
        # must be uppercase. don't need to explicitly 
        # check if string, since upper() only valid for strings
        self.__crackName = s.upper()
        self.reset()
        return

    #
    # Methods
    #
    
    def reset(self):
        """ resets any results to None """
        self.description    = None
        self.runCompletion  = None
        self.contourLabels  = None
        self.contourNumbers = None
        self.resultData     = None
        return

    
    def getJintegral(self):
        """ obtains the J-integral values for the crack """
        
        #open the output database. must be in same directory
        odb = openOdb(self.odbName,readOnly=True)
        
        #define description string (per ABAQUS, and for user-info)
        description = 'J-integral'
        
        #define history region to analyze. kind of a hack-ey work-around 
        #for if the ODB has been converted from a previous ABAQUS version
        try:
            histKey = 'ElementSet . PIBATCH'
            region_history = odb.steps[self.stepName].historyRegions[histKey].historyOutputs
        except:
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
        self.description    = description
        self.runCompletion  = runCompletion
        self.contourLabels  = contourLabels
        self.contourNumbers = contourNumbers
        self.resultData     = resultData
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