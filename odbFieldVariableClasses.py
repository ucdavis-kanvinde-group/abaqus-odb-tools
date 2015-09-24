"""
Vincente Pericoli
UC Davis
16 Sept 2015

Classes for the odbFetchFieldOutput library.
This is where all the juicy stuff is.
"""
from odbAccess import *
from abaqusConstants import *
import numpy
import sys
import re
import os
from myFileOperations import *

class fieldVariable(object):
    """ a base class for field variables; other classes inherit this class. """
    #
    # Attributes (object initialization)
    #
    def __init__(self, odbName, dataName, nodeSetName):
        """ return object with the desired attributes """
        # these attributes have properties (below) to protect the 
        # object from becoming unstable or broken
        self._odbName     = odbName
        self._dataName    = dataName.upper()    # must be upper-case
        self._nodeSetName = nodeSetName.upper() # must be upper-case
        
        # these are set by fetchNodalOutput()
        self._runCompletion = None
        self._nodeLabels    = None
        self._resultData    = None
        return
    
    #
    # Getters to make output attributes read-only
    #
    @property
    def runCompletion(self):
        return self._runCompletion
    
    @property
    def nodeLabels(self):
        return self._nodeLabels
    
    @property
    def resultData(self):
        return self._resultData

    #
    # Getters and Setters to protect Object
    #
    @property
    def odbName(self):
        return self._odbName
    
    @odbName.setter
    def odbName(self,s):
        if not isinstance(s,str):
            raise TypeError('Must be a string!')
        self.__odbName = s
        #changing this attribute will invalidate any field data
        self.reset()
        return
        
    @property
    def dataName(self):
        return self._dataName
    
    @dataName.setter
    def dataName(self, s):
        self._dataName = s.upper()
        #changing this attribute will invalidate any field data
        self.reset()
        return

    @property
    def nodeSetName(self):
        return self._nodeSetName
    
    @nodeSetName.setter
    def nodeSetName(self, s):
        self._nodeSetName = s.upper()
        #changing this attribute will invalidate any field data
        self.reset()
        return
    
    #
    # Methods
    #
    def reset(self):
        """ resets any results to None """
        print "\nWarning: instance is being reset\n"
        self._runCompletion = None
        self._nodeLabels    = None
        self._resultData    = None
        return
    
    def _saveOdbFieldDataCSV(self, dataTitle=None, 
                            dataSet=None, verbose=True):
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
        #assign dataTitle and dataSet if not defined
        if dataTitle is None:
            dataTitle = self.dataName
        if dataSet is None:
            dataSet = self.resultData

        #strip away file extension
        odbName = os.path.splitext(self.odbName)[0]
        #assign file name to save
        saveFileName = (odbName + '_' + self.nodeSetName
                        + '_' + dataTitle + '.csv')
        #ensure filename is safe to write
        saveFileName = safe_filename(saveFileName)

        #delete any pre-existing file
        check_delete(saveFileName, verbose)

        #open file with write permissions
        saveFile = open(saveFileName,'w')

        #write node line and empty line
        line1 = '"node (right):"'
        line2 = '"frame (below):"'
        for node in self.nodeLabels:
            line1 += ', ' + str(node)
            line2 += ', ' + '""'
        line1 += '\n'
        line2 += '\n'
        saveFile.write(line1)
        saveFile.write(line2)

        #begin writing dataSet, prepend lines with runCompletion:
        for i in range(0,len(self.runCompletion)):
            #for all frames
            line = str(self.runCompletion[i])

            for k in range(0,len(self.nodeLabels)):
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
        return


