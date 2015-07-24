"""
Vincente Pericoli
9 July 2015
UC Davis

** INTRO: **
Set of functions to use with ABAQUS output databases (ODB files).
These sets of functions can be used to obtain the nodal values of
PEEQ, Mises, Pressure, and COORD for a defined assembly-level node
set. Keep in mind that if you define a geometry set in ABAQUS/CAE,
it will automatically create a node and element set with the same
name.

Simply provide the functions with an ODB name and a node set name.
The functions will write all the relevant information into a nicely
formatted CSV file.

** LIMITATIONS: **
Please be advised that the functions employ an averaging scheme
to obtain the nodal values of integration point variables.
Since stress and strain are discontinuous between elements,
the nodal value is assumed to be an average of all connecting
elements. The functions will INDISCRIMINANTLY average values...
you will NOT be warned if the values are vastly different
in magnitude. The code can be easily edited to incorporate such a
feature if it is desired.

Furthermore, the code will only work if the requested set only includes
ONE instance from the assembly. This is because ABAQUS numbers the nodes
and elements locally to the part (or instance), and not globally.
However, this code can be presumably updated to account for this,
if you prepend the node labels with the instance string. Likely you
will not want to have the averaging scheme to work accross instances
(i.e. between TIE constraints).

** HOW TO USE: **
1. Copy this module and your ODB file into a separate directory.
2. Create your own python script
3. At the beginning of the script, import this module with:
   from odbFetchFieldOutput import *
4. Define your odb filename and node set name as strings, and
   calling any functions here that you want.
5. From the command prompt, call "abaqus python YourScriptHere.py"

** Main Functions: **
1. getNodalPEEQ(odbName, nodeSetName)
2. getNodalMises(odbName, nodeSetName)
3. getNodalPressure(odbName, nodeSetName)
4. getNodalCoords(odbName, nodeSetName)

Descriptions of these are below (underneath the def's)

Usage--
    Inputs:
        odbName     = string of ABAQUS odb file
                      (including .odb extension)
        nodeSetName = string name of desired (defined) node set

    Output:
        writes a CSV file containing node labels,
        frame values, and data. If integration point data
        is requested, the CSV contains averaged values.


** Dependent Subroutines: **
1. safe_filename
2. saveOdbFieldDataCSV
"""

#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Import Modules

from odbAccess import *
from abaqusConstants import *
import numpy
import sys
import re
from myFileOperations import *

#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Define Functions

def saveOdbFieldDataCSV(odbName, nodeSetName, dataName,
                   runCompletion, nodeLabels, dataSet):
    """
    saves an ODB data array to a CSV file
    dependencies: re, sys, os, numpy

    formatted so that each node (nodeLabels) is a column,
    and each frame value (runCompletion) is a row
    """
    odbName = os.path.splitext(odbName)[0]
    saveFileName = (odbName + '_' + nodeSetName
                    + '_' + dataName + '.csv')
    #ensure filename is safe to write
    saveFileName = safe_filename(saveFileName)

    #delete any pre-existing file
    check_delete(saveFileName)

    #open file with write permissions
    saveFile = open(saveFileName,'w')

    #write node line and empty line
    line1 = '"node (right):"'
    line2 = '"frame (below):"'
    for node in nodeLabels:
        line1 += ', ' + str(node)
        line2 += ', ' + '""'
    line1 += '\n'
    line2 += '\n'
    saveFile.write(line1)
    saveFile.write(line2)

    #begin writing dataSet, prepend lines with runCompletion:
    for i in range(0,len(runCompletion)):
        #for all frames
        line = str(runCompletion[i])

        for k in range(0,len(nodeLabels)):
            #for all nodes
            line += ', ' + str(dataSet[i,k])
        line += '\n'

        #write line for this frame
        saveFile.write(line)

    #end program
    saveFile.close()

