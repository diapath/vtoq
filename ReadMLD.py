#   Copyright 2021 DIAPath - CMMI Gosselies Belgium (diapath@cmmi.be)
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

import struct
from xml.etree import ElementTree as ET
import numpy as np
from PIL import Image
import os

POLYGON = 0
ELLIPSE = 1
CIRCLE = 2
POLYLINE = 3
LINE = 4
RECTANGLE = 5
SQUARE = 6
TEXT = 7

#Converts a struct to a dict or a list
def convert(f,struct_fmt,keys=None,as_list=False):
    struct_len = struct.calcsize(struct_fmt)

    if not type(f) is bytes:
        data = f.read(struct_len)
    else:
        data = f
        if len(data) > struct_len:
            data = data[:struct_len]
                
    if len(data) < struct_len:
        return None

    values = struct.unpack(struct_fmt, data)

    if len(values) == 1:
        return values[0]
    else:
        if as_list:
            return values
        else:
            #Make up some keys if none were sent
            if keys is None:
                keys = [str(i) for i in range(len(values))]
            return dict(zip(keys, values))

def read_text(f):
    # Chris Lamb
    # https://stackoverflow.com/questions/40335658/read-null-terminated-string-in-python
    text = ''.join(iter(lambda: f.read(1).decode('ascii'), '\x00'))
    return text

def parse_xml(root, parent='Frame0'):
    dic = {}
    for r in root:
        for item in r.find(parent):
            val = item.text
            if 'i4' in str(item.attrib):
                val = int(val)
            elif 'r8' in str(item.attrib):
                val = float(val)
            dic[item.tag] = val
            #print('%s | %s | %s' % (item.tag, item.attrib, item.text))
        return dic

def ReadXML(fn='ImageInfo.xml'):
    tree = ET.parse(fn)
    root = tree.getroot()
    dic = parse_xml(root)
    return dic


def ReadPolygon(f):
    # The last point in the polygon is not saved in the file but should be
    # added to close the polygon. Polygons can be assumed to be clock wise
    # oriented and non-self-intersecting.
    npts = convert(f,'<i')
    dic = None

    if npts > 0:
        pts = convert(f,'<%df' % (npts*2), as_list=True)
        if pts is None:
            print('OOPS on the Polygon pts extraction!!')
        else:
            x_pts = pts[::2]
            y_pts = pts[1::2]

            dic = {'shape':POLYGON, 'x_pts':x_pts,'y_pts':y_pts}
        
    return dic

def ReadPolyLine(f):
    dic = ReadPolygon(f)
    dic['shape'] = POLYLINE
    return dic

def ReadLine(f):
    pts = convert(f,'<4d',as_list=True)
    x_pts = pts[::2]
    y_pts = pts[1::2]
    dic = {'shape':LINE, 'x_pts':x_pts,'y_pts':y_pts}
    return dic
    
def ReadEllipse(f):
    dic = convert(f, '<i5d', ['garbage','x_orig','y_orig','maj_axis','min_axis','angle'])
    w, h = dic['maj_axis'], dic['min_axis']
    ca, sa = np.cos(dic['angle']), np.sin(dic['angle'])
    a = np.arange(0,1.,1/100)*2*np.pi
    a = np.append(a, 0)

    dic = convert(f, '<i3d', ['garbage','x_orig','y_orig','radius'])
    dic['x_pts'] = dic['maj_axis']*ca*np.cos(a) - dic['min_axis']*sa*np.sin(a) + dic['x_orig']
    dic['y_pts'] = dic['maj_axis']*sa*np.cos(a) + dic['min_axis']*ca*np.sin(a) + dic['x_orig']
    dic['shape'] = ELLIPSE
    del dic['garbage']
    return dic

def ReadCircle(f):
    a = np.arange(0,1.,1/100)*2*np.pi
    a = np.append(a, 0)
    dic = convert(f, '<i3d', ['garbage','x_orig','y_orig','radius'])
    dic['x_pts'] = dic['radius']*np.cos(a) + dic['x_orig']
    dic['y_pts'] = dic['radius']*np.sin(a) + dic['y_orig']
    dic['shape'] = CIRCLE
    del dic['garbage']
    return dic    
    
def ReadRectangle(f):
    dic = convert(f, '<i5d', ['garbage','x_orig','y_orig','width','height','angle'])
    w, h = 2*dic['width'], 2*dic['height']
    ca, sa = np.cos(dic['angle']), np.sin(dic['angle'])
    dic['x_pts'] = np.array([0,w,w,0,0])*ca - np.array([0,0,h,h,0])*sa + dic['x_orig'] - w/2
    dic['y_pts'] = np.array([0,w,w,0,0])*sa + np.array([0,0,h,h,0])*ca + dic['y_orig'] - h/2

    dic['shape'] = RECTANGLE
    del dic['garbage']
    return dic
    
def ReadSquare(f):
    dic = convert(f, '<i4d', ['garbage','x_orig','y_orig','width','angle'])
    w = dic['width']
    ca, sa = np.cos(dic['angle']), np.sin(dic['angle'])
    dic['x_pts'] = np.array([0,w,w,0,0])*ca+dic['x_orig']
    dic['y_pts'] = np.array([0,0,w,w,0])*sa+dic['y_orig']
    dic['shape'] = SQUARE
    del dic['garbage']
    return dic
    
