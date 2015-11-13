# abaqus-odb-tools

Tools for obtaining output from Abaqus output databases (ODB files).

These classes can be used to obtain the values of various field/history output quantities for a defined assembly-level node or element set. Keep in mind that if you define a geometry set in ABAQUS/CAE, it will automatically create a node and element set with the same name.

Verified to work with CAE 6.14

#### HOW TO USE:
See the example.py, and read the doc strings for more info...

When I have time, I will try to write a more comprehensive readme.

#### TYPES OF THINGS YOU CAN DO:
* For some defined node set, obtain the unique value for a nodal field quantity (e.g. displacement) at each node
* For some defined node set, obtain an averaged value for an integration point (IP) field quantity (e.g. MISES) at each node
* For some defined element set, obtain the unique value for an IP field quantity (e.g. MISES) at each IP
* For some defined element set, obtain an averaged value for an IP field quantity (e.g. MISES) for each element
* plus other cool stuff

#### LIMITATIONS:
Please be advised that the functions which employ an averaging scheme (e.g. to obtain the nodal values of an IP variable) will INDISCRIMINANTLY average values... you will NOT be warned if the values are vastly different in magnitude (e.g. when there is volumetric locking). However, the code can be easily edited to incorporate such a feature if it is desired. Generally, it is advisable to visually observe the quality of your results by using the ABAQUS ODB viewer with quilt plots.

Furthermore, the code will only work if the requested set only includes ONE instance from the assembly. This is because ABAQUS numbers the nodes and elements locally to the part (or instance), and not globally. However, this code can be presumably updated to account for this, if you prepend the node labels with the instance string. Likely you will not want to have the averaging scheme to work accross instances (i.e. between TIE constraints), which will complicate matters.