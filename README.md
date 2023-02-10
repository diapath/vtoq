# vtoq
Visiopharm to QuPath migration scripts

`vtoq` relies on a TSV results file exported from Visiopharm, to select image which need their ROIs exported as QuPath annotations (via GeoJSON files). The GeoJSON files are saved together with the images (path/image.ndpi -> path/image.ndpi.geojson). These can be imported en-masse for a QuPath project via the read_write_geojson.groovy script in this repository and discussed on [forum.image.sc](https://forum.image.sc/t/issue-with-accented-names-with-my-annotations-geojson-import-export-script-attached).

## Limitations
For now, `vtoq` only handles Visiopharm ROIs (not labels) and relies on the underlying images to be in the Hamamatsu NDPI format. This is because `vtoq` needs to convert vertices defined in physical units into pixel units. This is something I could only do by fetching pixel sizes, slide origin, image dimensions in the Original image. I have not yet looked at how to do this with other image formats than Hamamatsu NDPI. I use [tifffile](https://github.com/cgohlke/tifffile) to read the WSI image metadata.

`vtoq` tags holes as annotations named 'Hole' and classed 'Ignore' and then relies on QuPath to subtract them from their resolved parents. `vtoq` also handles ROIs with different indexes and can attribute a different class to each index.

## Contact
Do not hesitate to ping me here @zindy or on [https://forum.image.sc](https://forum.image.sc/t/python-script-to-migrate-visiopharm-roi-annotations-to-qupath) (@EP.Zindy) if you want to discuss this or help me improve the tools.

Cheers,\
Egor

# Migration steps
## In Visiopharm
Select the images, right click, select "Export selected results (.tsv)" and save a `test.tsv` file.

## In Python

The following code reads the tsv file previously saved, and for each Image and its LayerData, generates a GeoJSON file saved in the same location as the image (add .geojson to the image name).

If you want to attribute specific classes to the annotations (depending on their Visiopharm ROI index), you need to defined these as `vtoq.Classification` dictionaries. The following code defines two such classes, one for Tumor and one for Tissue.

```python
import csv
import vtoq

fn_tsv = 'test.tsv'

#Here we defined the annotation classifications for QuPath (name, color as 6 bytes RGB hex value)
c1 = vtoq.Classification("Tumor", 0xc80000)
c2 = vtoq.Classification("Tissue", 0x00c800)

#The keys are the ROI indexes used in Visiopharm
classes = {1:c1, 2:c2}

#Iterate through the TSV file making dictionaries from the header line
with open(fn_tsv, newline='') as csvfile:
    reader = csv.DictReader(csvfile, delimiter='\t')
    for row in reader:
        fn_image = row['Image']
        fn_mld = row['LayerData']
        print(fn_image)
        vtoq.do_convert(fn_mld, fn_image, classes=classes, overwrite=True)

```

With `overwrite=False` it should(?) be possible to import multiple sets of Visiopharm annotations into the same GeoJSON file. Say if you have a set of "Tissue" ROIs in one study, and a set of "Tumor" ROIs in a different study, but both point to the same image, then you could combine the two into a single QuPath GeoJSON feature collection with different classes for either "Tumor" or "Tissue" annotations.

## In QuPath
Assuming you have a project with some / all of the images defined in the tsv file, run the `read_write_geojson.groovy` file for the images in your project. The script will look for `imagename.extension.geojson` files at the same location as the images and import the collections in addition to any existing contours for that image.
