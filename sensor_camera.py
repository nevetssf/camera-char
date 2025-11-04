#standard modules
import os

#common 3rd party
import numpy as np
import plotly.express as px
import pandas as pd

#raw-specific modules
import exiftool
import rawpy

class Sensor(object):
    def __init__(self):
        pass
    
    def scan(self, path='.', suffix='DNG'):
        """Scan a directory for all raw files and create a data table summarizing the noise.
        """

        fn_list = sorted([i for i in os.listdir(path) if i.upper().endswith(suffix)])

        with exiftool.ExifToolHelper() as et:
            #metadata = et.get_metadata(fn_list)

            data = pd.DataFrame()

            i_total = len(fn_list)
            for i, fn in enumerate(fn_list):
                print('%d/%d %s' % (i, i_total, fn))
                      
                fn_abs = os.path.join(path, fn)
                #print('Scanning %s' % fn_abs)
                with exiftool.ExifToolHelper() as et:
                    metadata = et.get_metadata(fn_abs)[0]
                raw = rawpy.imread(fn_abs)
                
                #handle black level as string of levels per channel - happens in Leica Q
                black_level = metadata.get('EXIF:BlackLevel')
                if black_level is None:
                    black_level = metadata.get('MakerNotes:BlackLevel')
                if isinstance(black_level, str):
                    black_level = int(black_level.split()[0])
                elif black_level is None:
                    black_level = raw.black_level_per_channel[0]
                    
                #handle white level as string of levels per channel - happens in Leica Q
                white_level = metadata.get('EXIF:WhiteLevel')
                if white_level is None:
                    #assume the white level is the bit depth
                    bits = metadata.get('EXIF:BitsPerSample')
                    if bits is not None:
                        white_level = 2**bits
                if isinstance(white_level, str):
                    white_level = int(white_level.split()[0])
                    
                image = raw.raw_image
                   
                camera = metadata.get('EXIF:UniqueCameraModel')
                if camera is None:
                    camera = metadata.get('EXIF:Model')
                if camera == "LEICA Q (Typ 116)":
                    #handle artifacts on right side of Q sensor
                    image = image[:, 0:6011]
                elif camera == "RICOH GR III":
                    image = image[28:4052, 56:6088]
                elif camera == "LEICA CL":
                    image = image[:, 0:6048]
                elif camera == "LEICA Q3":
                    image = image[:, 0:7412]
                elif camera == "LEICA SL2-S":
                    #print('using crop for sl2-s')
                    #image = image[:, 0:6030]
                    #image = image[:, 0:6024]
                    image = image[0:4000, 0:6000]
                    #image = image[1000:1500, 1000:1500]

                width = metadata.get('EXIF:ExifImageWidth')
                if width is None:
                    width = metadata.get('EXIF:ImageWidth')
                height = metadata.get('EXIF:ExifImageHeight')
                if height is None:
                    height = metadata.get('EXIF:ImageHeight')
                
                df = pd.DataFrame({
                    'camera':[camera],
                    'source':[metadata.get('SourceFile')],
                    'black_level':[black_level],
                    'white_level':[white_level],
                    'width':width,
                    'height':height,
                    #'white':[raw.white_level],
                    'iso':[metadata.get('EXIF:ISO')],
                    'time':[metadata.get('EXIF:ExposureTime')],
                    'std':[np.std(image)],
                    'mean':[np.mean(image)],
                    'min':[np.min(image)],
                    'max':[np.max(image)],
                })
                data = pd.concat([data, df])
                raw.close()
            self.data = data
            #exposure value - (max digital range)/(std dev)
            data['EV'] = data.apply(lambda x: np.log((x['white_level']-x['black_level'])/x['std'])/np.log(2), axis='columns')
            
        return(data)