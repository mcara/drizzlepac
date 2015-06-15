""" pixtosky - A module to perform coordinate transformation from pixel to sky coordinates.

    :Authors: Warren Hack

    :License: `<http://www.stsci.edu/resources/software_hardware/pyraf/LICENSE>`_

    PARAMETERS
    ----------
    input : str
        full filename with path of input image, an extension name ['sci',1] should be
        provided if input is a multi-extension FITS file

    Optional Parameters
    -------------------
    x : float, optional
        X position from input image
    y : float, optional
        Y position from input image
    coords : str, optional
        full filename with path of file with x,y coordinates
    colnames : str, optional
        comma separated list of column names from 'coords' files
        containing x,y coordinates, respectively. Will default to
        first two columns if None are specified. Column names for ASCII
        files will use 'c1','c2',... convention.
    separator : str, optional
        non-blank separator used as the column delimiter in the coords file
    hms : bool, optional
        Produce output in HH:MM:SS.S format instead of decimal degrees? (default: False)
    precision : int, optional
        Number of floating-point digits in output values
    output : str, optional
        Name of output file with results, if desired
    verbose : bool
        Print out full list of transformation results (default: False)

    RETURNS
    -------
    ra : float
        Right Ascension of pixel. If more than 1 input value, then it will be a
        numpy array.
    dec : float
        Declination of pixel. If more than 1 input value, then it will be a
        numpy array.

    NOTES
    -----
    This module performs a full distortion-corrected coordinate transformation
    based on all WCS keywords and any recognized distortion keywords from the
    input image header.

    See Also
    --------
    `stwcs`

    EXAMPLES
    --------
    1. The following command will transform the position 256,256 into a
       position on the sky for the image 'input_flt.fits[sci,1]' using::

       >>> from drizzlepac import pixtosky
       >>> r,d = pixtosky.xy2rd("input_file_flt.fits[sci,1]", 256,256)


    2. The set of X,Y positions from 'input_flt.fits[sci,1]' stored as
       the 3rd and 4th columns from the ASCII file 'xy_sci1.dat'
       will be transformed and written out to 'radec_sci1.dat' using::

       >>> from drizzlepac import pixtosky
       >>> r,d = pixtosky.xy2rd("input_flt.fits[sci,1]", coords='xy_sci1.dat',
       ...                      colnames=['c3','c4'], output="radec_sci1.dat")

"""
from __future__ import absolute_import, division, print_function # confidence medium

import os,copy
import numpy as np

from stsci.tools import fileutil, teal
from . import util
from . import wcs_functions
import stwcs
from stwcs import distortion, wcsutil

# This is specifically NOT intended to match the package-wide version information.
__version__ = '0.1'
__vdate__ = '20-Jan-2011'

__taskname__ = 'pixtosky'

blank_list = [None, '', ' ']

def xy2rd(input,x=None,y=None,coords=None,colnames=None,separator=None,
            hms=True, precision=6,output=None,verbose=True):
    """ Primary interface to perform coordinate transformations from
        pixel to sky coordinates using STWCS and full distortion models
        read from the input image header.
    """
    if coords is not None:
        if colnames in blank_list:
            colnames = ['c1','c2']
        # Determine columns which contain pixel positions
        cols = util.parse_colnames(colnames,coords)
        # read in columns from input coordinates file
        xyvals = np.loadtxt(coords,usecols=cols,delimiter=separator)
        if xyvals.ndim == 1:  # only 1 entry in coords
            xlist = [xyvals[0].copy()]
            ylist = [xyvals[1].copy()]
        else:
            xlist = xyvals[:,0].copy()
            ylist = xyvals[:,1].copy()
        del xyvals
    else:
        if not isinstance(x,list):
            xlist = [x]
            ylist = [y]
        else:
            xlist = x
            ylist = y

    # start by reading in WCS+distortion info for input image
    inwcs = wcsutil.HSTWCS(input)

    # Now, convert pixel coordinates into sky coordinates
    dra,ddec = inwcs.all_pix2world(xlist,ylist,1)

    # convert to HH:MM:SS.S format, if specified
    if hms:
        ra,dec = wcs_functions.ddtohms(dra,ddec,precision=precision)
        rastr = ra
        decstr = dec
    else:
        # add formatting based on precision here...
        rastr = []
        decstr = []
        fmt = "%."+repr(precision)+"f"
        for r,d in zip(dra,ddec):
            rastr.append(fmt%r)
            decstr.append(fmt%d)

        ra = dra
        dec = ddec

    if verbose or (not verbose and util.is_blank(output)):
        print('# Coordinate transformations for ',input)
        print('# X      Y         RA             Dec\n')
        for x,y,r,d in zip(xlist,ylist,rastr,decstr):
            print("%.4f  %.4f    %s  %s"%(x,y,r,d))

    # Create output file, if specified
    if output:
        f = open(output,mode='w')
        f.write("# Coordinates converted from %s\n"%input)
        for r,d in zip(rastr,decstr):
            f.write('%s    %s\n'%(r,d))
        f.close()
        print('Wrote out results to: ',output)

    return ra,dec

#--------------------------
# TEAL Interface functions
#--------------------------
def run(configObj):

    coords = util.check_blank(configObj['coords'])
    colnames = util.check_blank(configObj['colnames'])
    sep = util.check_blank(configObj['separator'])
    outfile = util.check_blank(configObj['output'])

    xy2rd(configObj['input'],
            x = configObj['x'], y = configObj['y'],
            coords = coords, colnames = colnames,
            separator= sep, hms = configObj['hms'], precision= configObj['precision'],
            output= outfile, verbose = configObj['verbose'])


def help(file=None):
    """
    Print out syntax help for running astrodrizzle

    Parameters
    ----------
    file : str (Default = None)
        If given, write out help to the filename specified by this parameter
        Any previously existing file with this name will be deleted before
        writing out the help.

    """
    helpstr = getHelpAsString(docstring=True, show_ver = True)
    if file is None:
        print(helpstr)
    else:
        if os.path.exists(file): os.remove(file)
        f = open(file, mode = 'w')
        f.write(helpstr)
        f.close()


def getHelpAsString(docstring = False, show_ver = True):
    """
    return useful help from a file in the script directory called
    __taskname__.help

    """
    install_dir = os.path.dirname(__file__)
    taskname = util.base_taskname(__taskname__, '')
    htmlfile = os.path.join(install_dir, 'htmlhelp', taskname + '.html')
    helpfile = os.path.join(install_dir, taskname + '.help')

    if docstring or (not docstring and not os.path.exists(htmlfile)):
        if show_ver:
            helpString = os.linesep + \
                ' '.join([__taskname__, 'Version', __version__,
                ' updated on ', __vdate__]) + 2*os.linesep
        else:
            helpString = ''
        if os.path.exists(helpfile):
            helpString += teal.getHelpFileAsString(taskname, __file__)
        else:
            if __doc__ is not None:
                helpString += __doc__ + os.linesep
    else:
        helpString = 'file://' + htmlfile

    return helpString


__doc__ = getHelpAsString(docstring = True, show_ver = False)
