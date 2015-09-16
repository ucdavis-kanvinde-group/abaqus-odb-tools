"""
Vincente Pericoli
9 July 2015 (last modified: 10 Aug 2015)
UC Davis

for more info, including license information,
see: https://github.com/ucdavis-kanvinde-group/abaqus-odb-tools


** INTRO: **
Set of functions to use with ABAQUS output databases (ODB files).
These sets of functions can be used to obtain the nodal values of
various field output quantities for a defined assembly-level node
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
in magnitude (e.g. when there is volumetric locking). However,
the code can be easily edited to incorporate such a feature if it is 
desired. Generally, it is advisable to visually observe the quality 
of your results by using the ABAQUS ODB viewer with quilt plots.

Furthermore, the code will only work if the requested set only includes
ONE instance from the assembly. This is because ABAQUS numbers the nodes
and elements locally to the part (or instance), and not globally.
However, this code can be presumably updated to account for this,
if you prepend the node labels with the instance string. Likely you
will not want to have the averaging scheme to work accross instances
(i.e. between TIE constraints), which will complicate matters.

** HOW TO USE: **
1. Copy this module and your ODB file into a separate directory.
2. Create your own python script
3. At the beginning of the script, import this module with:
   from odbFetchFieldOutput import *
4. Define your odb filename and node set name as strings, and
   calling any functions here that you want.
5. From the command prompt, call "abaqus python YourScriptHere.py"

** Main Functions: **
1. getNodalPEEQ(odbName, nodeSetName, verbose)
2. getNodalMises(odbName, nodeSetName, verbose)
3. getNodalPressure(odbName, nodeSetName, verbose)
4. getNodalInv3(odbName, nodeSetName, verbose)
5. getNodalCoords(odbName, nodeSetName, verbose)
6. getNodalDispl(odbName, nodeSetName, verbose)
7. getNodalReaction(odbName, nodeSetName, verbose)
8. getNodalReactionSum(odbName, nodeSetName, verbose)

Descriptions of these are below (underneath the def's).

Usage--
    Inputs:
        odbName     = string of ABAQUS odb file
                      (including .odb extension)
        nodeSetName = string name of desired (defined) node set
        verbose     = optional input (default = True) which
                      controls printing to the command window.
                      If verbose=False, nothing will be printed
                      to the command window.

    Output:
        writes a CSV file containing node labels,
        frame values, and data. If integration point data
        is requested, the CSV contains averaged values.


** Dependencies: **
1. Numpy
2. odbAccess (comes with Abaqus by default)
3. abaqusConstants (comes with Abaqus by default)
4. myFileOperations (should be included with this file already)

"""

#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Import Modules

from odbAccess import *
from abaqusConstants import *
import numpy
import sys
import re
import os
from myFileOperations import *

#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Define Functions

def saveOdbFieldDataCSV(odbName, nodeSetName, dataName,
                   runCompletion, nodeLabels, dataSet, verbose=True):
    """
    saves an ODB data array to a CSV file
    dependencies: re, sys, os, numpy

    formatted so that each node (nodeLabels) is a column,
    and each frame value (runCompletion) is a row. For example,
    the file is saved so that runCompletion (the frame values) 
    itself is in the left-most column, and the nodeLabels are saved
    in the top-most row. Then, dataSet (can be anything... PEEQ, Mises,
    Pressure, etc.) is saved to the right of runCompletion and below 
    nodeLabels. In this way, each column of dataSet should correspond to
    a specific node (or element, or integration point, or whatever you pass
    in as nodeLabels),
    and each row should correspond to a specific frame value (or whatever you pass
    in as runCompletion).
    
    verbose is an optional input (default true) which defines where there will be
    a "verbose" output to the command window or not. If True, it will tell you
    when files are saved or replaced.
    """   
    odbName = os.path.splitext(odbName)[0]
    saveFileName = (odbName + '_' + nodeSetName
                    + '_' + dataName + '.csv')
    #ensure filename is safe to write
    saveFileName = safe_filename(saveFileName)

    #delete any pre-existing file
    check_delete(saveFileName, verbose)

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
            try:
                line += ', ' + str(dataSet[i,k])
            except IndexError:
                line += ', ' + str(dataSet[i])
        line += '\n'

        #write line for this frame
        saveFile.write(line)

    #end program
    saveFile.close()

