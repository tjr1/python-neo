# encoding: utf-8
"""
Classe for reading data from WinEdr, a software tool written by
John Dempster.

WinEdr is free:
http://spider.science.strath.ac.uk/sipbs/software.htm

Depend on: 

Supported : Read

Author: sgarcia

"""

from baseio import BaseIO
from ..core import *
import numpy as np
from numpy import dtype, zeros, fromstring, empty
import quantities as pq

import os
import struct


class WinEdrIO(BaseIO):
    """
    Class for reading data from WinEDR.
    
    Usage:
        >>> from neo import io
        >>> r = io.WinEdrIO( filename = 'File_WineEDR_1.EDR')
        >>> seg = r.read_segment(lazy = False, cascade = True,)
        >>> print seg._analogsignals
    
    """
    
    is_readable        = True
    is_writable        = False

    supported_objects  = [ Segment , AnalogSignal ]
    readable_objects   = [Segment]
    writeable_objects  = []  

    has_header         = False
    is_streameable     = False
    
    read_params        = { Segment : [ ], }
    
    write_params       = None
    
    name               = 'WinEDR'
    extensions          = [ 'EDR' ]
    
    mode = 'file'
    
    def __init__(self , filename = None) :
        """
        This class read a WinEDR file.
        
        Arguments:
            filename : the filename 
        
        """
        BaseIO.__init__(self)
        self.filename = filename


    def read(self , **kargs):
        """
        Return a neo.Segment
        See read_segment for detail.
        """
        return self.read_segment( **kargs)
    
    def read_segment(self , lazy = False, cascade = True):
        seg  = Segment(
                                    file_origin = os.path.basename(self.filename),
                                    )
        
        if not cascade:
            return seg

        fid = open(self.filename , 'rb')
        
        headertext = fid.read(2048)
        header = {}
        for line in headertext.split('\r\n'):
            if '=' not in line : continue
            #print '#' , line , '#'
            key,val = line.split('=')
            if key in ['NC', 'NR','NBH','NBA','NBD','ADCMAX','NP','NZ','ADCMAX' ] :
                val = int(val)
            if key in ['AD', 'DT', ] :
                val = val.replace(',','.')
                val = float(val)
            header[key] = val
        
        if not lazy:
            data = np.memmap(self.filename , dtype('i2')  , 'r', 
                  #shape = (header['NC'], header['NP']) ,
                  shape = (header['NP']/header['NC'],header['NC'], ) ,
                  offset = header['NBH'])

        for c in range(header['NC']):
            anaSig = AnalogSignal()
            
            
            YCF = float(header['YCF%d'%c].replace(',','.'))
            YAG = float(header['YAG%d'%c].replace(',','.'))
            YZ = float(header['YZ%d'%c].replace(',','.'))
            
            ADCMAX = header['ADCMAX']
            AD = header['AD']
            DT = header['DT']
            
            if 'TU' in header:
                if header['TU'] == 'ms':
                    DT *= .001
            
            unit = header['YU%d'%c]
            try :
                unit = pq.Quantity(1., unit)
            except:
                unit = pq.Quantity(1., '')
            
            if lazy:
                signal = [ ] * unit
            else:
                signal = (data[:,header['YO%d'%c]].astype('f4')-YZ) *AD/( YCF*YAG*(ADCMAX+1)) * unit
            
            ana = AnalogSignal( signal, 
                                            sampling_rate = pq.Hz/DT,
                                            t_start = 0.*pq.s,
                                            name = header['YN%d'%c],
                                            )
            ana._annotations['channel_index'] = c
            if lazy:
                ana._data_description = { 'shape' : header['NP']/header['NC'] }
            
            seg._analogsignals.append(ana)
            
            
        return seg
        
        
        



AnalysisDescription = [
    ('RecordStatus','8s'),
    ('RecordType','4s'),
    ('GroupNumber','f'),
    ('TimeRecorded','f'),
    ('SamplingInterval','f'),
    ('VMax','8f'),
    ]


class HeaderReader():
    def __init__(self,fid ,description ):
        self.fid = fid
        self.description = description
    def read_f(self, offset =0):
        self.fid.seek(offset)
        d = { }
        for key, format in self.description :
            val = struct.unpack(format , self.fid.read(struct.calcsize(format)))
            if len(val) == 1:
                val = val[0]
            else :
                val = list(val)
            d[key] = val
        return d


