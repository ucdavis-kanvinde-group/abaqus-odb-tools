"""
Vincente Pericoli
UC Davis
10/08/15

Example file, to show you how to use the abaqus-odb-tools classes
"""

# first we must import the tools we want to use
from odbFieldVariableClasses import *

# the above only works if your files are in the same folder as the tools.
# alternatively, you can keep the abaqus-odb-tools files in a different folder.
# in that case, you would import it like this:
import sys
sys.path.append("C:\\path\\to\\abaqus-odb-tools")
from odbFieldVariableClasses import *


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# for example, say I want to obtain the (average) nodal MISES
# for nodes in a defined assembly node set:

odbFile  = 'C:\\Folder\\example.odb' #or just 'example.odb' if in same folder
setName  = 'example_assembly_set'    #defined in abaqus CAE
dataName = 'MISES'

mises = IntPtVariable(odbFile, dataName, setName)
mises.fetchNodalAverage()
#now the attributes are populated. you can access them directly, like:
print mises.nodeLabels
print mises.resultData
#or, you can save them to a CSV file:
mises.saveCSV()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# instead, say I want to obtain the (average) element PEEQ

odbFile  = 'C:\\Folder\\example.odb' #or just 'example.odb' if in same folder
setName  = 'example_assembly_set'    #defined in abaqus CAE
dataName = 'PEEQ'

peeq = IntPtVariable(odbFile, dataName, setName)
peeq.fetchElementAverage()
#now the attributes are populated. you can access them directly, like:
print peeq.elementLabels
print peeq.resultData
#or, you can save them to a CSV file:
peeq.saveCSV()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# some things to keep in mind:
#   * If you define your set using the geometry option in CAE,
#     Abaqus will automatically create associated node and element sets
#   * Integration point variables must be averages at nodal locations,
#     because they are discontinuous accross the elements (i.e. at nodes).
#     This means you will likely run into problems if your set contains a
#     composite material, or has *TIE constraints. Furthermore, to obtain
#     the values at the nodal locations, Abaqus extrapolates using basis
#     functions.
#   * nodal variables work similarly, but their method is called
#     fetchNodalOutput(), because they are not discontinuous...
#     (no average needed)
#   * this example file is just a start! read the doc strings of the classes
#     for more detailed information.