def getNodalPEEQ(odbName, nodeSetName, verbose=True):
    """ Returns a CSV of the nodal averaged PEEQ"""
    
    #open the output database in read-only mode
    #must be in current working directory
    odb = openOdb(odbName,readOnly=True)

    #define dataName string for readability of the output file
    dataName = 'PEEQ'
    
    #define keyName string (per ABAQUS) where desired data is stored
    keyName = 'PEEQ'
    
    #ensure that the nodeSetName is uppercase (per ABAQUS)
    nodeSetName = nodeSetName.upper()
    
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
    # figure out which nodes are in myNodeSet, and sort them
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

            #initialize frame array.
            #this is used as temporary storage for 
            #averaging nodal results in the current frame
            framePEEQ = numpy.zeros((numnod,2),dtype=numpy.float64)
            framePEEQ[:,0] = numpy.float64(nodeLabels)
            
            #obtain a subset of the field output (based on myNodeSet)
            #this subset will only contain keyName (PEEQ) data
            myFieldOutput = frame.fieldOutputs[keyName].getSubset(
                position=ELEMENT_NODAL,region=myNodeSet)
            
            #obtain all the nodal PEEQ for this frame
            nodes = [];
            PEEQs = [];
            for value in myFieldOutput.values:
                #node number is stored in value.nodeLabel
                nodes.append(value.nodeLabel)
                #nodal PEEQ is stored in value.data
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
                   runCompletion, nodeLabels, resultPEEQ, verbose)
    return None

def getNodalMises(odbName, nodeSetName, verbose=True):
    """ returns a CSV of the nodal averaged Mises"""
    #open the output database in read-only mode
    #must be in current working directory
    odb = openOdb(odbName,readOnly=True)

    #define dataName string for readability of the output file
    dataName = 'MISES'
    
    #define keyName string (per ABAQUS) where desired data is stored
    #mises is stored in the stress output: 'S'
    keyName = 'S'
    
    #ensure that the nodeSetName is uppercase (per ABAQUS)
    nodeSetName = nodeSetName.upper()
    
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
    # figure out which nodes are in myNodeSet, and sort them
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

            #initialize frame array.
            #this is used as temporary storage for 
            #averaging nodal results in the current frame
            frameMISES = numpy.zeros((numnod,2),dtype=numpy.float64)
            frameMISES[:,0] = numpy.float64(nodeLabels)
            
            #obtain a subset of the field output (based on myNodeSet)
            #this subset will only contain keyName (stress) data
            myFieldOutput = frame.fieldOutputs[keyName].getSubset(
                position=ELEMENT_NODAL,region=myNodeSet)
            
            #obtain all the nodal MISES for this frame
            nodes = []
            MISESs = []
            for value in myFieldOutput.values:
                #node numbers are saved in value.nodeLabel
                nodes.append(value.nodeLabel)
                #mises stress is saved in value.mises
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
                   runCompletion, nodeLabels, resultMISES, verbose)
    return None

def getNodalPressure(odbName, nodeSetName, verbose=True):
    """ returns a CSV of the nodal averaged pressure """
    #open the output database in read-only mode.
    #must be in current working directory
    odb = openOdb(odbName,readOnly=True)

    #define dataName string for readability of the output file
    dataName = 'PRESS'
    
    #define keyName string (per ABAQUS) where desired data is stored
    #pressure is stored in the stress output: 'S'
    keyName = 'S'
    
    #ensure that the nodeSetName is uppercase (per ABAQUS)
    nodeSetName = nodeSetName.upper()
    
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
    # figure out which nodes are in myNodeSet, and sort them
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

            #initialize frame array.
            #this is used as temporary storage for 
            #averaging nodal results in the current frame
            framePRESS = numpy.zeros((numnod,2),dtype=numpy.float64)
            framePRESS[:,0] = numpy.float64(nodeLabels)
            
            #obtain a subset of the field output (based on myNodeSet)
            #this subset will only contain keyName (stress) data
            myFieldOutput = frame.fieldOutputs[keyName].getSubset(
                position=ELEMENT_NODAL,region=myNodeSet)
            
            #obtain all the nodal Pressure for this frame
            nodes = [];
            PRESSs = [];
            for value in myFieldOutput.values:
                #node numbers are stored in value.nodeLabel
                nodes.append(value.nodeLabel)
                #pressure is stored in value.press
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
                   runCompletion, nodeLabels, resultPRESS, verbose)
    return None
    
