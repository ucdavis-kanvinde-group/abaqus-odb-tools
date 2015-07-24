"""
Vincente Pericoli
4 May 2015
UC Davis

function to parse ABAQUS input files to obtain
nodes, coordinates, and element connectivity for
all parts in assembly
"""

#
# import modules
#
import re
import os
from myFileOperations import *

#
# define ABAQUS inp parsing function
#
def inp_ParseNodeElem(input_file):
    #open file for reading
    f = open(input_file,'r')
    line = f.readline()
    
    #prepare save directory
    input_name = os.path.splitext(input_file)[0]
    saveDir = os.getcwd() + '\\' + input_name
    if not os.path.exists(saveDir):
        os.makedirs(saveDir)

    while True:

        #search for the next part
        while line.find('*Part') == -1:
            line = f.readline()
            #terminate if end of assembly is reached
            if '*End Assembly' in line:
                f.close()
                return

        #set part name, as defined by user
        if '*Part' in line:
            len_line = len(line)
            name_index = line.find('=') + 1;
            part_name = line[name_index:len_line]
            #must ensure no illegal or newline characters
            part_name = part_name.rstrip()
            part_name = safe_filename(part_name)
            #define node output file accordingly
            n_file_name = 'Nodes_' + part_name + '.csv'
            n_file = saveDir + '\\' + n_file_name
            #delete pre-existing file if one exists
            check_delete(n_file)
            #save new file
            n_file = open(n_file,'w')


        #skip any lines with star fields
        while line[0] == '*':
            line = f.readline()

        #capture lines with no star fields (these are the nodes)
        while line[0] != '*':
            n_file.write( line )
            line = f.readline()

        #now, similarly output the elements
        if '*Element' in line:
            len_line = len(line)
            type_index = line.find('=') + 1;
            elem_type = line[type_index:len_line]
            #must ensure no illegal or newline characters
            elem_type = elem_type.rstrip()
            elem_type = safe_filename(elem_type)
            #define element output file accordingly
            e_file_name = 'Elements_' + part_name + \
                          '_' + elem_type + '.csv'
            e_file = saveDir + '\\' + e_file_name
            #delete pre-existing file if one exists
            check_delete(e_file)
            #save new file
            e_file = open(e_file,'w')

        #skip any lines with star fields
        while line[0] == '*':
            line = f.readline()

        #capture lines with no star fields (these are the elements)
        while line[0] != '*':
            e_file.write( line )
            line = f.readline()

        #all nodes and elements for this part have been captured
        #close files.
        n_file.close()
        e_file.close()