def getNodalPEEQ(odbName, nodeSetName):
    """ Returns a CSV of the nodal averaged PEEQ"""
    
    #open the output database. must be in same directory
    #(it is recommended to use a copy in a subdirectory)
    odb = openOdb(odbName,readOnly=True)

    #define dataName string for readability of the output file
    dataName = 'PEEQ'
    #define keyName string (per ABAQUS) for error handling
    keyName = 'PEEQ'
    
    #
    # check if keyName and nodeSetName exist (Error Handling):
    #
    try:
        myNodeSet = odb.rootAssembly.nodeSets[nodeSetName]
    except KeyError:
        print 'Assembly level node set named %s does' \
              'not exist in the output database %s' \
              % (nodeSetName, odbName)
        odb.close()
        exit(0)

    testStep = odb.steps.keys()[-1]
    if odb.steps[testStep].frames[-1].fieldOutputs.has_key(keyName) == 0:
        print '%s output request is not defined for' \
              'all (or any?) steps!' % (keyName)
        odb.close()
        exit(0)
    
    #
    # get the sorted node labels for the set
    #
    nodeLabels = []
    for n in myNodeSet.nodes[0]:
        nodeLabels.append(n.label)
    nodeLabels.sort()
    numnod = int(len(nodeLabels))

    #
    # loop through STEPs and FRAMEs, obtaining total number of FRAMEs
    #
    numframes = int(0)
    #loop steps
    for step in odb.steps.values():
        #loop frames (step increments)
        for frame in step.frames:
            numframes += 1

    #
    # iterate through the STEPs and FRAMEs, saving the info as applicable
    #

    #initialize
    stepNumber = int(-1)
    frameNumber = int(-1)
    runCompletion = []
    resultPEEQ = numpy.zeros((numframes,numnod),dtype=numpy.float64)
            
    #loop steps
    for step in odb.steps.values():
        stepNumber += 1

        #loop frames (step increments)
        for frame in step.frames:
            frameNumber += 1
            #obtain and save frameValue
            #you can interpret this as completion percentage
            runCompletion.append(frame.frameValue + stepNumber)

            #initialize frame array,
            #used for averaging nodal results in the frame
            framePEEQ = numpy.zeros((numnod,2),dtype=numpy.float64)
            framePEEQ[:,0] = numpy.float64(nodeLabels)
            
            #obtain a subset of the field output (based on myNodeSet)
            myFieldOutput = frame.fieldOutputs['PEEQ'].getSubset(
                position=ELEMENT_NODAL,region=myNodeSet)
            
            #obtain all the nodal PEEQ for this frame
            nodes = [];
            PEEQs = [];
            for value in myFieldOutput.values:
                nodes.append(value.nodeLabel)
                PEEQs.append(numpy.float64( value.data ))


            #average the nodal values so that there is
            #one PEEQ per node in the frame
            for i in range(0,len(nodeLabels)):
                #for all node labels
                nodal_PEEQ = []
                for k in range(0,len(nodes)):
                    if nodeLabels[i] == nodes[k]:
                        #pick up all PEEQs belonging to node
                        nodal_PEEQ.append(PEEQs[k])
                #save average to framePEEQ
                framePEEQ[i,1] = numpy.mean(nodal_PEEQ,dtype=numpy.float64)

            #save frame values to result
            resultPEEQ[frameNumber,:] = framePEEQ[:,1]

    #all data from the steps and frames has been collected!
    #save data to CSV
    odb.close()
    saveOdbFieldDataCSV(odbName, nodeSetName, dataName,
                   runCompletion, nodeLabels, resultPEEQ)
    return None

