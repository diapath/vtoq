// Code discussed in https://forum.image.sc/t/issue-with-accented-names-with-my-annotations-geojson-import-export-script-attached/74621
import qupath.lib.scripting.QP

def read_geojson(removeAnnotations=true)
{
    def server = QP.getCurrentImageData().getServer()

    // need to add annotations to hierarchy so qupath sees them
    def hierarchy = QP.getCurrentHierarchy()
    clearSelectedObjects(false);
    
    if (removeAnnotations)
        removeObjects(getAnnotationObjects(), true)
    
    //*********Get GeoJSON automatically based on naming scheme 
    def path = GeneralTools.toPath(server.getURIs()[0]).toString()
    path = path+".geojson";

    def JSONfile = new File(path)
    if (JSONfile.exists()) {
        println "Processing "+path
    } else {
        println "No GeoJSON file for this image..."
        return
    }
    
    def cal = server.getPixelCalibration()
    if (!cal.hasPixelSizeMicrons()) {
        Dialogs.showMessageDialog("Metadata check", "No pixel information for this image!");
        return
    }

    def pixelWidth = cal.getPixelWidthMicrons()
    def pixelHeight = cal.getPixelHeightMicrons()
    def ANNOTATION_AREA_MICRONS = 100
    var objs = PathIO.readObjects(JSONfile)
    
    for (annotation in objs) {
        if (annotation.getROI().getScaledArea(pixelWidth, pixelHeight) < ANNOTATION_AREA_MICRONS)
            continue
            
        annotation.setLocked(true)
        hierarchy.addPathObject(annotation) 
    }

    runPlugin('qupath.lib.plugins.objects.RefineAnnotationsPlugin', '{"minFragmentSizeMicrons":100.0,"maxHoleSizeMicrons":100.0}')

    //Rely on name and class to fin the holes
    def holes = getAnnotationObjects().findAll {it.getPathClass()==getPathClass("Ignore") && it.getDisplayedName().equals("Hole")}
    for (hole in holes) {
        resolveHierarchy()
        parent = hole.getParent()
        if (parent == null)
            continue;
        roi = parent.getROI()
        if (roi == null)
            continue;
        parentGeom = parent.getROI().getGeometry()
        holeGeom = hole.getROI().getGeometry()
    
        parentGeom = parentGeom.difference(holeGeom)
        parentROI = GeometryTools.geometryToROI(parentGeom, ImagePlane.getDefaultPlane())
        newParent = PathObjects.createAnnotationObject(parentROI, parent.getPathClass())
        newParent.setLocked(true)
        addObject(newParent)
        removeObject(parent, true)    
        removeObject(hole, true)    
    }

    //Resolve Hierarchy again since we've introduced new objects
    //resolveHierarchy()
    fireHierarchyUpdate()    
}

def write_geojson()
{
    def server = QP.getCurrentImageData().getServer()

    // need to add annotations to hierarchy so qupath sees them
    def hierarchy = QP.getCurrentHierarchy()
        
    //*********Get GeoJSON automatically based on naming scheme 
    def path = GeneralTools.toPath(server.getURIs()[0]).toString()+".geojson";

    // need to add annotations to hierarchy so qupath sees them
    def pathObjects = hierarchy.getAnnotationObjects()

    // 'FEATURE_COLLECTION' is standard GeoJSON format for multiple objects
    exportObjectsToGeoJson(pathObjects, path, "FEATURE_COLLECTION")

    // The same method without the 'FEATURE_COLLECTION' parameter outputs a simple JSON object/array
    // exportObjectsToGeoJson(annotations, path)    
}

//write_geojson()

removeAnnotations=false
read_geojson(removeAnnotations)
