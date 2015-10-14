# abaqus-odb-tools

Tools for obtaining output from Abaqus output databases (ODB files).

These classes can be used to obtain the values of various field/history output quantities for a defined assembly-level node or element set. Keep in mind that if you define a geometry set in ABAQUS/CAE, it will automatically create a node and element set with the same name.

Verified to work with CAE 6.14

#### HOW TO USE:
See the example.py, and read the doc strings for more info...

When I have time, I will try to write a more comprehensive readme.

#### LIMITATIONS:
Please be advised that the functions employ an averaging scheme to obtain the nodal values of integration point (IP) variables. Since IP variables are discontinuous between elements, the nodal value is assumed to be an average of all connecting elements. The functions will INDISCRIMINANTLY average values... you will NOT be warned if the values are vastly different in magnitude (e.g. when there is volumetric locking). However, the code can be easily edited to incorporate such a feature if it is desired. Generally, it is advisable to visually observe the quality of your results by using the ABAQUS ODB viewer with quilt plots.

Furthermore, the code will only work if the requested set only includes ONE instance from the assembly. This is because ABAQUS numbers the nodes and elements locally to the part (or instance), and not globally. However, this code can be presumably updated to account for this, if you prepend the node labels with the instance string. Likely you will not want to have the averaging scheme to work accross instances (i.e. between TIE constraints), which will complicate matters.

Similarly, you can request output of IP variables for the element as a whole, rather than at nodal locations. This ALSO employs an averaging scheme, to obtain a single value for each element.