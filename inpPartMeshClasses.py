"""
Vincente Pericoli
UC Davis
9/28/15

File that contains a class for retrieving mesh information
from Abaqus input files
"""

#
# import modules
#
import re
import os
import numpy
from myFileOperations import *

#
# object
#
class PartMesh(object):
    """ 
    mesh for a named part in Abaqus

    Attributes:
        inpPath  = string of input file path name. 
                   if a full path, must be in the form of 'C:\\folder\\...\\file.inp'
        partName = string name of the part you want the mesh for.
                   you will encounter a serious bug if other parts contain exactly this part name 
                   (e.g. if you want 'part1' but there is also a part named 'part11')

    Attributes set by fetchMesh():
        Nodes       = numpy array vector of all node numbers
        NodesCoords = numpy array of the nodal coordinates
                      (e.g. NodesCoords[0] is the coordinates of node 1)
        Elements    = numpy array vector of all element numbers
        ElemConnect = numpy array of the nodal connectivity for an element
                      (e.g. ElemConnect[0] is the connectivity of element 1)
        ElemType    = string of the type of element (e.g. 'CAX8R')
        
    Methods:
        fetchMesh()
        saveCSV()
    """
    
    def __init__(self, inpPath, partName):
        """ create object with requested attributes """
        
        # set by input parameters
        self.inpPath     = inpPath
        self.partName    = partName
        
        # set by methods (read-only)
        self._Nodes       = None
        self._NodesCoords = None
        self._Elements    = None
        self._ElemConnect = None
        self._ElemType    = None
        return
    
    # properties for read-only attributes
    @property
    def nodes(self):
        return self._Nodes

    @property
    def nodesCoords(self):
        return self._NodesCoords
    
    @property 
    def elements(self):
        return self._Elements
    
    @property
    def elemConnect(self):
        return self._ElemConnect
        
    @property
    def elemType(self):
        return self._ElemType
    
    # dependent properties
    @property
    def inpFileName(self):
        """ return name of the input file """
        return self.inpPath.split('\\')[-1]
        

    def fetchMesh(self):
        """ obtain the mesh. assign self.NodesCoords and self.ElemConnect attributes """
        
        # define lists
        nodeList  = []
        coordList = []
        connList  = []
        elemList  = []
        
        # initialize
        correctPart = False
        
        # open input file and walk through line-by-line
        with open(self.inpPath,'r') as fileObj:
            for line in fileObj:
                
                # search for the requested part
                if ('*Part' in line) and (self.partName in line):
                    correctPart = True
                    continue

                if correctPart:
                    # determine if a keyword is called
                    if '*Node' in line:
                        # we are on the "nodes" section
                        nodes    = True
                        elements = False
                        continue
                        
                    elif '*Element' in line:
                        # we are on the "elements" section
                        nodes    = False
                        elements = True
                        # obtain and save the element type
                        type_index = line.find('=') + 1
                        ElemType   = line[type_index:]
                        # strip away any newline chars
                        ElemType = ElemType.rstrip()
                        continue
                        
                    elif '*' in line:
                        # end of part has been reached. terminate loop
                        break

                    # capture nodal data
                    if nodes:
                        # remove whitespace from line
                        n_line = line.replace(" ","")
                        # split line into a list based on the comma
                        n_line = n_line.split(",")
                        
                        # save data to lists, and continue
                        nodeList.append(n_line[0])
                        coordList.append(n_line[1:])
                        continue
                        
                    # capture elements data
                    elif elements:
                        # remove whitespace from line
                        e_line = line.replace(" ","")
                        # split line into a list based on the comma
                        e_line = e_line.split(",")
                        
                        # save data to list and continue
                        elemList.append(e_line[0])
                        connList.append(e_line[1:])
                        continue
        
        # the elements and nodes have been saved to lists AS STRING OBJECTS...
        # convert to numpy arrays for efficient storage and explicitly defined type
        
        # determine the required array sizes...
        nnod = len(nodeList)           # number of nodes
        ndim = len(coordList[0])       # number of dimensions
        nele = len(elemList)           # number of elements
        nnodPerElem = len(connList[0]) # number of nodes per element
        
        # preallocate arrays:
        Nodes       = numpy.zeros((nnod,1), dtype=numpy.int_)
        Elements    = numpy.zeros((nele,1), dtype=numpy.int_)
        NodesCoords = numpy.zeros((nnod,ndim), dtype=numpy.float64)
        ElemConnect = numpy.zeros((nele,nnodPerElem), dtype=numpy.int_)
        
        # assign nodes:
        for i in range(0,nnod):
            Nodes[i] = numpy.int_(nodeList[i])

        # assign nodal coords:
        for i in range(0,nnod):
            NodesCoords[i,:] = numpy.float64(coordList[i])
        
        # assign elements:
        for i in range(0,nele):
            Elements[i] = numpy.int_(elemList[i])

        # assign element connectivity:
        for i in range(0,nele):
            ElemConnect[i,:] = numpy.int_(connList[i])
            
        # clean up memory:
        del nodeList
        del coordList
        del elemList
        
        # save to object attributes:
        self._Nodes       = Nodes
        self._NodesCoords = NodesCoords
        self._Elements    = Elements
        self._ElemConnect = ElemConnect
        self._ElemType    = ElemType
        return

        
    def saveCSV(self, saveDir=None):
        """ saves CSV files to the requested directory """
        #
        # determine save directory
        #
        if saveDir is None:
            # define default if otherwise undefined
            saveDir = os.path.dirname(self.inpFileName)
            if saveDir is "":
                saveDir = os.getcwd()
            saveDir += '\\'
        elif saveDir[-2:] != '\\':
            saveDir += '\\'
        
        #
        # open files for writing
        #
        
        # name of input file, excl. extension
        inpName = os.path.basename(self.inpPath)
        inpName = os.path.splitext(inpName)[0]
        
        # create file handles
        dummy = saveDir + inpName + '_' + self.partName + '_nodesCoords.csv'
        nodeFile = open(dummy,'w')
        
        dummy = saveDir + inpName + '_' + self.partName + '_elemConnect.csv'
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