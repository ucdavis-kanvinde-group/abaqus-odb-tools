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


class IntPtVariable(object):
    """ An integration point variable whose results
    are extrapolated to the nodes of a defined set.
    
    Attributes:
        odbName  = string name of ODB file/location
        dataName = string name of the data (e.g. 'MISES')
        keyName  = string name of hierarchical Abaqus output (e.g. 'S')
        nodeSetName = string of the requested node set
        
    Attributes set by fetchNodalOutput():
        runCompletion = list of frame values for abaqus run 
        nodeLabels    = list of nodes where output is generated
        resultData    = numpy float64 array of the actual field 
                        output data (e.g. PEEQ, mises, etc). 
                        Rows correspond to frame values,
                        columns correspond to nodes.
    """
    
    #
    # Attributes (object initialization)
    #
    def __init__(self, odbName, dataName, nodeSetName):
        """ return object with the desired attributes """
        self.odbName     = odbName
        self.dataName    = dataName.upper()    # must be upper-case
        self.nodeSetName = nodeSetName.upper() # must be upper-case
        
        # these are set by fetchNodalOutput()
        self.runCompletion = None
        self.nodeLabels    = None
        self.resultData    = None
                       
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
        elif: self.dataName == 'MISES':
            return 'S'
        elif: self.dataName == 'PRESS':
            return 'S'
        elif: self.dataName == 'INV3':
            return 'S'
        else:
            raise Exception('dataName')
    
    @property
    def abqAttrib(self):
        """ 
        Abaqus Attribute property... this is the name of the
        location where our field output data values are stored
        in the abaqus ODB structure
        """
        if self.dataName == 'PEEQ':
            return 'data'
        elif: self.dataName == 'MISES':
            return 'mises'
        elif: self.dataName == 'PRESS':
            return 'press'
        elif: self.dataName == 'INV3':
            return 'inv3'
        else:
            raise Exception('dataName')

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
        self.runCompletion = runCompletion
        self.nodeLabels    = nodeLabels
        self.resultData    = resultData
        
        #all data from the steps and frames has been collected!
        #close output database
        odb.close()