class IntPtVariable(fieldVariable):
    """ An integration point variable whose results
    are extrapolated to the nodes of a defined set.
    
    Attributes:
        odbName  = string name of ODB file/location
        dataName = string name of the data (e.g. 'MISES')
        nodeSetName = string of the requested node set
        
    Dependent Attributes (automatically calculated):
        keyName   = string name of hierarchical Abaqus output (e.g. 'S')
                    depends on setting of dataName
        abqAttrib = string name of data storage location
                    depends on setting of dataName
        
    Attributes set by fetchNodalOutput():
        runCompletion = list of frame values for abaqus run 
                        runCompletion[0] corresponds to resultData[0,:], etc.
        nodeLabels    = list of nodes where output is generated
                        nodeLabels[0] cooresponds to resultData[:,0], etc.
        resultData    = numpy float64 array of the actual field 
                        output data (e.g. PEEQ, mises, etc). 
                        Rows correspond to frame values,
                        columns correspond to nodes.
    """
    
    #
    # Dependent Properties (set depending on dataName)
    #
    @property
    def keyName(self):
        """ 
        keyName property. 
        This is the "main" output variable in Abaqus that you are
        looking for. For example, if you want MISES data, the 
        "main" output variable is actually stress, which has a 
        keyName of 'S' in the output.
        """
        if self.dataName == 'PEEQ':
            return 'PEEQ'
        elif self.dataName == 'MISES':
            return 'S'
        elif self.dataName == 'PRESS':
            return 'S'
        elif self.dataName == 'INV3':
            return 'S'
        else:
            raise Exception('Unknown dataName assignment!')
        return
    
    @property
    def abqAttrib(self):
        """ 
        Abaqus Attribute property... this is the name of the
        location where our field output data values are stored
        in the abaqus ODB structure
        """
        if self.dataName == 'PEEQ':
            return 'data'
        elif self.dataName == 'MISES':
            return 'mises'
        elif self.dataName == 'PRESS':
            return 'press'
        elif self.dataName == 'INV3':
            return 'inv3'
        else:
            raise Exception('Unknown dataName assignment!')
        return

    #
    # Methods
    #
    def fetchNodalOutput(self):
        """ fetch the integration point field output
        for the desired node set. Since we are requesting IP
        field output at the nodes, ABAQUS will extrapolate 
        using basis functions. Furthermore, IP field variables 
        are discontinuous at the nodal locations, so this function
        performs an average to obtain a single output per node. 
        Unfortunately, this means that the function will not work
        at TIE constraints.
        
        this method sets the following attributes:
            runCompletion
            nodeLabels
            resultData
        """
        
        #open the output database in read-only mode
        if self.odbName.endswith('.odb'):
            odb = openOdb(self.odbName, readOnly=True)
        else:
            odb = openOdb(self.odbName + '.odb', readOnly=True)

        #
        # check if keyName and nodeSetName exist (Error Handling)
        # and set them if they do.
        #
        try:
            myNodeSet = odb.rootAssembly.nodeSets[self.nodeSetName]
        except KeyError:
            print 'Assembly level node set named %s does' \
                  'not exist in the output database %s' \
                  % (self.nodeSetName, self.odbName)
            odb.close()
            exit(0)

        testStep = odb.steps.keys()[-1]
        if odb.steps[testStep].frames[-1].fieldOutputs.has_key(self.keyName) == 0:
            print '%s output request is not defined for' \
                  'all (or any?) steps!' % (self.keyName)
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
        stepNumber    = int(-1)
        frameNumber   = int(-1)
        runCompletion = []
        resultData    = numpy.zeros((numframes,numnod),dtype=numpy.float64)
                
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
                frameData      = numpy.zeros((numnod,2),dtype=numpy.float64)
                frameData[:,0] = numpy.float64(nodeLabels)
                
                #obtain a subset of the field output (based on myNodeSet)
                #this subset will only contain keyName data
                myFieldOutput = frame.fieldOutputs[self.keyName].getSubset(
                    position=ELEMENT_NODAL,region=myNodeSet)
                
                #obtain all the nodal data for this frame
                tempNodes = [];
                tempData  = [];
                for value in myFieldOutput.values:
                    #node number is stored in value.nodeLabel
                    tempNodes.append(value.nodeLabel)
                    #nodal data is stored in value.(abqAttrib)
                    tempData.append(numpy.float64( 
                                    getattr(value, self.abqAttrib) ))


                #average the nodal values so that there is
                #one field data value per node in the frame
                for i in range(0,len(nodeLabels)):
                    #for all node labels
                    nodal_data = []
                    for k in range(0,len(tempNodes)):
                        if nodeLabels[i] == tempNodes[k]:
                            #pick up all data belonging to node
                            nodal_data.append(tempData[k])
                    #save average to frameData
                    frameData[i,1] = numpy.mean(nodal_data, dtype=numpy.float64)

                #save frame values to result
                resultData[frameNumber,:] = frameData[:,1]

        #set the proper attributes
        self._runCompletion = runCompletion
        self._nodeLabels    = nodeLabels
        self._resultData    = resultData
        
        #all data from the steps and frames has been collected!
        #close output database
        odb.close()
        return
        
    def saveCSV(self, verbose=True):
        """ save a CSV file of data """
        self._saveOdbFieldDataCSV(verbose=verbose)
        return