def getNodalInv3(odbName, nodeSetName, verbose=True):
    """ returns a CSV of the nodal averaged third invariant """
    #open the output database in read-only mode
    #must be in current working directory
    odb = openOdb(odbName,readOnly=True)

    #define dataName string for readability of the output file
    dataName = 'INV3'
    
    #define keyName string (per ABAQUS) where desired data is stored
    #inv3 is stored in the stress output: 'S'
    keyName = 'S'
    
    #ensure that the nodeSetName is uppercase (per ABAQUS)
    nodeSetName = nodeSetName.upper()
    
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
    # figure out which nodes are in myNodeSet, and sort them
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
    resultINV3 = numpy.zeros((numframes,numnod),dtype=numpy.float64)
            
    #loop steps
    for step in odb.steps.values():
        stepNumber += 1

        #loop frames (step increments)
        for frame in step.frames:
            frameNumber += 1
            #obtain and save frameValue
            #you can interpret this as completion percentage
            runCompletion.append(frame.frameValue + stepNumber)

            #initialize frame array.
            #this is used as temporary storage for 
            #averaging nodal results in the current frame
            frameINV3 = numpy.zeros((numnod,2),dtype=numpy.float64)
            frameINV3[:,0] = numpy.float64(nodeLabels)
            
            #obtain a subset of the field output (based on myNodeSet)
            #this subset will only contain keyName (stress) data
            myFieldOutput = frame.fieldOutputs[keyName].getSubset(
                position=ELEMENT_NODAL,region=myNodeSet)
            
            #obtain all the nodal INV3 for this frame
            nodes = []
            INV3s = []
            for value in myFieldOutput.values:
                #node numbers are saved in value.nodeLabel
                nodes.append(value.nodeLabel)
                #inv3 stress is saved in value.inv3
                INV3s.append(numpy.float64( value.inv3 ))


            #average the nodal values so that there is
            #one INV3 per node in the frame
            for i in range(0,len(nodeLabels)):
                #for all node labels
                nodal_INV3 = []
                for k in range(0,len(nodes)):
                    if nodeLabels[i] == nodes[k]:
                        #pick up all INV3 belonging to node
                        nodal_INV3.append(INV3s[k])
                #save average to frameINV3
                frameINV3[i,1] = numpy.mean(nodal_INV3,dtype=numpy.float64)

            #save frame values to result
            resultINV3[frameNumber,:] = frameINV3[:,1]

    #all data from the steps and frames has been collected!
    #save data to CSV
    odb.close()
    saveOdbFieldDataCSV(odbName, nodeSetName, dataName,
                   runCompletion, nodeLabels, resultINV3, verbose)
    return None

def getNodalCoords(odbName, nodeSetName, verbose=True):
    """
    returns several CSVs of the nodal coordinates
    (one CSV file per direction)
    """
    #open the output database in read-only mode.
    #must be in current working directory
    odb = openOdb(odbName,readOnly=True)
    
    #define keyName string (per ABAQUS) where desired data is stored
    keyName = 'COORD'
    
    #dataName will be defined per ABAQUS componentLabels.
    
    #ensure that the nodeSetName is uppercase (per ABAQUS)
    nodeSetName = nodeSetName.upper()
    
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
    # figure out which nodes are in myNodeSet, and sort them
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
            #this subset will only contain keyName (COORD) data
            myFieldOutput = frame.fieldOutputs[keyName].getSubset(
                            region=myNodeSet)
            
            #initialize an array to temporarily store COORD for this frame.
            #necessary since we cannot be sure what order the nodes are in
            frameCOORDs = numpy.zeros((numnod,numdim),dtype=numpy.float64)
            
            #retrieve all the nodal COORD for this frame
            nodes = []
            for value in myFieldOutput.values:
                #for all values in the frame
                nodes.append( value.nodeLabel )
                for i in range(0,numdim):
                    #for all defined coordinates (e.g. COOR1, COOR2, COOR3)
                    try:
                        #analysis is single precision, so COORD is stored
                        #as a vector in value.data
                        frameCOORDs[len(nodes)-1,i] = value.data[i]
                    except:
                        #analysis is double precision, so COORD is stored
                        #as a vector in value.dataDouble
                        frameCOORDs[len(nodes)-1,i] = value.dataDouble[i]

            #save frame values to result
            for i in range(0,numnod):
                for k in range(0,len(nodes)):
                    if nodeLabels[i] == nodes[k]:
                        resultCOORD[frameNumber,i,:] = frameCOORDs[k,:]

    #all data from the steps and frames has been collected!
    #save data to CSV
    odb.close()
    for i in range(0,numdim):
        saveOdbFieldDataCSV(odbName, nodeSetName, components[i],
                       runCompletion, nodeLabels, resultCOORD[:,:,i], verbose)

    return None

