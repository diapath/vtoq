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

def reduce_polygon(polygon, angle_th=0, distance_th=0):
    # code lifted from StackOverflow: https://stackoverflow.com/a/69026086
    angle_th_rad = np.deg2rad(angle_th)
    points_removed = [0]
    while len(points_removed):
        points_removed = list()
        for i in range(0, len(polygon)-2, 2):
            v01 = polygon[i-1] - polygon[i]
            v12 = polygon[i] - polygon[i+1]
            d01 = np.linalg.norm(v01)
            d12 = np.linalg.norm(v12)
            if d01 < distance_th and d12 < distance_th:
                points_removed.append(i)
                continue
            angle = np.arccos(np.clip(np.sum(v01*v12) / (d01 * d12) if (d01 * d12) else 0, 0, 1))
            if angle < angle_th_rad:
                points_removed.append(i)

        polygon = np.delete(polygon, points_removed, axis=0)
    return polygon

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

def do_convert(fn_mld, fn_image, fn_json=None, classes=None, overwrite=True, debug=False, scale_factor=None, offset=None, angle_th=5, distance_th=0.01):
    #The default with overwrite=True is to create a new feature collection
    fc = {
      "type": "FeatureCollection",
      "features": []
    }
    
    if fn_json is None:
        fn_json = fn_image.strip()+'.geojson'    

    # Do we need to generate a new JSON file or do we have one we need to use?
    if os.path.exists(fn_json) and not overwrite:
        with open(fn_json) as fp:
            fc = json.load(fp)

    # Here we read the MLD file with the path provided
    mld = ReadMLD.ReadMLDFile(fn_mld, debug=debug)

    # Only get scale_factor and offset if they weren't provided as arguments already
    if scale_factor is None or offset is None:
        scale_factor, offset = get_scale_offset(fn_image, debug=debug)

    # The ignore class will be applied to ay holes defined in the MLD file
    ignore_class = Classification("Ignore", 0xb4b4b4)

    for obj in mld['ROI']:
        if obj['shape'] in [ReadMLD.POLYGON, ReadMLD.ELLIPSE, ReadMLD.CIRCLE, ReadMLD.RECTANGLE, ReadMLD.SQUARE]:
            arr = np.array((obj['x_pts'], obj['y_pts']),dtype=float).T

            # Here we can simplify the outline
            if distance_th > 0:
                arr = reduce_polygon(arr, angle_th=angle_th, distance_th=distance_th)

            # Here we apply scale_factor and offset
            arr = (arr*scale_factor+offset).astype(int)

            #We need at least 3 points for a valid polygon
            if arr.shape[0] < 3:
                continue

            if debug: print(f"Will import: ObjShape={obj['shape']}, Objtype={obj['type']}, arr.shape={arr.shape}")
            if obj['x_pts'][0] < -1e38:
                #Background, ignore
                continue

            if obj['type'] == 0:
                # Consider all holes are potentially disconnected. We'll save them as "ignored" for now.
                name = 'Hole'
                annotation_class=ignore_class
            else:
                name = None
                #Create a new feature (a CLEAR object type (0) can only be a hole in a previously defined annotation)
                if obj['type'] in classes.keys():
                    #We have a class associated with the ROI index
                    annotation_class = classes[obj['type']]
                else:
                    #The ROI index does not have a class associated with
                    annotation_class = None
                    
            # Here we create a new feature and add it to the collection
            f = Feature(classification=annotation_class, name=name)
            f.add_polygon(arr.tolist())
            fc['features'].append(f)

    with open(fn_json, "w") as fp:
        json.dump(fc,fp) #,indent=4)

    return mld
