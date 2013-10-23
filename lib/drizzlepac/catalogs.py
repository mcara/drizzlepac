import os
import numpy as np
import pywcs
import astrolib.coords as coords
from stsci.tools import logutil, textutil

import stwcs
from stwcs import wcsutil
import pyfits
import stsci.imagestats as imagestats

#import idlphot
import tweakutils,util

COLNAME_PARS = ['xcol','ycol','fluxcol']
CATALOG_ARGS = ['sharpcol','roundcol','hmin','fwhm','maxflux','minflux','fluxunits','nbright']+COLNAME_PARS

REFCOL_PARS = ['refxcol','refycol','rfluxcol']
REFCAT_ARGS = ['rmaxflux','rminflux','rfluxunits','refnbright']+REFCOL_PARS

log = logutil.create_logger(__name__)

def generateCatalog(wcs,mode='automatic',catalog=None,**kwargs):
    """ Function which determines what type of catalog object needs to be
        instantiated based on what type of source selection algorithm the user
        specified.

        Parameters
        ----------
        wcs : obj
            WCS object generated by STWCS or PyWCS
        catalog : str or ndarray
            Filename of existing catalog or ndarray of image for generation of source catalog
        kwargs : dict
            Parameters needed to interpret source catalog from input catalog
            with `findmode` being required.

        Returns
        -------
        catalog : obj
            A Catalog-based class instance for keeping track of WCS and
            associated source catalog
    """
    if not isinstance(catalog,Catalog):
        if mode == 'automatic': # if an array is provided as the source
            # Create a new catalog directly from the image
            catalog = ImageCatalog(wcs,catalog,**kwargs)
        else: # a catalog file was provided as the catalog source
            catalog = UserCatalog(wcs,catalog,**kwargs)
    return catalog

