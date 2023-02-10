// Code discussed in https://forum.image.sc/t/issue-with-accented-names-with-my-annotations-geojson-import-export-script-attached/74621
import qupath.lib.scripting.QP

def read_geojson()
{
    def server = QP.getCurrentImageData().getServer()

    // need to add annotations to hierarchy so qupath sees them
    def hierarchy = QP.getCurrentHierarchy()
        
    //*********Get GeoJSON automatically based on naming scheme 
    def path = GeneralTools.toPath(server.getURIs()[0]).toString()+".geojson";

    def JSONfile = new File(path)
    if (!JSONfile.exists()) {
        println "No GeoJSON file for this image..."
        return
    }

    var objs = PathIO.readObjects(JSONfile)
    for (annotation in objs) {
        println "Object: "+annotation.toString()
            
        annotation.setLocked(true)
        hierarchy.addPathObject(annotation) 
    }
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
read_geojson()
