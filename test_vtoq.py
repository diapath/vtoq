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

import csv, sys, os
import vtoq

def main():
    fn_tsv = sys.argv[1] if len(sys.argv) == 2 else None
    if len(sys.argv) != 2 or not os.path.exists(fn_tsv):
        print("Usage:\ntest_vtoq.py filename.tsv")
        return

    #Here we defined the annotation classifications for QuPath (name, color as 6 bytes RGB hex value)
    with open(fn_json) as f:
        #The keys are the ROI indexes used in Visiopharm
        classes = {int(c): vtoq.Classification(name, int(rgb, 16)) for c, (name, rgb) in json.load(f).items()}

    #Iterate through the TSV file making dictionaries from the header line
    with open(fn_tsv, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in reader:
            fn_image = row['Image']
            fn_mld = row['LayerData']

            print(fn_image)
            #This is NDPI specific, but the idea to split this function out of do_convert is that
            #maybe we'll be able to read the scale_factor and offset a different way
            scale_factor, offset = vtoq.get_scale_offset(fn_image)
            vtoq.do_convert(fn_mld, fn_image, classes=classes, overwrite=True, scale_factor=scale_factor, offset=offset)

if __name__ == '__main__':
    main()
