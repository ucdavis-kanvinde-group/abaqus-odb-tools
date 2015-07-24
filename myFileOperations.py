"""
Vincente Pericoli
14 July 2015
UC Davis

Set of common file operations

Requires the send2trash module
(see https://pypi.python.org/pypi/Send2Trash)
"""

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import re
import sys
sys.path.append("C:\\Python27\\Lib\\site-packages")
from send2trash import send2trash

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def check_delete(name):
    """ deletes old file, if it exists """
    try:
        send2trash(name)
        print "\nold file sent to recycle bin"
        print "saving new \"%s\"\n" % (name)
    except:
        print "\nno file found, saving new file \"%s\"\n" % (name)


def safe_filename(name):
    """
    function to strip illegal characters out of filenames
    dependencies: re
    """
    safe_name = re.sub('[<>:"/\|?*]', '', name)
    return safe_name