def getNodalMises(odbName, nodeSetName):
    """ returns a CSV of the nodal averaged Mises"""
    #open the output database. must be in same directory
    #(it is recommended to use a copy in a subdirectory)
    odb = openOdb(odbName,readOnly=True)

    #define dataName string for readability of the output file
    dataName = 'MISES'
    #define keyName string (per ABAQUS) for error handling
    keyName = 'S'
    
    #
    # check if dataName and nodeSetName exist (Error Handling):
    #
    try:
        myNodeSet = odb.rootAssembly.nodeSets[nodeSetName]
    except KeyError:
        print 'Assembly level node set named %s does' \
              'not exist in the output database %s' \
              % (nodeSetName, odbName)
        odb.close()
        exit(0)

    testStep = odb.steps.keys()[-1]
    if odb.steps[testStep].frames[-1].fieldOutputs.has_key(keyName) == 0:
        print '%s output request is not defined for' \
              'all (or any?) steps!' % (keyName)
        odb.close()
        exit(0)
    
    #
    # get the sorted node labels for the set
    #
    nodeLabels = []
    for n in myNodeSet.nodes[0]:
        nodeLabels.append(n.label)
    nodeLabels.sort()
    numnod = int(len(nodeLabels))

    #
    # loop through STEPs and FRAMEs, obtaining total number of FRAMEs
    #
    numframes = int(0)
    #loop steps
    for step in odb.steps.values():
        #loop frames (step increments)
        for frame in step.frames:
            numframes += 1

    #
    # iterate through the STEPs and FRAMEs, saving the info as applicable
    #

    #initialize
    stepNumber = int(-1)
    frameNumber = int(-1)
    runCompletion = []
    resultMISES = numpy.zeros((numframes,numnod),dtype=numpy.float64)
            
    #loop steps
    for step in odb.steps.values():
        stepNumber += 1

        #loop frames (step increments)
        for frame in step.frames:
            frameNumber += 1
            #obtain and save frameValue
            #you can interpret this as completion percentage
            runCompletion.append(frame.frameValue + stepNumber)

            #initialize frame array,
            #used for averaging nodal results in the frame
            frameMISES = numpy.zeros((numnod,2),dtype=numpy.float64)
            frameMISES[:,0] = numpy.float64(nodeLabels)
            
            #obtain a subset of the field output (based on myNodeSet)
            myFieldOutput = frame.fieldOutputs['S'].getSubset(
                position=ELEMENT_NODAL,region=myNodeSet)
            
            #obtain all the nodal MISES for this frame
            nodes = []
            MISESs = []
            for value in myFieldOutput.values:
                nodes.append(value.nodeLabel)
                MISESs.append(numpy.float64( value.mises ))


            #average the nodal values so that there is
            #one MISES per node in the frame
            for i in range(0,len(nodeLabels)):
                #for all node labels
                nodal_MISES = []
                for k in range(0,len(nodes)):
                    if nodeLabels[i] == nodes[k]:
                        #pick up all MISES belonging to node
                        nodal_MISES.append(MISESs[k])
                #save average to frameMISES
                frameMISES[i,1] = numpy.mean(nodal_MISES,dtype=numpy.float64)

            #save frame values to result
            resultMISES[frameNumber,:] = frameMISES[:,1]

    #all data from the steps and frames has been collected!
    #save data to CSV
    odb.close()
    saveOdbFieldDataCSV(odbName, nodeSetName, dataName,
                   runCompletion, nodeLabels, resultMISES)
    return None

def getNodalPressure(odbName, nodeSetName):
    """ returns a CSV of the nodal averaged pressure """
    #open the output database. must be in same directory
    #(it is recommended to use a copy in a subdirectory)
    odb = openOdb(odbName,readOnly=True)

    #define dataName string for readability of the output file
    dataName = 'PRESS'
    #define keyName string (per ABAQUS) for error handling
    keyName = 'S'
    
    #
    # check if keyName and nodeSetName exist (Error Handling):
    #
    try:
        myNodeSet = odb.rootAssembly.nodeSets[nodeSetName]
    except KeyError:
        print 'Assembly level node set named %s does' \
              'not exist in the output database %s' \
              % (nodeSetName, odbName)
        odb.close()
        exit(0)

    testStep = odb.steps.keys()[-1]
    if odb.steps[testStep].frames[-1].fieldOutputs.has_key(keyName) == 0:
        print '%s output request is not defined for' \
              'all (or any?) steps!' % (keyName)
        odb.close()
        exit(0)
    
    #
    # get the sorted node labels for the set
    #
    nodeLabels = []
    for n in myNodeSet.nodes[0]:
        nodeLabels.append(n.label)
    nodeLabels.sort()
    numnod = int(len(nodeLabels))

    #
    # loop through STEPs and FRAMEs, obtaining total number of FRAMEs
    #
    numframes = int(0)
    #loop steps
    for step in odb.steps.values():
        #loop frames (step increments)
        for frame in step.frames:
            numframes += 1

    #
    # iterate through the STEPs and FRAMEs, saving the info as applicable
    #

    #initialize
    stepNumber = int(-1)
    frameNumber = int(-1)
    runCompletion = []
    resultPRESS = numpy.zeros((numframes,numnod),dtype=numpy.float64)
            
    #loop steps
    for step in odb.steps.values():
        stepNumber += 1

        #loop frames (step increments)
        for frame in step.frames:
            frameNumber += 1
            #obtain and save frameValue
            #you can interpret this as completion percentage
            runCompletion.append(frame.frameValue + stepNumber)

            #initialize frame array,
            #used for averaging nodal results in the frame
            framePRESS = numpy.zeros((numnod,2),dtype=numpy.float64)
            framePRESS[:,0] = numpy.float64(nodeLabels)
            
            #obtain a subset of the field output (based on myNodeSet)
            myFieldOutput = frame.fieldOutputs['S'].getSubset(
                position=ELEMENT_NODAL,region=myNodeSet)
            
            #obtain all the nodal PEEQ for this frame
            nodes = [];
            PRESSs = [];
            for value in myFieldOutput.values:
                nodes.append(value.nodeLabel)
                PRESSs.append(numpy.float64( value.press ))


            #average the nodal values so that there is
            #one PRESS per node in the frame
            for i in range(0,len(nodeLabels)):
                #for all node labels
                nodal_PRESS = []
                for k in range(0,len(nodes)):
                    if nodeLabels[i] == nodes[k]:
                        #pick up all PRESS belonging to node
                        nodal_PRESS.append(PRESSs[k])
                #save average to framePRESS
                framePRESS[i,1] = numpy.mean(nodal_PRESS,dtype=numpy.float64)

            #save frame values to result
            resultPRESS[frameNumber,:] = framePRESS[:,1]

    #all data from the steps and frames has been collected!
    #save data to CSV
    odb.close()
    saveOdbFieldDataCSV(odbName, nodeSetName, dataName,
                   runCompletion, nodeLabels, resultPRESS)
    return None

