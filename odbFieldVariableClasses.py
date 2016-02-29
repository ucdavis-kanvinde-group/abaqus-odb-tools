"""
Vincente Pericoli
UC Davis
16 Sept 2015

for README, license, and other info, see:
https://github.com/ucdavis-kanvinde-group/abaqus-odb-tools


Classes for representing Abaqus ODB field variables.

Contained in this file:
    * fieldVariable class: superclass which the others inherit
    * IntPtVariable class: represents an integration point variable (e.g. Mises, PEEQ, etc.)
    * NodalVariable class: represents a nodal variable (e.g. U, COORD, etc.)
    * ElementVariable class: represents an element variable (e.g. EVOL)
"""

#
# Import Modules
#
from odbAccess import *
from abaqusConstants import *
import numpy
import sys
import re
import os
from myFileOperations import *

#
# Classes
#

class fieldVariable(object):
    """ a base class for field variables; other classes inherit this class. """
    #
    # Attributes (object initialization)
    #
    def __init__(self, odbPath, dataName, setName):
        """ return object with the desired attributes """
        # these attributes have properties (below) to protect the 
        # object from becoming unstable or broken
        self._odbPath  = odbPath
        self._dataName = dataName.upper() # must be upper-case
        self._setName  = setName.upper()  # must be upper-case

        # these are set by methods
        self._totalTime     = None
        self._nodeLabels    = None
        self._elementLabels = None
        self._intPtLabels   = None
        self._resultData    = None
        return
    
    #
    # Getters to make output attributes read-only
    #
    @property
    def totalTime(self):
        return self._totalTime
    
    @property
    def nodeLabels(self):
        return self._nodeLabels
    
    @property
    def elementLabels(self):
        return self._elementLabels

    @property
    def intPtLabels(self):
        return self._intPtLabels
        
    @property
    def resultData(self):
        return self._resultData

    #
    # Getters and Setters to protect Object
    #
    @property
    def odbPath(self):
        return self._odbPath
    
    @odbPath.setter
    def odbPath(self,s):
        if not isinstance(s,str):
            raise TypeError('Must be a string!')
        self._odbPath = s
        #changing this attribute will invalidate any field data
        self.reset()
        return

    @property
    def odbName(self):
        """ returns odb file name (with file extensions) """
        return self.odbPath.split('\\')[-1]
        
    @property
    def dataName(self):
        return self._dataName
    
    @dataName.setter
    def dataName(self, s):
        #call to upper() will automatically throw exception if not string
        #so, no need to do error handling
        self._dataName = s.upper() 
        #changing this attribute will invalidate any field data
        self.reset()
        return

    @property
    def setName(self):
        return self._setName
    
    @setName.setter
    def setName(self, s):
        #call to upper() will automatically throw exception if not string
        #so, no need to do error handling
        self._setName = s.upper()
        #changing this attribute will invalidate any field data
        self.reset()
        return
        
    #
    # Methods
    #
    def reset(self):
        """ resets any results to None """
        print "\nWarning: instance is being reset\n"
        self._totalTime     = None
        self._nodeLabels    = None
        self._elementLabels = None
        self._intPtLabels   = None
        self._resultData    = None
        return
    
    def _open_odb_check_keys(self,setType):
        """ 
        opens ODB file, checks if a set of setType exists
        in the assembly, and whether keyName is a defined
        output quanitity.
        
        setType should be a string of 'NODE' or 'ELEMENT'
        
        returns [odb, mySet]
        """
    
        #open the output database in read-only mode
        if self.odbPath.endswith('.odb'):
            odb = openOdb(self.odbPath, readOnly=True)
        else:
            odb = openOdb(self.odbPath + '.odb', readOnly=True)

        
        #
        # check if setName exists, and open it
        #
        try:
            #open the node or element set
            if setType.upper() == 'NODE':
                mySet = odb.rootAssembly.nodeSets[self.setName]
            elif setType.upper() == 'ELEMENT':
                mySet = odb.rootAssembly.elementSets[self.setName]
            else:
                print "\n\n!! unknown setType defined !!\n\n"
                raise Exception
        except KeyError:
            #the requested set does not exist...
            print '\n!! Assembly level %s set named %s does' \
                  'not exist in the output database %s !!\n\n' \
                    % (setType, self.setName, self.odbPath)
            odb.close()
            raise Exception
        
        #
        # check if keyName is a requested output
        #
        testStep = odb.steps.keys()[-1]
        if odb.steps[testStep].frames[-1].fieldOutputs.has_key(self.keyName) == 0:
            print '\n\n%s output request is not defined for ' \
                  'all (or any?) steps!\n\n' % (self.keyName)
            odb.close()
            raise Exception
        
        return [odb, mySet]
    
    def _numframes(self, odb):
        """
        given an odb, loop through STEPs, obtaining
        the total number of FRAMEs in the analysis.
        
        does not include redundant frames.
        useful for preallocating numpy arrays.
        """

        totalTime = []
        #loop steps and frames
        for step in odb.steps.values():
            for frame in step.frames:
                time = step.totalTime + frame.frameValue
                if time not in totalTime:
                    totalTime.append(time)
        
        return len(totalTime)
    
    def _saveOdbFieldDataCSV(self, dataTitle=None, dataSet=None, 
                            verbose=True, customFileName=None):
        """
        saves an ODB data array to a CSV file
        dependencies: re, sys, os, numpy

        formatted so that each node (nodeLabels) is a column,
        and each frame value (totalTime) is a row. For example,
        the file is saved so that totalTime (the frame values) 
        itself is in the left-most column, and the nodeLabels are saved
        in the top-most row. Then, dataSet (can be anything... PEEQ, Mises,
        Pressure, etc.) is saved to the right of totalTime and below 
        nodeLabels. In this way, each column of dataSet should correspond to
        a specific node (or element, or integration point, or whatever you pass
        in as nodeLabels),
        and each row should correspond to a specific frame value (or whatever you pass
        in as totalTime).
        
        verbose is an optional input (default true) which defines where there will be
        a "verbose" output to the command window or not. If True, it will tell you
        when files are saved or replaced.
        """
        #assign dataTitle and dataSet if not defined
        if dataTitle is None:
            dataTitle = self.dataName
        if dataSet is None:
            dataSet = self.resultData
            
        #set which labels to write
        if self.intPtLabels is not None:
            #we want to write the element labels
            #because the array contains data for
            #all elements for a single IntPt
            labels = self.elementLabels
            #write in file as such
            line1  = '"element (right):"'
        elif self.elementLabels is not None:
            #we want to write the element labels
            labels = self.elementLabels
            #write in file as such
            line1 = '"element (right):"'
        elif self.nodeLabels is not None:
            #we want to write the node labels
            labels = self.nodeLabels
            #write in file as such
            line1 = '"node (right):"'
        else:
            raise Exception("Labels are undefined!")
        

        #assign file name to save
        if customFileName is None:
            #custom name not requested, figure out our own name
            
            #strip away file extension of odb
            odbName = os.path.splitext(self.odbName)[0]
            
            #define save file name
            saveFileName = (odbName + '_' + self.setName + '_' + dataTitle + '.csv')
        else:
            saveFileName = customFileName + '.csv'

        #ensure filename is safe to write
        saveFileName = safe_filename(saveFileName)

        #delete any pre-existing file
        check_delete(saveFileName, verbose)

        #open file with write permissions
        saveFile = open(saveFileName,'w')

        #write labels line and empty line
        #line1 set already (see above)
        line2 = '"frame (below):"'
        for label in labels:
            line1 += ', ' + str(label)
            line2 += ', ' + '""'
        line1 += '\n'
        line2 += '\n'
        saveFile.write(line1)
        saveFile.write(line2)

        #begin writing dataSet, prepend lines with totalTime:
        for i in range(0,len(self.totalTime)):
            #for all frames
            line = str(self.totalTime[i])

            for k in range(0,len(labels)):
                #for all labels (node or element)
                
                #need try/except for if there is only 1 label (vector array)
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
    could be extrapolated to the nodes of a defined set.
    
    Attributes:
        odbPath  = string name of ODB file/location
        dataName = string name of the data (e.g. 'MISES')
        setName = string of the requested node set
        
    Dependent Attributes (automatically calculated):
        keyName   = string name of hierarchical Abaqus output (e.g. 'S')
                    depends on setting of dataName
        abqAttrib = string name of data storage location
                    depends on setting of dataName
    
    Attributes set by fetchNodalExtrap():
        totalTime = tuple of frame values for abaqus run 
                        totalTime[i] corresponds to resultData[i,:,:], etc.
        elementLabels = tuple of element numbers where output is generated
                        elementLabels[e] corresponds to resultData[:,:,e]
        nodeLabels    = numpy int array (rank-2) of the nodal connectivity for
                        each element in elementLabels. So, nodeLabels[e,:] 
                        cooresponds to the nodal connectivity of elementLabel[e].
                        nodeLabels[e,n] corresponds to the n-th node of elementLabel[e],
                        per the ABAQUS node numbering convention.
        resultData    = numpy float64 array (rank-3) of the actual field output data 
                        (e.g. PEEQ, mises, etc) at nodal point locations (obtained via
                        ABAQUS extrapolation technique). 
                        Access is: resultData[i,n,e]
        
    Attributes set by fetchNodalAverage():
        totalTime = tuple of frame values for abaqus run 
                        totalTime[0] corresponds to resultData[0,:], etc.
        nodeLabels    = tuple of nodes where output is generated
                        nodeLabels[0] cooresponds to resultData[:,0], etc.
        resultData    = numpy float64 array (rank-2) of the actual field 
                        output data (e.g. PEEQ, mises, etc). 
                        Rows correspond to frame values,
                        columns correspond to nodes.
    
    Attributes set by fetchElementAverage():
        totalTime = see above
        elementLabels = tuple of elements where output is generated
                        elemental analog to nodeLabels
                        elementLabels[e] corresponds to resultData[:,e]
        resultData    = see above (except w.r.t. elements)

    Attributes set by fetchIntPtData():
        totalTime = see above
        intPtLabels   = tuple of integration point labels where output is generated
                        intPtLabels[ip] corresponds to resultData[:,ip,:]
        elementLabels = tuple of element labels where output is generated
                        elementLabels[e] corresponds to resultData[:,:,e]
        resultData    = numpy float64 array (rank-3) of the actual field output data 
                        (e.g. PEEQ, mises, etc) at integration point locations
                        Access is: resultData[i,ip,e]
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
            raise Exception('That dataName has not been programmed! (yet?)')
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
            raise Exception('That dataName has not been programmed! (yet?)')
        return

    #
    # Name Mangled Methods
    #
    def __fetchElementLabels(self, myElemSet):
        """ return a tuple of sorted element labels """
        elementLabels = [e.label for e in myElemSet.elements[0]]
        elementLabels.sort()
        return tuple(elementLabels)
    
    def __fetchNodeLabels(self, myNodeSet):
        """ returns a tuple of sorted node labels """
        nodeLabels = [n.label for n in myNodeSet.nodes[0]]
        nodeLabels.sort()
        return tuple(nodeLabels)
        
    #
    # Methods
    #
    def fetchNodalExtrap(self):
        """ fetch integration point field output at the node locations
        (for the desired element set) using extrapolation techniques.
        Since we are requesting IP field output at the nodes, 
        ABAQUS will extrapolate using basis functions. This function
        does NOT perform any averaging at all. The nodal values for 
        each element are stored, according to the ABAQUS node 
        numbering scheme.
        
        this method sets the following attributes:
            totalTime
            elementLabels
            nodeLabels
            resultData
        """
        #open output database and obtain myElemSet
        odb,myElemSet = self._open_odb_check_keys('ELEMENT')
        
        #
        # figure out details on how big the problem is
        #
        
        #number of elements in set:
        numele = len(myElemSet.elements[0])
        #assuming all elements are the same, number of nodes per elem
        nnpe = len(myElemSet.elements[0][0].connectivity)
        # obtain numframes
        numframes = self._numframes(odb)
        # determine the total number of elements and nodes in the instance where the set is defined on
        i_numele = len( odb.rootAssembly.instances[myElemSet.instanceNames[0]].elements )
        i_numnod = len( odb.rootAssembly.instances[myElemSet.instanceNames[0]].nodes )
        
        #
        # obtain element labels
        #
        elementLabels = self.__fetchElementLabels(myElemSet)
        # set as array for logical indexing
        elementLabels = numpy.asarray(elementLabels, dtype=int)
        
        #
        # nodeLabels will essentially be the element connectivity of the set
        #
        nodeLabels = numpy.zeros((numele,nnpe),dtype=int)
        for e in myElemSet.elements[0]:
            nodeLabels[numpy.where(elementLabels==e.label)[0][0],:] = e.connectivity
            
        #
        # iterate through the STEPs and FRAMEs, saving the info as applicable
        #

        #initialize
        totalTime   = []
        resultData  = numpy.zeros((numframes,nnpe,numele),dtype=numpy.float64)
        
        #loop steps
        for step in odb.steps.values():

            #loop frames (step increments)
            for frame in step.frames:
                #calculate the "time" of this specific frame
                frameTime = step.totalTime + frame.frameValue
                #check to see if this is a duplicate frame (happens between steps)
                if frameTime in totalTime:
                    #this is a duplicate. continue to next frame
                    continue
                else:
                    #this is not a duplicate; save to totalTime
                    totalTime.append(frameTime)
                
                # allocate temporary storage arrays for data.
                frameData = numpy.zeros((i_numnod,i_numele),dtype=numpy.float64)
                
                # obtain a subset of the field output (based on myElemSet)
                # this subset will only contain keyName data
                myFieldOutput = frame.fieldOutputs[self.keyName].getSubset(
                    position=ELEMENT_NODAL,region=myElemSet)
                
                # obtain all the data for this frame
                for value in myFieldOutput.values:
                    # element number is stored in value.elementLabel
                    e = value.elementLabel
                    # node number is stored in value.nodeLabel
                    n = value.nodeLabel
                    # set the data into temporary storage array
                    frameData[n-1,e-1] = numpy.float64( getattr(value, self.abqAttrib) )
                    
                # save to resultData.
                # even though this seems like a strange way to go about it,
                # cProfile has shown this is significantly more efficient compared to 
                # inserting directly into resultData[] with tuple.index() indexing 
                # (i.e. without using a temporary frameData at all).
                for i,e in enumerate(elementLabels):
                    resultData[len(totalTime)-1,:,i] = frameData[nodeLabels[i,:]-1,e-1]
        
        #set the proper attributes
        self._totalTime     = tuple(totalTime)
        self._nodeLabels    = nodeLabels
        self._elementLabels = elementLabels
        self._resultData    = resultData
        
        #flag that this method has been executed
        self.__methodFlag = 'fetchNodalData'
        
        #all data from the steps and frames has been collected!
        #close output database
        odb.close()
        return
        
    def fetchNodalAverage(self):
        """ fetch the average nodal point field output
        for the desired node set. Return an average
        for each node in the set.
        
        this method sets the following attributes:
            totalTime
            nodeLabels
            resultData
        """
        #open output database and obtain myNodeSet
        odb,myNodeSet = self._open_odb_check_keys('NODE')
        
        #
        # figure out which nodes are in myNodeSet, and sort them
        #
        nodeLabels = self.__fetchNodeLabels(myNodeSet)
        numnod = len(nodeLabels)
        #convert to array for logical indexing (required in averaging scheme)
        nodeLabels = numpy.asarray(nodeLabels,dtype=int)
        
        #
        # determine the total number of nodes in the instance where the set is defined on
        #
        i_numnod = len( odb.rootAssembly.instances[myNodeSet.instanceNames[0]].nodes )
        
        #
        # obtain numframes
        #
        numframes = self._numframes(odb)

        #
        # iterate through the STEPs and FRAMEs, saving the info as applicable
        #

        #initialize
        totalTime  = []
        resultData = numpy.zeros((numframes,numnod),dtype=numpy.float64)
                
        
        #loop steps
        for step in odb.steps.values():

            #loop frames (step increments)
            for frame in step.frames:
                #calculate the "time" of this specific frame
                frameTime = step.totalTime + frame.frameValue
                #check to see if this is a duplicate frame (happens between steps)
                if frameTime in totalTime:
                    #this is a duplicate. continue to next frame
                    continue
                else:
                    #this is not a duplicate; save to totalTime
                    totalTime.append(frameTime)

                #initialize arrays.
                #these are used as temporary storage for 
                #averaging nodal results in the current frame.
                frameData   = numpy.zeros((i_numnod,1),dtype=numpy.float64)
                nValPerNode = numpy.zeros((i_numnod,1),dtype=numpy.float64)
                
                #obtain a subset of the field output (based on myNodeSet)
                #this subset will only contain keyName data
                myFieldOutput = frame.fieldOutputs[self.keyName].getSubset(
                    position=ELEMENT_NODAL,region=myNodeSet)
                
                #loop through all data values for this frame
                for value in myFieldOutput.values:
                    #sum the data into frameData, while keeping track of the
                    #number of sums with nValPerNode.
                    
                    #node number is stored in value.nodeLabel
                    #nodal data is stored in value.(abqAttrib)
                    frameData[value.nodeLabel-1,0]   += getattr(value, self.abqAttrib)
                    nValPerNode[value.nodeLabel-1,0] += 1.0
                
                #average the nodal values so that there is one field data value 
                #per node in the frame, and save frame values to resultData.
                #note that the default numpy array divide is element-wise (like ./ in MATLAB)
                resultData[len(totalTime)-1,:] = frameData[nodeLabels-1,0] / nValPerNode[nodeLabels-1,0]

        #set the proper attributes
        self._totalTime  = tuple(totalTime)
        self._nodeLabels = tuple(nodeLabels)
        self._resultData = resultData
        
        #flag that this method has been executed
        self.__methodFlag = 'fetchNodalAverage'
        
        #all data from the steps and frames has been collected!
        #close output database
        odb.close()
        return
    
    def fetchIntPtData(self):
        """ fetch the ingegration point field output
        for the desired element set. Return the values for
        each integration point in each element in the set 
        
        this methods sets the following attributes:
            totalTime
            intPtLabels
            resultData
        """
        
        #open output database and obtain myElemSet
        odb,myElemSet = self._open_odb_check_keys('ELEMENT')
        
        #
        # figure out details on how big the problem is
        #
        
        # figure out how many integration points there are (total)
        testStep = odb.steps.keys()[-1]
        testFrameData = odb.steps[testStep].frames[-1].fieldOutputs[self.keyName].getSubset(
                            region=myElemSet,position=INTEGRATION_POINT)
        numips = len(testFrameData.values) #there is a value for every int point in the region
        
        # determine the total number of elements in the instance where the set is defined on
        i_numel = len( odb.rootAssembly.instances[myElemSet.instanceNames[0]].elements )
        
        # figure out how many elements and IPs per element there are in the set itself
        numel = len(myElemSet.elements[0])   #num elements
        nipe  = numips/numel                 #num integration pts per elem
        intPtLabels = tuple(range(1,nipe+1)) #list of all IP numbers
        
        # get a list of all elements in the set
        elementLabels = self.__fetchElementLabels(myElemSet)
        # convert to array so we can use logical indexing
        elementLabels = numpy.asarray(elementLabels,dtype=int)
        
        # determine out how many frames there are
        numframes = self._numframes(odb)

        #
        # iterate through the STEPs and FRAMEs, saving the info as applicable
        #

        #initialize
        totalTime  = []
        resultData = numpy.zeros((numframes,nipe,numel),dtype=numpy.float64)
                
        #loop steps
        for step in odb.steps.values():

            #loop frames (step increments)
            for frame in step.frames:
                #calculate the "time" of this specific frame
                frameTime = step.totalTime + frame.frameValue
                #check to see if this is a duplicate frame (happens between steps)
                if frameTime in totalTime:
                    #this is a duplicate. continue to next frame
                    continue
                else:
                    #this is not a duplicate; save to totalTime
                    totalTime.append(frameTime)

                # create temporary storage array
                frameData = numpy.zeros((nipe,i_numel),dtype=numpy.float64)
                
                #obtain a subset of the field output (based on myElemSet)
                #this subset will only contain keyName data
                myFieldOutput = frame.fieldOutputs[self.keyName].getSubset(
                    position=INTEGRATION_POINT,region=myElemSet)
                
                #obtain all the data for this frame
                for value in myFieldOutput.values:
                    #element number is stored in value.elementLabel
                    e  = value.elementLabel
                    #integration point number is stored in value.integrationPoint
                    ip = value.integrationPoint
                    # set the data into temporary storage array
                    frameData[ip-1,e-1] = numpy.float64( getattr(value, self.abqAttrib) )
                
                # save to resultData
                resultData[len(totalTime)-1,:,:] = frameData[:,elementLabels-1]
        
        #set the proper attributes
        self._totalTime     = tuple(totalTime)
        self._intPtLabels   = intPtLabels
        self._elementLabels = elementLabels
        self._resultData    = resultData
        
        #flag that this method has been executed
        self.__methodFlag = 'fetchIntPtData'
        
        #all data from the steps and frames has been collected!
        #close output database
        odb.close()
        return
        
    def fetchElementAverage(self):
        """ fetch the integration point field output
        for the desired element set. Return an average
        for each element in the set.
        
        this method sets the following attributes:
            totalTime
            elementLabels
            resultData
            
        *** NOTE: 
        this method still uses an old and slow averaging scheme.
        needs to be updated to the new scheme... 
        see fetchNodalAverage() for newer scheme.
        """

        #open output database and obtain myElemSet
        odb,myElemSet = self._open_odb_check_keys('ELEMENT')
        
        #
        # figure out which elements are in myElemSet, and sort them
        #
        elementLabels = self.__fetchElementLabels(myElemSet)
        numele = int(len(elementLabels))

        #
        # obtain numframes
        #
        numframes = self._numframes(odb)

        #
        # iterate through the STEPs and FRAMEs, saving the info as applicable
        #

        #initialize
        totalTime  = []
        resultData = numpy.zeros((numframes,numele),dtype=numpy.float64)
                
        #loop steps
        for step in odb.steps.values():

            #loop frames (step increments)
            for frame in step.frames:
                #calculate the "time" of this specific frame
                frameTime = step.totalTime + frame.frameValue
                #check to see if this is a duplicate frame (happens between steps)
                if frameTime in totalTime:
                    #this is a duplicate. continue to next frame
                    continue
                else:
                    #this is not a duplicate; save to totalTime
                    totalTime.append(frameTime)

                #initialize frame array.
                #this is used as temporary storage for 
                #averaging integration point results in the current frame
                frameData      = numpy.zeros((numele,2),dtype=numpy.float64)
                frameData[:,0] = numpy.float64(elementLabels) #this is included for debugging
                
                #obtain a subset of the field output (based on myElemSet)
                #this subset will only contain keyName data
                myFieldOutput = frame.fieldOutputs[self.keyName].getSubset(
                    position=INTEGRATION_POINT,region=myElemSet)
                
                #obtain all the nodal data for this frame
                tempElems = [];
                tempData  = [];
                for value in myFieldOutput.values:
                    #element number is stored in value.elementLabel
                    tempElems.append(value.elementLabel)
                    #int. pt. data is stored in value.(abqAttrib)
                    tempData.append(numpy.float64( 
                                    getattr(value, self.abqAttrib) ))


                #average the int. pt. values so that there is
                #one field data value per node in the frame
                for i in range(0,len(elementLabels)):
                    #for all element labels
                    ip_data = []
                    for k in range(0,len(tempElems)):
                        if elementLabels[i] == tempElems[k]:
                            #pick up all data belonging to element
                            ip_data.append(tempData[k])
                    #save average to frameData
                    frameData[i,1] = numpy.mean(ip_data, dtype=numpy.float64)

                #save frame values to result
                resultData[len(totalTime)-1,:] = frameData[:,1]

        #set the proper attributes
        self._totalTime = tuple(totalTime)
        self._elementLabels = tuple(elementLabels)
        self._resultData    = resultData
        
        #flag that this method has been executed
        self.__methodFlag = 'fetchElementAverage'
        
        #all data from the steps and frames has been collected!
        #close output database
        odb.close()
        return
        
    def saveCSV(self, verbose=True):
        """ save a CSV file of data """
        if self.__methodFlag == 'fetchIntPtData':
            for i in self.intPtLabels:
                self._saveOdbFieldDataCSV(dataTitle=(self.dataName + '_IP' + str(i)),
                                      dataSet=self.resultData[:,i-1,:], verbose=verbose)
        
        elif self.__methodFlag == 'fetchNodalData':
            numele,nnpe = self.nodeLabels.shape
            for i in range(0,nnpe):
                self._saveOdbFieldDataCSV(dataTitle=(self.dataName + '_NOD' + str(i)),
                                      dataSet=self.resultData[:,i,:], verbose=verbose)
        else:
            self._saveOdbFieldDataCSV(verbose=verbose)
        return