class Catalog(object):
    """ Base class for keeping track of a source catalog for an input WCS

        .. warning:: This class should never be instantiated by itself,
                     as necessary methods are not defined yet.
    """
    def __init__(self,wcs,catalog_source,**kwargs):
        """
        This class requires the input of a WCS and a source for the catalog,
        along with any arguments necessary for interpreting the catalog.


        Parameters
        ----------
        wcs : obj
            Input WCS object generated using STWCS or HSTWCS
        catalog_source : str or ndarray
            Catalog generated from this image(ndarray) or read from this file(str)
        kwargs : dict
            Parameters for interpreting the catalog file or for performing the source
            extraction from the image. These will be set differently depending on
            the type of catalog being instantiated.
        """
        self.wcs = wcs # could be None in case of user-supplied catalog
        self.xypos = None
        self.in_units = 'pixels'
        self.sharp = None
        self.round = None
        self.numcols = None
        self.origin = 1 # X,Y coords will ALWAYS be FITS 1-based, not numpy 0-based
        self.pars = kwargs


        self.start_id = 0
        if 'start_id' in self.pars:
            self.start_id = self.pars['start_id']

        self.fname = catalog_source
        self.source = catalog_source
        self.catname = None

        self.num_objects = None

        self.radec = None # catalog of sky positions for all sources on this chip/image
        self.set_colnames()

    def generateXY(self):
        """ Method to generate source catalog in XY positions
            Implemented by each subclass
        """
        pass

    def set_colnames(self):
        """ Method to define how to interpret a catalog file
            Only needed when provided a source catalog as input
        """
        pass

    def _readCatalog(self):
        pass

    def generateRaDec(self):
        """ Convert XY positions into sky coordinates using STWCS methods
        """
        if not isinstance(self.wcs,pywcs.WCS):
            print >> sys.stderr,textutil.textbox(
            'WCS not a valid PyWCS object. Conversion of RA/Dec not possible...')
            raise ValueError
        if len(self.xypos[0]) == 0:
            self.xypos = None
        if self.xypos is None:
            warnstr = textutil.textbox('WARNING: \n'+
                        'No objects found for this image...')
            for line in warnstr.split('\n'):
                log.warning(line)
            print(warnstr)
            return

        if self.radec is None or force:
            if self.wcs is not None:
                print('    Number of objects in catalog: %d'%(len(self.xypos[0])))
                self.radec = self.wcs.all_pix2sky(self.xypos[0],self.xypos[1],self.origin)
            else:
                # If we have no WCS, simply pass along the XY input positions
                # under the assumption they were already sky positions.
                self.radec = self.xypos

    def apply_exclusions(self,exclusions):
        """ Trim sky catalog to remove any sources within regions specified by
            exclusions file
        """
        # parse exclusion file into list of positions and distances
        exclusion_coords = tweakutils.parse_exclusions(exclusions)
        if exclusion_coords is None:
            return

        excluded_list = []
        radec_indx = range(len(self.radec[0]))
        for ra,dec,indx in zip(self.radec[0],self.radec[1],radec_indx):
            src_pos = coords.Position((ra,dec))
            # check to see whether this source is within an exclusion region
            for reg in exclusion_coords:
                if reg['units'] == 'sky':
                    regpos = reg['pos']
                    regdist = reg['distance']
                else:
                    regradec = self.wcs.all_pix2sky([reg['pos']],1)[0]
                    regpos = (regradec[0],regradec[1])
                    regdist = reg['distance']*self.wcs.pscale

                epos = coords.Position(regpos)
                if src_pos.within(epos,regdist):
                    excluded_list.append(indx)
                    break
        # create a list of all 'good' sources outside all exclusion regions
        for e in excluded_list: radec_indx.remove(e)
        radec_indx = np.array(radec_indx,dtype=np.int64)
        num_excluded = len(excluded_list)
        if num_excluded > 0:
            radec_trimmed = []
            xypos_trimmed = []
            for arr in self.radec:
                radec_trimmed.append(arr[radec_indx])
            for arr in self.xypos:
                xypos_trimmed.append(arr[radec_indx])
            xypos_trimmed[-1] = np.arange(len(xypos_trimmed[0]))
            self.radec = radec_trimmed
            self.xypos = xypos_trimmed
            log.info('Excluded %d sources from catalog.'%num_excluded)

    def buildCatalogs(self,exclusions=None):
        """ Primary interface to build catalogs based on user inputs.
        """
        self.generateXY()
        self.generateRaDec()
        if exclusions:
            self.apply_exclusions(exclusions)

    def plotXYCatalog(self,**kwargs):
        """
        Method which displays the original image and overlays the positions
        of the detected sources from this image's catalog.

        Plotting `kwargs` that can be provided are::

            vmin, vmax, cmap, marker

        Default colormap is `summer`.

        """
        try:
            from matplotlib import pyplot as pl
        except:
            pl = None

        if pl is not None: # If the pyplot package could be loaded...
            pl.clf()
            pars = kwargs.copy()

            if 'marker' not in pars:
                pars['marker'] = 'b+'

            if 'cmap' in pars:
                pl_cmap = pars['cmap']
                del pars['cmap']
            else:
                pl_cmap = 'summer'
            pl_vmin = None
            pl_vmax = None
            if 'vmin' in pars:
                pl_vmin = pars['vmin']
                del pars['vmin']
            if 'vmax' in pars:
                pl_vmax = pars['vmax']
                del pars['vmax']

            pl.imshow(self.source,cmap=pl_cmap,vmin=pl_vmin,vmax=pl_vmax)
            pl.plot(self.xypos[0]-1,self.xypos[1]-1,pars['marker'])

    def writeXYCatalog(self,filename):
        """ Write out the X,Y catalog to a file
        """
        if self.xypos is None:
            warnstr = textutil.textbox(
                'WARNING: \n    No X,Y source catalog to write to file. ')
            for line in warnstr.split('\n'):
                log.warning(line)
            print(warnstr)
            return

        f = open(filename,'w')
        f.write("# Source catalog derived for %s\n"%self.wcs.filename)
        f.write("# Columns: \n")
        f.write('#    X      Y         Flux       ID\n')
        f.write('#   (%s)   (%s)\n'%(self.in_units,self.in_units))

        for row in range(len(self.xypos[0])):
            for i in range(len(self.xypos)):
                f.write("%g  "%(self.xypos[i][row]))
            f.write("\n")

        f.close()



