"""
Vincente Pericoli
UC Davis
9/28/15

File that contains a class for representing/retrieving 
mesh information for an instance in the assembly of 
an ABAQUS odb file.
"""

#
# import modules
#
from odbAccess import *
from abaqusConstants import *
import os
import numpy
from myFileOperations import *

#
# object
#
class InstanceMesh(object):
    """ 
    mesh for a named instance in the Abaqus assembly
    
    only works if all elements in the instance have the same number of nodes

    Attributes:
        odbPath      = string of ODB file path name. 
                       if a full path, must be in the form of 'C:\\folder\\...\\file.odb'
        instanceName = string name of the instance you want the mesh for.
                       You can use the exact instance name as defined in the assembly (default)
                       You can also utilize partial matching, with the exactKey flag. Be very careful.
        exactKey     = (optional) logical True/False (Default True)
                       determines if partial matching is used

    Attributes set by fetchMesh():
        Nodes       = numpy array vector of all node numbers
        NodesCoords = numpy array of the nodal coordinates
                      (e.g. NodesCoords[0] is the coordinates of node 1)
        Elements    = numpy array vector of all element numbers
        ElemConnect = numpy array of the nodal connectivity for an element
                      (e.g. ElemConnect[0] is the connectivity of element 1)
        ElemType    = string of the type of element (e.g. 'CAX8R')
                      assumes that all elements are the same type. invalid otherwise.
        
    Methods:
        fetchMesh()
        saveCSV()
    """
    
    def __init__(self, odbPath, instanceName, exactKey=True):
        """ create object with requested attributes """
        
        # set by input parameters
        self.odbPath      = odbPath
        self.instanceName = instanceName.upper()
        
        # this is set as a name-mangled attribute (see below)
        self.exactKey = exactKey
        
        # set by methods (read-only)
        self._nodes       = None
        self._nodesCoords = None
        self._elements    = None
        self._elemConnect = None
        self._elemType    = None
        return
    
    # properties for read-only attributes
    @property
    def nodes(self):
        return self._nodes

    @property
    def nodesCoords(self):
        return self._nodesCoords
    
    @property 
    def elements(self):
        return self._elements
    
    @property
    def elemConnect(self):
        return self._elemConnect
        
    @property
    def elemType(self):
        return self._elemType
    
    # name mangled properties
    @property
    def exactKey(self):
        return self.__exactKey

    @exactKey.setter
    def exactKey(self, b):
        if type(b) is bool:
            self.__exactKey = b
        else:
            raise ValueError("exactKey must be boolean logical")
    
    # dependent properties
    @property
    def odbFileName(self):
        """ return name of the input file """
        return self.odbPath.split('\\')[-1]
        

    def fetchMesh(self):
        """ obtain the mesh. assign self.NodesCoords and self.ElemConnect attributes """
        #
        # open the output database in read-only mode
        #
        if self.odbPath.endswith('.odb'):
            odb = openOdb(self.odbPath, readOnly=True)
        else:
            odb = openOdb(self.odbPath + '.odb', readOnly=True)
            
        #
        # figure out what our instance dictionary key is
        #
        
        # initialize dict key
        iKey = None
        
        # determine dict key
        if self.exactKey:
            # then the instance is exactly self.instanceName
            iKey = self.instanceName
        else:
            # then the instance is a partial match of self.instanceName
            # pick the first partial match that we arrive at
            for k in odb.rootAssembly.instances.keys():
                if self.instanceName in k:
                    iKey = k
                    break
        
        #
        # define instance if it exists, otherwise error handle
        #
        try:
            myInstance = odb.rootAssembly.instances[iKey]
        except:
            odb.close()
            print "\n\n!! instance " + iKey + \
                  " is not defined in the assembly !!\n\n"
            raise KeyError
        
        # 
        # determine the size of the problem
        #
        nnod = len( myInstance.nodes )     #number of nodes
        nele = len( myInstance.elements )  #number of elements
        nnpe = len( myInstance.elements[0].connectivity ) #number of nodes per element
        
        #
        # obtain element type (assume instance is all the same type)
        #
        elemType = myInstance.elements[0].type
        
        #
        # preallocate arrays
        #
        nodes       = numpy.zeros((nnod,1), dtype=int)
        elements    = numpy.zeros((nele,1), dtype=int)
        nodesCoords = numpy.zeros((nnod,3), dtype=numpy.float64)
        elemConnect = numpy.zeros((nele,nnpe), dtype=int)
        
        #
        # obtain node information/data
        #
        for i,n in enumerate( myInstance.nodes ):
            nodes[i,0]       = n.label
            nodesCoords[i,:] = n.coordinates
        
        #
        # obtain element information/data
        #
        for i,e in enumerate( myInstance.elements ):
            elements[i,0]    = e.label
            elemConnect[i,:] = e.connectivity
        
        #
        # save to object attributes:
        #
        self._nodes       = nodes
        self._nodesCoords = nodesCoords
        self._elements    = elements
        self._elemConnect = elemConnect
        self._elemType    = elemType
        return

        
    def saveCSV(self, saveDir=None):
        """ saves CSV files to the requested directory """
        #
        # determine save directory
        #
        if saveDir is None:
            # define default if otherwise undefined
            saveDir = os.path.dirname(self.odbFileName)
            if saveDir is "":
                saveDir = os.getcwd()
            saveDir += '\\'
        elif saveDir[-2:] != '\\':
            saveDir += '\\'
        
        #
        # open files for writing
        #
        
        # name of input file, excl. extension
        odbName = os.path.basename(self.odbPath)
        odbName = os.path.splitext(odbName)[0]
        
        # create file handles
        dummy = saveDir + odbName + '_' + self.instanceName + '_nodesCoords.csv'
        nodeFile = open(dummy,'w')
        
        dummy = saveDir + odbName + '_' + self.instanceName + '_elemConnect.csv'
        elemFile = open(dummy,'w')
        
        # save to CSV
        self.__saveArrayCSV(nodeFile, self.nodesCoords)
        self.__saveArrayCSV(elemFile, self.elemConnect)
        
        # close file handles
        nodeFile.close()
        elemFile.close()
        return
        
    def __saveArrayCSV(self, fhandle, array):
        """ 
        writes array to CSV, given a file handle 
        written for node and elemConnect arrays...
        because CSV rows are prepended with their # (i.e. node # or element #)
        """
        
        #determine shape of array
        nrow,ncol = array.shape
        
        for row in range(0,nrow):
            #start a new line
            line = str(row+1)
            for col in range(0,ncol):
                line += ', ' + str(array[row,col])
            #end of line, write to file
            line += '\n'
            fhandle.write(line)
        
        return