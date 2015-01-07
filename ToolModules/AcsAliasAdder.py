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
        self.prefixDir = "PREDIR"
        self.street = "STREETNAME"
        self.streetType = "STREETTYPE"
        self.alias1 = "ALIAS1"
        self.alias1Type = "ALIAS1TYPE"
        self.acsName = "ACSNAME"
        self.acsSuffix = "ACSSUF"   
        self.streetNameFields = [self.objectId, self.prefixDir, self.street, self.streetType]
        self.aliasFields = [self.alias1, self.alias1Type, self.acsName, self.acsSuffix]
        
        self._fieldList = [self.objectId, self.prefixDir, self.street, self.streetType, self.alias1, self.alias1Type, self.acsName, self.acsSuffix]

class AddressPointFields(Fields):
    def __init__(self, addrPoints):
        self.objectId = arcpy.Describe(addrPoints).OIDFieldName
        self.prefixDir = "PreFixDir"
        self.street = "StreetName"
        self.streetType = "StreetType"
        
        self._fieldList = [self.objectId, self.prefixDir, self.street, self.streetType]

class Main(object):
    
    def deletelayerIfExist(self, layerName):
        if arcpy.Exists(layerName):
            arcpy.Delete_management(layerName)
    
    def start(self, roadFeature, addrPointsFeature, outputDirectory):       
        #Intermediate tables. They are stored in memory.
        outputGdbName = "AcsAliasAdd_" + strftime("%Y%m%d%H%M%S") + ".gdb"
        arcpy.CreateFileGDB_management(outputDirectory, outputGdbName)
        outputGdb = os.path.join(outputDirectory, outputGdbName)
        tempGdb = "in_memory"
        roads = os.path.join(outputGdb, "tempRoads")
        addrPoints = os.path.join(outputGdb, "AddrPoints_W_Alias")
        freqTable = os.path.join(tempGdb, "roadFrequency")
        outputNear = os.path.join(tempGdb, "finalNear")
        self.deletelayerIfExist(tempGdb)
        
        #Copy features
        acsRoadsWhere = """("ACSNAME" <> '' and "ACSNAME" is not null) or ( "ALIAS1" <> '' and "ALIAS1" is not null)"""
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
        
        arcpy.Frequency_analysis("acsRoads", freqTable, roadFields.streetNameFields)
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
                if nearNameI % 32 == 0:
                    print  "Precent Complete: %{0:0.2f}".format(nearNameI / uniqueRoadNamesCount * 100)

                preDirVal = row[roadFields.getI(roadFields.prefixDir)]
                streetVal = row[roadFields.getI(roadFields.street)]
                typeVal = row[roadFields.getI(roadFields.streetType)]
                
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
        arcpy.Merge_management(intermediateNears, outputNear)
        #Join Object ID of closest road to point and add alias fields
        arcpy.JoinField_management(addrPoints, addrPointFields.objectId, outputNear, "IN_FID", ["NEAR_FID", "NEAR_DIST"])
        arcpy.JoinField_management(addrPoints, "NEAR_FID", roads, roadFields.objectId, roadFields.aliasFields)
        print  "Precent Complete: %100"
        self.deletelayerIfExist(roads)
        arcpy.Delete_management(tempGdb)
        
        

if __name__ == '__main__':
    roads = os.path.join(os.path.dirname(__file__), os.pardir, r"data\SampleData.gdb\Roads_SGID")
    addressPoints = os.path.join(os.path.dirname(__file__), os.pardir, r"data\SampleData.gdb\AddressPoints_SGID")
    outputDirectory = os.path.join(os.path.dirname(__file__), os.pardir, "data")
    
    totalTime = time.time()#timer
    aliasAdder = Main();
    aliasAdder.start(roads, addressPoints, outputDirectory)
    print "Total Time: {0:.03f} seconds".format(time.time() - totalTime)