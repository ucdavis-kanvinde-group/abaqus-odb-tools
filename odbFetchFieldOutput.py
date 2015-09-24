"""
Vincente Pericoli
9 July 2015 (Major Update: 17 Sept 2015)
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
from odbFieldVariableClasses import *

#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Define Functions



def getNodalPEEQ(odbName, nodeSetName, verbose=True):
    """ Returns a CSV of the nodal averaged PEEQ """
    
    dataName = 'PEEQ'
    nodalPEEQ = IntPtVariable(odbName, dataName, nodeSetName)
    nodalPEEQ.fetchNodalOutput()
    nodalPEEQ.saveCSV(verbose)
    return

def getNodalMises(odbName, nodeSetName, verbose=True):
    """ returns a CSV of the nodal averaged Mises """
    
    dataName = 'MISES'
    nodalMISES = IntPtVariable(odbName, dataName, nodeSetName)
    nodalMISES.fetchNodalOutput()
    nodalMISES.saveCSV(verbose)
    return

def getNodalPressure(odbName, nodeSetName, verbose=True):
    """ returns a CSV of the nodal averaged pressure """
    
    dataName =  'PRESS'
    nodalPRESS = IntPtVariable(odbName, dataName, nodeSetName)
    nodalPRESS.fetchNodalOutput()
    nodalPRESS.saveCSV(verbose)
    return
    
def getNodalInv3(odbName, nodeSetName, verbose=True):
    """ returns a CSV of the nodal averaged third invariant """
    
    dataName = 'INV3'
    nodalINV3 = IntPtVariable(odbName, dataName, nodeSetName)
    nodalINV3.fetchNodalOutput()
    nodalINV3.saveCSV(verbose)
    return

def getNodalCoords(odbName, nodeSetName, verbose=True):
    """
    returns several CSVs of the nodal coordinates
    (one CSV file per direction)
    """
    dataName = 'COORD'
    nodalCoord = NodalVariable(odbName, dataName, nodeSetName)
    nodalCoord.fetchNodalOutput()
    nodalCoord.saveCSV(verbose)
    return

def getNodalDispl(odbName, nodeSetName, verbose=True):
    """
    returns several CSVs of the nodal coordinates
    (one CSV file per direction)
    """
    dataName = 'U'
    nodalDispl = NodalVariable(odbName, dataName, nodeSetName)
    nodalDispl.fetchNodalOutput()
    nodalDispl.saveCSV(verbose)
    return

def getNodalReaction(odbName, nodeSetName, verbose=True):
    """
    returns several CSVs of the nodal reactions
    (one CSV file per direction)
    """
    dataName = 'RF'
    nodalRF = NodalVariable(odbName, dataName, nodeSetName)
    nodalRF.fetchNodalOutput()
    nodalRF.saveCSV(verbose)
    return


def getNodalReactionSum(odbName, nodeSetName, verbose=True):
    """
    returns several CSVs of the summed nodal reactions
    (one CSV file per direction)
    """
    dataName = 'RF'
    summedRF = NodalVariable(odbName, dataName, nodeSetName)
    summedRF.fetchNodalOutput()
    summedRF.sumNodalData()
    summedRF.saveCSV(verbose)
    return
    
    