class NodalVariable(fieldVariable):
    """ 
    A nodal variable whose results are obtained on the defined set 
    
    Attributes:
        odbName  = string name of ODB file/location
        dataName = string name of the data (e.g. 'U')
        nodeSetName = string of the requested node set
    
    Attributes set by fetchNodalOutput():
        runCompletion = list of frame values for abaqus run 
                        runCompletion[0] corresponds to resultData[0,:,:], etc.
        nodeLabels    = list of nodes where output is generated
                        nodeLabels[0] cooresponds to resultData[:,0,:], etc.
        componentLabels = list of components where output is generated
                        componentLabels[0] corresponds to resultData[:,:,0], etc.
        resultData    = numpy float64 array of the actual field 
                        output data (e.g. 'U', 'COORD', etc.)
                        in the form of [frame, node, dimension]
    """
    
    #
    # Attributes (object initialization)
    #
    def __init__(self, odbName, dataName, nodeSetName):
        """ return object with desired attributes """
        
        # initialize field variable
        fieldVariable.__init__(self, odbName, dataName, nodeSetName)
        #add new attribute
        self.__componentLabels = None
        
        return
    
    #
    # Dependent Attributes
    #
    @property
    def keyName(self):
        return self.dataName

    @property
    def componentLabels(self):
        return self.__componentLabels
    
    #
    # Methods
    #
    def fetchNodalOutput(self):
        """ obtains the nodal output for the defined set """
        
        #open the output database in read-only mode
        if self.odbName.endswith('.odb'):
            odb = openOdb(self.odbName, readOnly=True)
        else:
            odb = openOdb(self.odbName + '.odb', readOnly=True)
        
        #
        # check if keyName and nodeSetName exist (Error Handling):
        #
        try:
            myNodeSet = odb.rootAssembly.nodeSets[self.nodeSetName]
        except KeyError:
            print 'Assembly level node set named %s does' \
                  'not exist in the output database %s' \
                  % (self.nodeSetName, self.odbName)
            odb.close()
            raise KeyError

        testStep = odb.steps.keys()[-1]
        if odb.steps[testStep].frames[-1].fieldOutputs.has_key(self.keyName) == 0:
            print '%s output request is not defined for' \
                  'all (or any?) steps!' % (self.keyName)
            odb.close()
            raise KeyError
        
        #
        # obtain the componentLabels so that we know what the values
        # in the ODB array mean. This will also be used to meaningfully
        # name the saved data
        #
        components = odb.steps[testStep].frames[0]. \
                     fieldOutputs[self.keyName].componentLabels
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
        stepNumber    = int(-1)
        frameNumber   = int(-1)
        runCompletion = []
        resultData    = numpy.zeros( (numframes,numnod,numdim),
                                     dtype=numpy.float64 )
        
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
                #this subset will only contain keyName data
                myFieldOutput = frame.fieldOutputs[self.keyName].getSubset(
                                region=myNodeSet)
                
                #initialize an array to temporarily store data for this frame.
                #necessary since we cannot be sure what order the nodes are in
                frameData = numpy.zeros((numnod,numdim),dtype=numpy.float64)
                
                #retrieve all the nodal data for this frame
                nodes = []
                for value in myFieldOutput.values:
                    #for all values in the frame
                    nodes.append( value.nodeLabel )
                    for i in range(0,numdim):
                        #for all defined dimensions
                        try:
                            #analysis is single precision, so data is stored
                            #as a vector in value.data
                            frameData[len(nodes)-1,i] = value.data[i]
                        except:
                            #analysis is double precision, so data is stored
                            #as a vector in value.dataDouble
                            frameData[len(nodes)-1,i] = value.dataDouble[i]

                #save frame values to result
                for i in range(0,numnod):
                    for k in range(0,len(nodes)):
                        if nodeLabels[i] == nodes[k]:
                            resultData[frameNumber,i,:] = frameData[k,:]

        #all data from the steps and frames has been collected!
        #close output database
        odb.close()
        
        #save to self
        self._runCompletion = runCompletion
        self._nodeLabels    = nodeLabels
        self._resultData    = resultData
        self._componentLabels = components
        return

    def saveCSV(self, verbose=True):
        """ save a CSV file of the data """
        for i in range(0,len(self.componentLabels)):
            self._saveOdbFieldDataCSV(self.componentLabels[i],
                                      self.resultData[:,:,i], verbose=verbose)
        return
    
    def sumNodalData(self):
        """ 
        sums the data across all nodes (but not frames).
        This is useful, for example, if you wish to get the
        total reaction force 'RF' for the node set.
        """
        #determine size of problem
        numframes = len(self.runCompletion)
        numdim    = len(self.componentLabels)
        
        #rename componentLabels to indicate they are summed
        componentLabels = []
        for i in range(0,numdim):
            componentLabels.append('summed' + self.componentLabels[i])
        componentLabels = tuple(componentLabels)
        self.componentLabels = componentLabels
        
        #initialize array
        resultData = numpy.zeros((numframes,1,numdim),dtype=numpy.float64)
        
        #perform the sum
        for dim in range(0,numdim):
            for frame in range(0,numframes):
                for n in range(0,len(self.nodeLabels)):
                    resultData[frame,0,dim] += self.resultData[frame,n,dim]
        #save
        self._resultData = resultData
        self._nodeLabels = [-1]
        return