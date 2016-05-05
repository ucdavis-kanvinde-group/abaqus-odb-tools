"""
Vincente Pericoli
14 July 2015
UC Davis

Set of common (Windows) file operations
"""

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import re
import os


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def check_delete(name, verbose=True):
    """ 
    deletes old file, if it exists 
    input: 
        name    = file name, with extension (must be in current working dir)
        verbose = optional input (default=True) which will print messages
                  to the command window
    """
    if verbose:
        try:
            os.remove(name)
            print "\nold file deleted"
            print "saving new \"%s\"\n" % (name)
        except:
            print "\nno file found \"%s\"\n" % (name)
    else:
        try:
            os.remove(name)
        except:
            pass

def check_recycle(name, verbose=True):
    """ 
    places old file in recycle bin, if it exists.
    this should work for any system, but requires the send2trash module
    (see https://pypi.python.org/pypi/Send2Trash)
    
    input: 
        name    = file name, with extension (must be in current working dir)
        verbose = optional input (default=True) which will print messages
                  to the command window
    """
    # import send2trash module:
    # it's bad practice to import within a function, but the use of
    # check_recycle is optional, since check_delete exists. Thus, I don't
    # want the import of myFileOperations to break simply because someone
    # does not have the optional send2trash module installed...
    from send2trash import send2trash
    
    if verbose:
        try:
            send2trash(name)
            print "\nold file sent to recycle bin"
            print "saving new \"%s\"\n" % (name)
        except:
            print "\nno file found, saving new file \"%s\"\n" % (name)
    else:
        try:
            send2trash(name)
        except:
            pass

def safe_filename(name):
    """
    function to strip illegal characters out of filenames
    dependencies: re
    """
    safe_name = re.sub('[<>:"/\|?*]', '', name)
    return safe_name
