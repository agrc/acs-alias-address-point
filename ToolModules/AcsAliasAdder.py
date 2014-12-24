'''
Created on Dec 23, 2014

@author: kwalker
'''
import arcpy, os

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
        
        self._fieldList = [self.objectId, self.prefixDir, self.street, self.streetType]

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
    
    def start(self, roads, addrPoints, outputDirectory):
        tempGdb = r"C:\Users\kwalker\Documents\GitHub\acs-alias-address-point\data\tmpGdb.gdb"#"in_memory"
        freqTable = os.path.join(tempGdb, "roadFrequency")
        self.deletelayerIfExist(freqTable)
        
        roadFields = RoadFields(roads)
        roadLayer = "roads"
        
        addrPointFields = AddressPointFields(addrPoints)
        addrPointLayer = "addressPoints"
        
        intermediateNears = []
        nearBaseName = "near"
        
        nearNameI  = 0;
        arcpy.Frequency_analysis(roads, freqTable, [roadFields.prefixDir, roadFields.street, roadFields.streetType])
        with arcpy.da.SearchCursor(freqTable, roadFields.getFieldList()) as cursor:
            for row in cursor:
                #print"sfsdfsdfsdf"
                preDirVal = row[roadFields.getI(roadFields.prefixDir)]
                streetVal = row[roadFields.getI(roadFields.street)]
                typeVal = row[roadFields.getI(roadFields.streetType)]
                
                addrPointWhere = """"{}" = '{}' and "{}" = '{}' and "{}" = '{}'""".format(addrPointFields.prefixDir, preDirVal, 
                                                                                          addrPointFields.street, streetVal, 
                                                                                          addrPointFields.streetType, typeVal)
                print addrPointWhere
                self.deletelayerIfExist(addrPointLayer)
                arcpy.MakeFeatureLayer_management (addrPoints, addrPointLayer)
                arcpy.SelectLayerByAttribute_management (addrPointLayer, "NEW_SELECTION", addrPointWhere)
                
                roadWhere = """"{}" = '{}' and "{}" = '{}' and "{}" = '{}'""".format(roadFields.prefixDir, preDirVal, 
                                                                                          roadFields.street, streetVal, 
                                                                                          roadFields.streetType, typeVal)
                print roadWhere
                self.deletelayerIfExist(roadLayer)
                arcpy.MakeFeatureLayer_management (roads, roadLayer)
                arcpy.SelectLayerByAttribute_management (roadLayer, "NEW_SELECTION", roadWhere)
                
                arcpy.GenerateNearTable_analysis(addrPointLayer, roads, os.path.join(tempGdb, nearBaseName + str(nearNameI)))
                nearNameI += 1
        
        #arcpy.Delete_management(tempGdb)
        
        

if __name__ == '__main__':
    aliasAdder = Main();
    aliasAdder.start(r"C:\Users\kwalker\Documents\GitHub\acs-alias-address-point\data\SampleData.gdb\Roads_SGID",
                      r"C:\Users\kwalker\Documents\GitHub\acs-alias-address-point\data\SampleData.gdb\AddressPoints_SGID",
                      "outputDirectory")