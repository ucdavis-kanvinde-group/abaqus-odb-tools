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
from myFileOperations import *
from odbHistoryVariableClasses import *

#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 
def getJintegral(odbName, stepName, crackName):
    """ 
    Returns a CSV of the J contour integrals 
    for the desired step 
    """
    
    crack = CrackVariable(odbName, stepName, crackName)
    crack.getJintegral()
    crack.saveCSV()
    return
            
    