def getNodalCoords(odbName, nodeSetName):
    """
    returns several CSVs of the nodal coordinates
    (one CSV file per direction)
    """
    #open the output database. must be in same directory
    #(it is recommended to use a copy in a subdirectory)
    odb = openOdb(odbName,readOnly=True)
    
    #define keyName string (per ABAQUS) for error handling
    keyName = 'COORD'
    #unlike the other functions above, dataName will be 
    #defined per ABAQUS componentLabels
    
    #
    # check if keyName and nodeSetName exist (Error Handling):
    #
    try:
        myNodeSet = odb.rootAssembly.nodeSets[nodeSetName]
    except KeyError:
        print 'Assembly level node set named %s does' \
              'not exist in the output database %s' \
              % (nodeSetName, odbName)
        odb.close()
        exit(0)

    testStep = odb.steps.keys()[-1]
    if odb.steps[testStep].frames[-1].fieldOutputs.has_key(keyName) == 0:
        print '%s output request is not defined for' \
              'all (or any?) steps!' % (keyName)
        odb.close()
        exit(0)
    
    #
    # obtain the componentLabels so that we know what the values
    # in the ODB array mean. This will also be used to meaningfully
    # name the saved data
    #
    components = odb.steps[testStep].frames[0]. \
                 fieldOutputs[keyName].componentLabels
    numdim = len(components)
    #
    # get the sorted node labels for the set
    #
    nodeLabels = []
    for n in myNodeSet.nodes[0]:
        nodeLabels.append(n.label)
    nodeLabels.sort()
    numnod = int(len(nodeLabels))

    #
    # loop through STEPs and FRAMEs, obtaining total number of FRAMEs
    #
    numframes = int(0)
    #loop steps
    for step in odb.steps.values():
        #loop frames (step increments)
        for frame in step.frames:
            numframes += 1

    #
    # iterate through the STEPs and FRAMEs, saving the info as applicable
    #

    #initialize
    stepNumber = int(-1)
    frameNumber = int(-1)
    runCompletion = []
    resultCOORD = numpy.zeros((numframes,numnod,numdim),dtype=numpy.float64)
    
    #loop steps
    for step in odb.steps.values():
        stepNumber += 1

        #loop frames (step increments)
        for frame in step.frames:
            frameNumber += 1
            #obtain and save frameValue
            #you can interpret this as completion percentage
            runCompletion.append(frame.frameValue + stepNumber)

            #obtain a subset of the field output (based on myNodeSet)
            myFieldOutput = frame.fieldOutputs[keyName].getSubset(
                            region=myNodeSet)
            
            #initialize an array to store COORD for this frame.
            #necessary since we cannot be sure what order the nodes are in
            frameCOORDs = numpy.zeros((numnod,numdim),dtype=numpy.float64)
            
            #retrieve all the nodal COORD for this frame
            nodes = []
            for value in myFieldOutput.values:
                #for all values in the frame
                nodes.append( value.nodeLabel )
                for i in range(0,numdim):
                    #for all defined coordinates
                    try:
                        frameCOORDs[len(nodes)-1,i] = value.data[i]
                    except:
                        frameCOORDs[len(nodes)-1,i] = value.dataDouble[i]

            #save frame values to result
            for i in range(0,numnod):
                for k in range(0,len(nodes)):
                    if nodeLabels[i] == nodes[k]:
                        resultCOORD[frameNumber,i,:] = \
                              frameCOORDs[k,:]

    #all data from the steps and frames has been collected!
    #save data to CSV
    odb.close()
    for i in range(0,numdim):
        saveOdbFieldDataCSV(odbName, nodeSetName, components[i],
                       runCompletion, nodeLabels, resultCOORD[:,:,i])

