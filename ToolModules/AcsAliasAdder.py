'''
Add alias fields to address points
from the cloest road with the same name.

'''
import arcpy, os, time
from time import strftime

class Fields (object):
    
    def __init__(self):
        self._fieldList = []
        
    def getI(self, field):
        return self._fieldList.index(field)
    
    def getFieldList(self):
        return self._fieldList


class RoadFields(Fields):
    def __init__(self, roads):
        self.objectId = arcpy.Describe(roads).OIDFieldName
        self.prefixDir = "PRE_DIR"
        self.street = "S_NAME"
        self.streetType = "S_TYPE"
#         self.alias1 = "ALIAS1"
#         self.alias1Type = "ALIAS1TYPE"
        self.acsName = "ACS_STREET"
        self.acsSuffix = "ACS_SUFDIR"   
        self.streetNameFields = [self.prefixDir, self.street, self.streetType]
        self.aliasFields = [self.acsName, self.acsSuffix]
        
        self._fieldList = [self.objectId, self.prefixDir, self.street, self.streetType,self.acsName, self.acsSuffix]

class AddressPointFields(Fields):
    def __init__(self, addrPoints):
        self.objectId = arcpy.Describe(addrPoints).OIDFieldName
        self.prefixDir = "PreDir"
        self.street = "S_NAME"
        self.streetType = "Suf"
        
        self._fieldList = [self.objectId, self.prefixDir, self.street, self.streetType]

class Main(object):
    
    def deletelayerIfExist(self, layerName):
        if arcpy.Exists(layerName):
            arcpy.Delete_management(layerName)
    
    def start(self, roadFeature, addrPointsFeature, outputDirectory):       
        #Output layers.
        outputGdbName = "AcsAliasAdd_" + "Results" + ".gdb"
        arcpy.CreateFileGDB_management(outputDirectory, outputGdbName)
        outputGdb = os.path.join(outputDirectory, outputGdbName)
        #Intermediate tables.
        tempGdbName = "temp_" + strftime("%Y%m%d%H%M%S") + ".gdb"
        arcpy.CreateFileGDB_management(outputDirectory, tempGdbName)
        tempGdb = os.path.join(outputDirectory, tempGdbName)
        
        roads = os.path.join(outputGdb, "AliasRoads")
        addrPoints = os.path.join(outputGdb, "AddrPoints_W_Alias")
        freqTable = os.path.join(tempGdb, "roadFreq")
        outputNear = os.path.join(tempGdb, "finalNear")

        #Copy features
        acsRoadsWhere = """("{0}" <> '' and "{0}" is not null)""".format("ACS_STREET")
        arcpy.MakeFeatureLayer_management (roadFeature, "acsRoads", acsRoadsWhere)
        arcpy.CopyFeatures_management("acsRoads", roads)
        
        arcpy.CopyFeatures_management(addrPointsFeature, addrPoints)
        
        #Fied Objects for input layers. Schema changes can be handled in the Field classes
        roadFields = RoadFields(roads)
        roadLayer = "roads"
        addrPointFields = AddressPointFields(addrPoints)
        addrPointLayer = "addressPoints"
        #Local accumulator variables
        intermediateNears = []
        nearBaseName = "near"
        
        arcpy.Frequency_analysis(roads, freqTable, roadFields.streetNameFields)
        #Frequency table count for measuring progress
        self.deletelayerIfExist("freqCount")
        arcpy.MakeTableView_management(freqTable, "freqCount")
        uniqueRoadNamesCount = arcpy.GetCount_management("freqCount")
        uniqueRoadNamesCount = int(uniqueRoadNamesCount.getOutput(0))
        print "Unique street names: {}".format(uniqueRoadNamesCount)
        #Index feature classes to speed up selections
        arcpy.AddIndex_management (addrPoints, 
                                   "{};{};{}".format(addrPointFields.street, addrPointFields.prefixDir, addrPointFields.streetType), 
                                   "addrPnt_IDX11", "NON_UNIQUE", "ASCENDING")
        arcpy.AddIndex_management (roads, 
                                  "{};{};{}".format(roadFields.street, roadFields.prefixDir, roadFields.streetType), 
                                   "roads_IDX11", "NON_UNIQUE", "ASCENDING")
        
        nearNameI  = 1;
        uniqueRoadNamesCount = float(uniqueRoadNamesCount)
        #Create point and road feature layers for selections
        self.deletelayerIfExist(addrPointLayer)
        arcpy.MakeFeatureLayer_management (addrPoints, addrPointLayer)
        self.deletelayerIfExist(roadLayer)
        arcpy.MakeFeatureLayer_management (roads, roadLayer)
        #Main loop. Selects points and roads that share a street name and does Near analysis
        print  "Precent Complete: %0"
        with arcpy.da.SearchCursor(freqTable, roadFields.streetNameFields) as cursor:
            for row in cursor:
                #Progress update
                if nearNameI % 128 == 0:
                    print  "Precent Complete: %{0:0.2f}".format(nearNameI / uniqueRoadNamesCount * 100)

                preDirVal = row[0]#roadFields.getI(roadFields.prefixDir)]
                streetVal = row[1]#roadFields.getI(roadFields.street)]
                typeVal = row[2]#roadFields.getI(roadFields.streetType)]
                
                addrPointWhere = """"{}" = '{}' and "{}" = '{}' and "{}" = '{}'""".format(addrPointFields.prefixDir, preDirVal, 
                                                                                          addrPointFields.street, streetVal, 
                                                                                          addrPointFields.streetType, typeVal)
                arcpy.SelectLayerByAttribute_management (addrPointLayer, "NEW_SELECTION", addrPointWhere)
                
                roadWhere = """"{}" = '{}' and "{}" = '{}' and "{}" = '{}'""".format(roadFields.prefixDir, preDirVal, 
                                                                                          roadFields.street, streetVal, 
                                                                                          roadFields.streetType, typeVal)
                arcpy.SelectLayerByAttribute_management (roadLayer, "NEW_SELECTION", roadWhere)
                
                
                tempNearName = os.path.join(tempGdb, nearBaseName + str(nearNameI))
                arcpy.GenerateNearTable_analysis(addrPointLayer, roadLayer, tempNearName)
                intermediateNears.append(tempNearName)
                #Increment index to keep near tables unique
                nearNameI += 1

                      
        #Merge intermediat near tables
        print "Start Append"
        ourputNear = os.path.join(outputGdb, "finalNear")
        first = 1
        for near in intermediateNears:
            if first:
                arcpy.CopyRows_management(near, outputNear)
                first = 0
            else:
                arcpy.Append_management(near, outputNear)
        #Join Object ID of closest road to point and add alias fields
        arcpy.JoinField_management(addrPoints, addrPointFields.objectId, outputNear, "IN_FID", ["NEAR_FID", "NEAR_DIST"])
        arcpy.JoinField_management(addrPoints, "NEAR_FID", roads, roadFields.objectId, roadFields.aliasFields)
        print  "Precent Complete: %100"
        #arcpy.Delete_management(tempGdb)
        
        

if __name__ == '__main__':
    roads = r"path to roads here"#Path to road data
    addressPoints = r"path to address points here"#Path to address point data
    outputDirectory = r"output directory here"#Output working directory
    
    totalTime = time.time()#timer
    aliasAdder = Main();
    aliasAdder.start(roads, addressPoints, outputDirectory)
    print "Total Time: {0:.03f} seconds".format(time.time() - totalTime)