class NodalVariable(fieldVariable):
    """ 
    A nodal variable whose results are obtained on the defined set 
    
    Attributes:
        odbPath  = string name of ODB file/location
        dataName = string name of the data (e.g. 'U')
        setName = string of the requested node set
    
    Attributes set by fetchNodalAverage():
        totalTime = list of frame values for abaqus run 
                        totalTime[0] corresponds to resultData[0,:,:], etc.
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
    def __init__(self, odbPath, dataName, setName):
        """ return object with desired attributes """
        
        # initialize field variable
        fieldVariable.__init__(self, odbPath, dataName, setName)
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
        return self._componentLabels
    
    #
    # Methods
    #
    def fetchNodalOutput(self):
        """ obtains the nodal output for the defined set """
        

        #open output database and obtain myElemSet
        odb,myNodeSet = self._open_odb_check_keys('NODE')
        
        #
        # obtain the componentLabels so that we know what the values
        # in the ODB array mean. This will also be used to meaningfully
        # name the saved data
        #
        testStep = odb.steps.keys()[-1]
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
        # obtain numframes
        #
        numframes = self._numframes(odb)

        #
        # iterate through the STEPs and FRAMEs, saving the info as applicable
        #

        #initialize
        totalTime = []
        resultData    = numpy.zeros( (numframes,numnod,numdim),
                                     dtype=numpy.float64 )
        
        #loop steps
        for step in odb.steps.values():

            #loop frames (step increments)
            for frame in step.frames:
                #calculate the "time" of this specific frame
                frameTime = step.totalTime + frame.frameValue
                #check to see if this is a duplicate frame (happens between steps)
                if frameTime in totalTime:
                    #this is a duplicate. continue to next frame
                    continue
                else:
                    #this is not a duplicate; save to totalTime
                    totalTime.append(frameTime)

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
                            resultData[len(totalTime)-1,i,:] = frameData[k,:]

        #save to attributes
        self._totalTime   = tuple(totalTime)
        self._nodeLabels      = tuple(nodeLabels)
        self._resultData      = resultData
        self._componentLabels = tuple(components)
        
        #all data from the steps and frames has been collected!
        #close output database
        odb.close()
        return

    def sumNodalOutput(self):
        """ 
        sums the data across all nodes (but not frames).
        This is useful, for example, if you wish to get the
        total reaction force 'RF' for the node set.
        """
        #determine size of problem
        numframes = len(self.totalTime)
        numdim    = len(self.componentLabels)
        
        #rename componentLabels to indicate they are summed
        componentLabels = []
        for i in range(0,numdim):
            componentLabels.append('summed' + self.componentLabels[i])
        componentLabels = tuple(componentLabels)
        
        #initialize array
        resultData = numpy.zeros((numframes,1,numdim),dtype=numpy.float64)
        
        #perform the sum
        for dim in range(0,numdim):
            for frame in range(0,numframes):
                for n in range(0,len(self.nodeLabels)):
                    resultData[frame,0,dim] += self.resultData[frame,n,dim]
        #save
        self._resultData = resultData
        self._nodeLabels = (-1,)
        self._componentLabels = componentLabels
        return
    
    def avgNodalOutput(self):
        """
        averages the data across all nodes (but not frames).
        This is useful, for example, if you wish to get the
        average displacement of a surface (node set)
        """
        #determine size of problem
        numframes = len(self.totalTime)
        numdim    = len(self.componentLabels)
        
        #rename componentLabels to indicate they are averaged
        componentLabels = []
        for i in range(0,numdim):
            componentLabels.append('average' + self.componentLabels[i])
        componentLabels = tuple(componentLabels)
        
        #initialize array
        resultData = numpy.zeros((numframes,1,numdim),dtype=numpy.float64)
        
        #perform the average
        for dim in range(0,numdim):
            for frame in range(0,numframes):
                resultData[frame,0,dim] = numpy.mean( self.resultData[frame,:,dim] )

        #save
        self._resultData = resultData
        self._nodeLabels = (-1,)
        self._componentLabels = componentLabels
        return
    
    def saveCSV(self, verbose=True):
        """ save a CSV file of the data """
        for i in range(0,len(self.componentLabels)):
            self._saveOdbFieldDataCSV(dataTitle=self.componentLabels[i],
                                      dataSet=self.resultData[:,:,i], verbose=verbose)
        return


class ElementVariable(fieldVariable):
    """ 
    any variable intrinsic to a whole element itself (like volume)
    which is not represented through nodes or integration points
    """
    
    @property
    def keyName(self):
        """ 
        similar to IntPtFieldvariable
        """
        if self.dataName == 'EVOL':
            return 'EVOL'
        else:
            raise Exception('Unknown dataName assignment!')
        return
        
    
    def fetchInitialElementVolume(self):
        """ obtain the initial (frame 0) EVOL """
        
        #open output database and obtain myElemSet
        odb,myElemSet = self._open_odb_check_keys('ELEMENT')
        
        #
        # figure out which elements are in myElemSet, and sort them
        #
        elementLabels = []
        for e in myElemSet.elements[0]: #for some reason, this is a 1-element tuple...
            elementLabels.append(e.label)
        elementLabels.sort()
        numele = int(len(elementLabels))

        #
        # Open up Step 1 Frame 1, and save EVOL
        #
        
        #define abaqus field
        firstStep    = odb.steps.keys()[0]
        firstFrame   = odb.steps[firstStep].frames[0]
        initialField = firstFrame.fieldOutputs[self.keyName].getSubset(region=myElemSet)
        
        #obtain the data
        tempData      = []
        elementLabels = []
        for value in initialField.values:
            #element number is stored in value.elementLabel
            elementLabels.append(value.elementLabel)
            # EVOL is stored in data or dataDouble
            try:
                tempData.append(numpy.float64( value.data ))
            except:
                tempData.append(numpy.float64( value.dataDouble ))

        #save data as a numpy array
        resultData = numpy.zeros((1,numele),dtype=numpy.float64)
        resultData[0,:] = tempData
        
        #save to self
        self._elementLabels = tuple(elementLabels)
        self._resultData    = resultData
        self._totalTime     = (0,)
        
        #close output database and return
        odb.close()
        return

    def saveCSV(self, verbose=True):
        """ save CSV file of the data """
        self._saveOdbFieldDataCSV(verbose=verbose)
        return