class ImageCatalog(Catalog):
    """ Class which generates a source catalog from an image using
        Python-based, daofind-like algorithms

        Required input `kwargs` parameters::

            computesig, skysigma, threshold, peakmin, peakmax,
            hmin, conv_width, [roundlim, sharplim]

    """
    def __init__(self,wcs,catalog_source,**kwargs):
        Catalog.__init__(self,wcs,catalog_source,**kwargs)
        if self.wcs.extname == ('',None): self.wcs.extname = (0)
        self.source = pyfits.getdata(self.wcs.filename,ext=self.wcs.extname)

    def generateXY(self):
        """ Generate source catalog from input image using DAOFIND-style algorithm
        """
        #x,y,flux,sharp,round = idlphot.find(array,self.pars['hmin'],self.pars['fwhm'],
        #                    roundlim=self.pars['roundlim'], sharplim=self.pars['sharplim'])
        print '###Source finding for EXT=',self.wcs.extname,' started at: ',util._ptime()[0]
        if self.pars['computesig']:
            # compute sigma for this image
            sigma = self._compute_sigma()
        else:
            sigma = self.pars['skysigma']
        skymode = sigma**2
        log.info('   Finding sources using sky sigma = %f'%sigma)
        if self.pars['threshold'] in [None,"INDEF",""," "]:
            hmin = skymode
        else:
            hmin = sigma*self.pars['threshold']

        x,y,flux,id = tweakutils.ndfind(self.source,hmin,self.pars['conv_width'],skymode,
                            peakmin=self.pars['peakmin'],
                            peakmax=self.pars['peakmax'],
                            fluxmin=self.pars['fluxmin'],
                            fluxmax=self.pars['fluxmax'],
                            nsigma=self.pars['nsigma'])
        if len(x) == 0:
            if  not self.pars['computesig']:
                sigma = self._compute_sigma()
                hmin = sigma * self.pars['threshold']
                log.info('No sources found with original thresholds. Trying automatic settings.')
                x,y,flux,id = tweakutils.ndfind(source,hmin,self.pars['conv_width'],skymode,
                                        peakmin=self.pars['peakmin'],
                                        peakmax=self.pars['peakmax'],
                                        fluxmin=self.pars['fluxmin'],
                                        fluxmax=self.pars['fluxmax'],
                                        nsigma=self.pars['nsigma'])
            else:
                self.xypos = [[],[],[],[]]
                warnstr = textutil.textbox('WARNING: \n'+
                    'No valid sources found with the current parameter values!')
                for line in warnstr.split('\n'):
                    log.warning(line)
                print(warnstr)
        log.info('###Source finding finished at: %s'%(util._ptime()[0]))
        self.xypos = [x+1,y+1,flux,id+self.start_id] # convert the positions from numpy 0-based to FITS 1-based

        self.in_units = 'pixels' # Not strictly necessary, but documents units when determined
        self.sharp = None # sharp
        self.round = None # round
        self.numcols = 3  # 5
        self.num_objects = len(x)

    def _compute_sigma(self):
        istats = imagestats.ImageStats(self.source,nclip=3,
                                        fields='mode,stddev',binwidth=0.01)
        sigma = np.sqrt(2.0 * np.abs(istats.mode))
        return sigma

class UserCatalog(Catalog):
    """ Class to manage user-supplied catalogs as inputs.

        Required input `kwargs` parameters::

            xyunits, xcol, ycol[, fluxcol, [idcol]]

    """
    COLNAMES = COLNAME_PARS
    IN_UNITS = None

    def set_colnames(self):
        self.colnames = []

        cnum = 1
        for cname in self.COLNAMES:
            if cname in self.pars and not util.is_blank(self.pars[cname]):
                self.colnames.append(self.pars[cname])
            else:
                # Insure that at least x and y columns had default values
                if 'fluxcol' not in cname:
                    self.colnames.append(str(cnum))
                cnum += 1

        # count the number of columns
        self.numcols = len(self.colnames)

        if self.IN_UNITS is not None:
            self.in_units = self.IN_UNITS
        else:
            self.in_units = self.pars['xyunits']

    def _readCatalog(self):
        # define what columns will be read
        # The following loops
        #colnums = [self.pars['xcol']-1,self.pars['ycol']-1,self.pars['fluxcol']-1]

        # read the catalog now, one for each chip/mosaic
        # Currently, this only supports ASCII catalog files
        # Support for FITS tables needs to be added
        catcols = tweakutils.readcols(self.source, cols=self.colnames)
        if not util.is_blank(catcols) and len(catcols[0]) == 0:
            catcols = None
        return catcols

    def generateXY(self):
        """
        Method to interpret input catalog file as columns of positions and fluxes.
        """

        xycols = self._readCatalog()
        if xycols is not None:
            # convert the catalog into attribute
            self.xypos = xycols[:3]
            # convert optional columns if they are present
            if self.numcols > 3:
                self.sharp = xycols[3]
            if self.numcols > 4:
                self.round = xycols[4]

        self.num_objects = 0
        if xycols is not None:
            self.num_objects = len(xycols[0])

        if self.numcols < 3: # account for flux column
            self.xypos.append(np.zeros(self.num_objects))
        # add source ID column
        self.xypos.append(np.arange(self.num_objects)+self.start_id)

    def plotXYCatalog(self,**kwargs):
        """
        Plots the source catalog positions using matplotlib's `pyplot.plot()`

        Plotting `kwargs` that can also be passed include any keywords understood
        by matplotlib's `pyplot.plot()` function such as::

            vmin, vmax, cmap, marker


        """
        try:
            from matplotlib import pyplot as pl
        except:
            pl = None

        if pl is not None:
            pl.clf()
            pl.plot(self.xypos[0],self.xypos[1],**kwargs)


class RefCatalog(UserCatalog):
    """ Class which manages a reference catalog.

    Notes
    -----
    A *reference catalog* is defined as a catalog of undistorted source positions
    given in RA/Dec which would be used as the master list for subsequent
    matching and fitting.

    """
    COLNAMES = REFCOL_PARS
    IN_UNITS = 'degrees'

    def generateXY(self):
        pass
    def generateRaDec(self):
        if isinstance(self.source,list):
            self.radec = self.source
        else:
            self.radec = self._readCatalog()
    def buildXY(self,catalogs):
        if instance(catalogs,dict):
            # we have chip_catalogs from an ImageClass instance
            pass
        else:
            # create X,Y positions based on self.radec and self.wcs
            pass