def getNodalReaction(odbName, nodeSetName):
    """
    returns several CSVs of the nodal reactions
    (one CSV file per direction)
    """
    #open the output database. must be in same directory
    #(it is recommended to use a copy in a subdirectory)
    odb = openOdb(odbName,readOnly=True)
    
    #define keyName string (per ABAQUS) for error handling
    keyName = 'RF'
    #unlike the other functions above, dataName will be 
    #defined per ABAQUS componentLabels
    
    #
    # check if keyName and nodeSetName exist (Error Handling):
    #
    try:
        myNodeSet = odb.rootAssembly.nodeSets[nodeSetName]
    except KeyError:
        print 'Assembly level node set named %s does' \
              'not exist in the output database %s' \
              % (nodeSetName, odbName)
        odb.close()
        exit(0)

    testStep = odb.steps.keys()[-1]
    if odb.steps[testStep].frames[-1].fieldOutputs.has_key(keyName) == 0:
        print '%s output request is not defined for' \
              'all (or any?) steps!' % (keyName)
        odb.close()
        exit(0)
    
    #
    # obtain the componentLabels so that we know what the values
    # in the ODB array mean. This will also be used to meaningfully
    # name the saved data
    #
    components = odb.steps[testStep].frames[0]. \
                 fieldOutputs[keyName].componentLabels
    numdim = len(components)
    #
    # get the sorted node labels for the set
    #
    nodeLabels = []
    for n in myNodeSet.nodes[0]:
        nodeLabels.append(n.label)
    nodeLabels.sort()
    numnod = int(len(nodeLabels))

    #
    # loop through STEPs and FRAMEs, obtaining total number of FRAMEs
    #
    numframes = int(0)
    #loop steps
    for step in odb.steps.values():
        #loop frames (step increments)
        for frame in step.frames:
            numframes += 1

    #
    # iterate through the STEPs and FRAMEs, saving the info as applicable
    #

    #initialize
    stepNumber = int(-1)
    frameNumber = int(-1)
    runCompletion = []
    resultRF = numpy.zeros((numframes,numnod,numdim),dtype=numpy.float64)
    
    #loop steps
    for step in odb.steps.values():
        stepNumber += 1

        #loop frames (step increments)
        for frame in step.frames:
            frameNumber += 1
            #obtain and save frameValue
            #you can interpret this as completion percentage
            runCompletion.append(frame.frameValue + stepNumber)

            #obtain a subset of the field output (based on myNodeSet)
            myFieldOutput = frame.fieldOutputs[keyName].getSubset(
                            region=myNodeSet)
            
            #initialize an array to store RF for this frame.
            #necessary since we cannot be sure what order the nodes are in
            frameRFs = numpy.zeros((numnod,numdim),dtype=numpy.float64)
            
            #retrieve all the nodal RF for this frame
            nodes = []
            for value in myFieldOutput.values:
                #for all values in the frame
                nodes.append( value.nodeLabel )
                for i in range(0,numdim):
                    #for all defined coordinates
                    try:
                        frameRFs[len(nodes)-1,i] = value.data[i]
                    except:
                        frameRFs[len(nodes)-1,i] = value.dataDouble[i]

            #save frame values to result
            for i in range(0,numnod):
                for k in range(0,len(nodes)):
                    if nodeLabels[i] == nodes[k]:
                        resultRF[frameNumber,i,:] = frameRFs[k,:]

    #all data from the steps and frames has been collected!
    #save data to CSV
    odb.close()
    for i in range(0,numdim):
        saveOdbFieldDataCSV(odbName, nodeSetName, components[i],
                       runCompletion, nodeLabels, resultRF[:,:,i])
