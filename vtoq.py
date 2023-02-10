#   Copyright 2023 DIAPath - CMMI Gosselies Belgium (diapath@cmmi.be)
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import numpy as np
import tifffile
import json
import uuid
import os
import ReadMLD

class Feature(dict):
    def __init__(self, name=None, classification=None):
        self['type'] = 'Feature'
        self['id'] = str(uuid.uuid4())
        self['geometry'] = {'type':'Polygon','coordinates':[]}
        self['properties'] = {
            'object_type': 'annotation',
            'isLocked': True
        }
        if name is not None:
            self['properties']['name'] = name
        if classification is not None:
            self['properties']['classification'] = classification
    def add_polygon(self,coordinates):
        if coordinates[0] != coordinates[-1]:
            coordinates.append(coordinates[0])
        self['geometry']['coordinates'].append(coordinates)
    def size(self):
        return len(self['geometry']['coordinates'])

class Classification(dict):
    def __init__(self, name, color=0xc80000):
        self['name'] = name
        self.color = color

    @property
    def color(self):
        return self['colorRGB'] & 0xffffff
       
    # a setter function
    @color.setter
    def color(self, c):
        self['colorRGB'] = -0x1000000 + c

def get_scale_offset(fn_image, debug=False):
    tif = tifffile.TiffFile(fn_image)

    ru = tif.pages[0].tags['ResolutionUnit']
    if not 'CENTIMETER' in str(ru):
        #I'm sure we could be more cleverer about this...
        raise ValueError('ResolutionUnit should be \'CENTIMETER\'!')
    
    x_res = tif.pages[0].tags['XResolution'].value[0]
    px = 1e-2 / x_res #RU is centimeter

    y_res = tif.pages[0].tags['YResolution'].value[0]
    py = 1e-2 / y_res #RU is centimeter

    xcent = tif.pages[0].tags['ImageWidth'].value // 2
    ycent = tif.pages[0].tags['ImageLength'].value // 2

    xoffs = tif.pages[0].ndpi_tags['XOffsetFromSlideCenter'] #Offset value in nm
    yoffs = tif.pages[0].ndpi_tags['YOffsetFromSlideCenter'] #Offset value in nm

    scale_factor = [1./(px*1e3), -1./(py*1e3)] #Scale factor from mm (Visiopharm)
    offset = [xcent-xoffs/(px*1e9),ycent-yoffs/(py*1e9)] #Offset from nm (NDPI)

    if debug:
        print("Pixel size (m):",px, py)
        print("Offset:",xoffs,yoffs)
        print("scale factor", scale_factor)
        print("offset", offset)
        
    tif.close()
    return scale_factor, offset

def do_convert(fn_mld, fn_image, fn_json=None, classes = None, overwrite=True, debug=False):
    if fn_json is None:
        fn_json = fn_image.strip()+'.geojson'    

    #The default with overwrite=True is to create a new feature collection
    fc = {
      "type": "FeatureCollection",
      "features": []
    }
    
    if os.path.exists(fn_json) and not overwrite:
        with open(fn_json) as fp:
            fc = json.load(fp)

    mld = ReadMLD.ReadMLDFile(fn_mld, debug=debug)
    scale_factor, offset = get_scale_offset(fn_image, debug=debug)
    f = None
    for obj in mld['ROI']:
        if obj['shape'] == 0:
            obj_type = obj['type']
            if obj_type > 0 or f is None:
                #Create a new feature (A CLEAR object type (0) can only be a hole in a previously defined annotation)
                if obj_type in classes.keys():
                    #We have a class associated with the ROI index
                    annotation_class = classes[obj_type]
                else:
                    #The ROI index does not have a class associated with
                    annotation_class = None
                    
                f = Feature(classification=annotation_class)
                fc['features'].append(f)
            
            if f is not None:
                #Add the polygon to the current feature (first is annotation, next are holes)
                arr = np.array((obj['x_pts'], obj['y_pts']),dtype=float).T
                arr = (arr*scale_factor+offset).astype(int)
                f.add_polygon(arr.tolist())

    with open(fn_json, "w") as fp:
        json.dump(fc,fp) 