def ReadText(f):
    dic = convert(f, '<i2d', ['garbage','x_orig','y_orig'])
    dic['shape'] = RECTANGLE
    del dic['garbage']
    return dic

def ReadObject(f):
    ret = convert(f, '<2b', as_list=True) #object
    if ret is None:
        return None

    shape,typ = ret
    if shape == POLYGON:
        dic = ReadPolygon(f)
    elif shape == ELLIPSE:
        dic = ReadEllipse(f)
    elif shape == CIRCLE:
        dic = ReadCircle(f)
    elif shape == POLYLINE:
        dic = ReadPolyLine(f)
    elif shape == LINE:
        dic = ReadLine(f)
    elif shape == RECTANGLE:
        dic = ReadRectangle(f)
    elif shape == SQUARE:
        dic = ReadSquare(f)
    elif shape == TEXT:
        dic = ReadText(f)
    elif shape == 8:
        dic = ReadPolygon(f)
    else:
        print('OOPS!',shape)
        dic = None
    
    if dic is not None:
        #Text and additional info
        dic['text'] = read_text(f)
        dic['additional'] = read_text(f)
        dic['type'] = typ
    return dic

#def to return a mask image from just giving the folder
def GetMask(directory, objname='ROI', objid=0):
    fn_mld = os.path.join(directory, 'LayerData.mld')
    fn_xml = os.path.join(directory, 'ImageInfo.xml')
    fn_tif = os.path.join(directory, 'Image.tif')

    if not (os.path.exists(fn_mld) and os.path.exists(fn_xml) and os.path.exists(fn_tif)):
        return None

    mld = ReadMLDFile(fn_mld)
    if mld is None:
        return None
    info = ReadXML(fn_xml)
    im = Image.open(fn_tif)

    width, height = im.size
    ret = np.zeros(im.size[::-1],dtype=np.uint8)

    for obj in mld[objname]:
        if obj['shape'] == objid: # and obj['type'] == 3:
            #print(obj['type'])
            x_pts = np.array(obj['x_pts'])
            y_pts = np.array(obj['y_pts'])       
            vertices = np.vstack([x_pts,y_pts]).T
            arr = create_polygon(im.size[::-1],
                    vertices,extent=[info['Left'],info['Right'],info['Bottom'],info['Top']])        

            ret = np.bitwise_or(ret,arr*obj['type'])
    return ret

#Read a MLD file
def ReadMLDFile(fn, debug=False):
    f = open(fn,'rb')

    ret = convert(f,'<4s2i',['magic','version','nlayers'])
    if debug: print('Version=%d - nlayers=%d' % (ret['version'],ret['nlayers']))

    for layer_index in range(ret['nlayers']):
        layer_pos = f.seek(0,1)

        #In some cases, the buffer size given for a layer is smaller than it should.
        #We seek the next section if that happens:
        while 1:
            f.seek(layer_pos)
            _ = convert(f,'<64s?i',as_list=True)
            if _ is not None:
                name, imgcoords, nobjects = _
                name = name.rstrip(b'\0')
                if name in [b'ROI', b'Label', b'Annotation']:
                    break

            layer_pos+=1

        # Then decode the name:
        try:
            name = name.decode('utf-8')
        except:
            print('Layer %d corrupted:'%layer_index,name)
            name = 'L%d'%layer_index

        #Here we gather all the objects for that layer:
        objects = []
        if debug: print(f'{name}:{nobjects}')

        if nobjects > 0:
            buf_size = convert(f, '<i')

            obj_pos = f.seek(0,1)
            buf_pos = obj_pos

            for i in range(nobjects):
                failed = False
                #print(obj_pos + buf_size , buf_pos)

                obj = ReadObject(f)
                if obj is not None:
                    objects.append(obj)
                else:
                    failed = True

                buf_pos = f.seek(0,1)
                if buf_pos >= obj_pos + buf_size:
                    if debug: print('done!',buf_pos, obj_pos+buf_size,i+1,nobjects)
                    failed = True

                if failed:
                    break

            f.seek(obj_pos + buf_size)

        ret[name] = objects

    #Here we read additional objects characterised by a 0-terminated magic string
    layer_image_dic = {}
    while 1:
        magic = read_text(f)
        #print('>>>'+magic+'<<<')
        if magic == '':
            break

        if debug: print('Found '+magic)
        if magic.startswith('LDFF'):
            #Version of the LDFF, might as well record that
            ret['LDFF'] = magic
            break
        elif magic == '[LayerImage]':
            name = read_text(f)
            if name == '':
                print('LayerImage has no name...')
                break

                #4 bytes length
                image_len = convert(f,'<i')
                if image_len <= 0:
                    print('LayerImage has a corrupted size...')
                    break

                #Read the data stream
                data = f.read(image_len)
                if debug: print(f'image_len={image_len}, len={len(data)}')
                if len(data) != image_len:
                    print('LayerImage has a corrupted payload...')
                    break
            layer_image_dic[name] = data

        elif magic == '[LayerConfigs]' or magic == '[LayerAtlas]':
            section_len = convert(f,'<q')
            section_xml = ''
            if section_len > 0:
                section_xml = f.read(section_len)
            ret[magic[1:-1]] = section_xml
        else:
            print('Not implemented: '+magic)
            break

    f.close()
    return ret
