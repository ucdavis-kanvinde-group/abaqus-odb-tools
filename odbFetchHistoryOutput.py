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
# Define Functions
def saveContourDataCSV(odbName, description, runCompletion,
                       contourLabels, contourNumbers, dataSet):
    """
    saves an ODB Contour data array to a CSV file
    dependencies: re, sys, os, numpy

    formatted so that each contour (contourLabels) is a column,
    and each frame value (runCompletion) is a row
    """
    odbName = os.path.splitext(odbName)[0]
    saveFileName = (odbName + '_' + description + '.csv')
    #ensure filename is safe to write
    saveFileName = safe_filename(saveFileName)

    #delete any pre-existing file
    check_delete(saveFileName)

    #open file with write permissions
    saveFile = open(saveFileName,'w')

    #write contour name and number
    line1 = '""'
    line2 = '""'
    for i in range(0,len(contourLabels)):
        line1 += ', ' + contourLabels[i]
        line2 += ', ' + contourNumbers[i]
    line1 += '\n'
    line2 += '\n'
    saveFile.write(line1)
    saveFile.write(line2)

    #begin writing dataSet, prepend lines with runCompletion:
    for i in range(0,len(runCompletion)):
        #for all frames
        line = str(runCompletion[i])

        for k in range(0,len(contourLabels)):
            #for all contours
            line += ', ' + str(dataSet[i,k])
        line += '\n'

        #write line for this frame
        saveFile.write(line)

    #end program
    saveFile.close()

def getJintegral(odbName, stepName):
    """ 
    Returns a CSV of the J contour integrals 
    for the desired step 
    """
    
    #open the output database. must be in same directory
    #(it is recommended to use a copy in a subdirectory)
    odb = openOdb(odbName,readOnly=True)
    
    #define description string (per ABAQUS)
    description = 'J-integral'
    
    #define history region to analyse
    region_history = odb.steps['Pull'].historyRegions['ElementSet . ALL ELEMENTS'].historyOutputs
    
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
        if description in region_history[key].description:
            #implies this key is a J-integral
            numcontours += 1
            
    #
    # loop through history output, obtaining data
    #
    
    #initialize
    contourIndex = int(-1)
    contourLabels = []
    contourNumbers = []
    dataSet = numpy.zeros((numframes,numcontours),dtype=numpy.float64)
    
    for key in region_history.keys():
        if description in region_history[key].description:
            #implies this key is a J-integral
            contourIndex += 1
            
            #save contour name and number
            name = string.split(region_history[key].name,'_')
            contourLabels.append(name[-2] + '_' + name[-1])
            contourNumbers.append(name[-1])
            
            #save contour data
            data = region_history[key].data
            for i in range(0,len(data)):
                dataSet[i,contourIndex] = data[i][1]

    # all relevant data for the step has been captured!
    
    #
    # save output
    #
    saveContourDataCSV(odbName, description, runCompletion,
                       contourLabels, contourNumbers, dataSet)
    
            
    