def getNodalDispl(odbName, nodeSetName, verbose=True):
    """
    returns several CSVs of the nodal coordinates
    (one CSV file per direction)
    """
    #open the output databasein read-only mode.
    #must be in current working directory.
    odb = openOdb(odbName,readOnly=True)
    
    #define keyName string (per ABAQUS) where desired data is stored
    keyName = 'U'
    
    #dataName will be defined per ABAQUS componentLabels
    
    #ensure that the nodeSetName is uppercase (per ABAQUS)
    nodeSetName = nodeSetName.upper()
    
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
    # figure out which nodes are in myNodeSet, and sort them
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
    resultU = numpy.zeros((numframes,numnod,numdim),dtype=numpy.float64)
    
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
            #this subset will only contain keyName (displacement) data
            myFieldOutput = frame.fieldOutputs[keyName].getSubset(
                            region=myNodeSet)
            
            #initialize an array to temporarily store displacements for this frame.
            #necessary since we cannot be sure what order the nodes are in
            frameU = numpy.zeros((numnod,numdim),dtype=numpy.float64)
            
            #retrieve all the nodal displacements (U) for this frame
            nodes = []
            for value in myFieldOutput.values:
                #for all values in the frame
                nodes.append( value.nodeLabel )
                for dim in range(0,numdim):
                    #for all defined coordinates (i.e. U1, U2, U3)
                    try:
                        #analysis is single precision, so U is stored
                        #as a vector in value.data
                        frameU[len(nodes)-1,dim] = value.data[dim]
                    except:
                        #analysis is double precision, so U is stored
                        #as a vector in value.dataDouble
                        frameU[len(nodes)-1,dim] = value.dataDouble[dim]

            #save frame values to result
            for i in range(0,numnod):
                for k in range(0,len(nodes)):
                    if nodeLabels[i] == nodes[k]:
                        resultU[frameNumber,i,:] = frameU[k,:]

    #all data from the steps and frames has been collected!
    #save data to CSV
    odb.close()
    for i in range(0,numdim):
        saveOdbFieldDataCSV(odbName, nodeSetName, components[i],
                       runCompletion, nodeLabels, resultU[:,:,i], verbose)

    return None

def getNodalReaction(odbName, nodeSetName, verbose=True):
    """
    returns several CSVs of the nodal reactions
    (one CSV file per direction)
    """
    #open the output database in read-only mode.
    #must be in current working directory
    odb = openOdb(odbName,readOnly=True)
    
    #define keyName string (per ABAQUS) where desired data is stored
    keyName = 'RF'
    
    #dataName will be defined per ABAQUS componentLabels
    
    #ensure that the nodeSetName is uppercase (per ABAQUS)
    nodeSetName = nodeSetName.upper()
    
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
    # figure out which nodes are in myNodeSet, and sort them
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
            #this subset will only contain keyName (reaction) data
            myFieldOutput = frame.fieldOutputs[keyName].getSubset(
                            region=myNodeSet)
            
            #initialize an array to temporarily store RF for this frame.
            #necessary since we cannot be sure what order the nodes are in
            frameRFs = numpy.zeros((numnod,numdim),dtype=numpy.float64)
            
            #retrieve all the nodal RF for this frame
            nodes = []
            for value in myFieldOutput.values:
                #for all values in the frame
                nodes.append( value.nodeLabel )
                for i in range(0,numdim):
                    #for all defined coordinates (e.g. RF1, RF2, RF3)
                    try:
                        #analysis is in single precision,
                        #so RF is stored in value.data
                        frameRFs[len(nodes)-1,i] = value.data[i]
                    except:
                        #analysis is in double precision,
                        #so RF is stored in value.dataDouble
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
                       runCompletion, nodeLabels, resultRF[:,:,i], verbose)
                       
    return None

def getNodalReactionSum(odbName, nodeSetName, verbose=True):
    """
    returns several CSVs of the summed nodal reactions
    (one CSV file per direction)
    """
    #open the output database in read-only mode
    #must be in current working directory
    odb = openOdb(odbName,readOnly=True)
    
    #define keyName string (per ABAQUS) where desired data is stored
    keyName = 'RF'
    
    #dataName will be defined per ABAQUS componentLabels
    
    #ensure that the nodeSetName is uppercase (per ABAQUS)
    nodeSetName = nodeSetName.upper()
    
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
    resultRF = numpy.zeros((numframes,numdim),dtype=numpy.float64)
    
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
            #this subset will contain keyName (reaction) data only
            myFieldOutput = frame.fieldOutputs[keyName].getSubset(
                            region=myNodeSet)

            #retrieve and sum all the nodal RF for this frame
            for value in myFieldOutput.values:
                #for all values in the frame
                for dim in range(0,numdim):
                    #for all defined coordinates
                    try:
                        #analysis is in single precision,
                        #so RF is stored in value.data
                        resultRF[frameNumber,dim] += value.data[dim]
                    except:
                        #analysis is in double precision,
                        #so RF is stored in value.dataDouble
                        resultRF[frameNumber,dim] += value.dataDouble[dim]

    #all data from the steps and frames has been collected!
    #save data to CSV
    odb.close()
    for dim in range(0,numdim):
        saveOdbFieldDataCSV(odbName, nodeSetName, 'summed' + components[dim],
                       runCompletion, [0], resultRF[:,dim], verbose)
                       
    return None
    
    