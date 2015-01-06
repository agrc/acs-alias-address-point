'''
Created on Dec 23, 2014

@author: kwalker
'''
import arcpy, os, time

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
    
    def start(self, roads, addrPoints, outputDirectory):       
        tempGdb = "in_memory"#r"C:\Users\kwalker\Documents\Aptana Studio 3 Workspace\acs-alias-address-point\data\tmpGdb.gdb"
        freqTable = os.path.join(r"C:\Users\kwalker\Documents\Aptana Studio 3 Workspace\acs-alias-address-point\data\tmpGdb.gdb", "roadFrequency")
        #self.deletelayerIfExist(freqTable)
        outputNear = os.path.join(r"C:\Users\kwalker\Documents\Aptana Studio 3 Workspace\acs-alias-address-point\data\tmpGdb.gdb", "finalNear")
        #self.deletelayerIfExist(outputNear)
        #Temp dev
        self.deletelayerIfExist(tempGdb)
        arcpy.CreateFileGDB_management(r"C:\Users\kwalker\Documents\Aptana Studio 3 Workspace\acs-alias-address-point\data", "tmpGdb.gdb")
        #Temp dev
        
        roadFields = RoadFields(roads)
        roadLayer = "roads"
        
        addrPointFields = AddressPointFields(addrPoints)
        addrPointLayer = "addressPoints"
        
        intermediateNears = []
        nearBaseName = "near"
        
        
        freqTime = time.time()#timer
        self.deletelayerIfExist("acsRoads")
        acsRoadsWhere = """("ACSNAME" <> '' and "ACSNAME" is not null) or ( "ALIAS1" <> '' and "ALIAS1" is not null)"""
        arcpy.MakeFeatureLayer_management (roads, "acsRoads", acsRoadsWhere)
        
        acsRoadsCount = arcpy.GetCount_management("acsRoads")
        print int(acsRoadsCount.getOutput(0))
        
        arcpy.Frequency_analysis("acsRoads", freqTable, roadFields.streetNameFields)
        print "freq time: {}".format(time.time() - freqTime)#timer
        #print
        
        nearNameI  = 0;
        #Create point and road feature layers for selections
        self.deletelayerIfExist(addrPointLayer)
        arcpy.MakeFeatureLayer_management (addrPoints, addrPointLayer)
        self.deletelayerIfExist(roadLayer)
        arcpy.MakeFeatureLayer_management (roads, roadLayer)
        loopTimeTotal = time.time()#timer
        with arcpy.da.SearchCursor(freqTable, roadFields.streetNameFields) as cursor:
            for row in cursor:
                loopTime = time.time()#timer

                preDirVal = row[roadFields.getI(roadFields.prefixDir)]
                streetVal = row[roadFields.getI(roadFields.street)]
                typeVal = row[roadFields.getI(roadFields.streetType)]
                
                addrPointWhere = """"{}" = '{}' and "{}" = '{}' and "{}" = '{}'""".format(addrPointFields.prefixDir, preDirVal, 
                                                                                          addrPointFields.street, streetVal, 
                                                                                          addrPointFields.streetType, typeVal)
                pointSelectTime = time.time()#timer
                arcpy.SelectLayerByAttribute_management (addrPointLayer, "NEW_SELECTION", addrPointWhere)
                print "Pont time: {}".format(time.time() - pointSelectTime)#timer
                
                roadWhere = """"{}" = '{}' and "{}" = '{}' and "{}" = '{}'""".format(roadFields.prefixDir, preDirVal, 
                                                                                          roadFields.street, streetVal, 
                                                                                          roadFields.streetType, typeVal)
                roadSelectTime = time.time()#timer
                arcpy.SelectLayerByAttribute_management (roadLayer, "NEW_SELECTION", roadWhere)
                print "Road time: {}".format(time.time() - roadSelectTime)#timer
                
                nearTime = time.time()#timer
                tempNearName = os.path.join(tempGdb, nearBaseName + str(nearNameI))
                arcpy.GenerateNearTable_analysis(addrPointLayer, roadLayer, tempNearName)
                #arcpy.Near_analysis(addrPointLayer, roadLayer)#, tempNearName)
                intermediateNears.append(tempNearName)
                print"Near time: {}".format(time.time() - nearTime)#timer
                nearNameI += 1
                print "Loop time: {}".format(time.time() - loopTime)#timer
                print
                
        print "LpTot time: {}".format(time.time() - loopTimeTotal)#timer
        mergeTime = time.time()#timer        
        arcpy.Merge_management(intermediateNears, outputNear)
        print "Merge time: {}".format(time.time() - mergeTime)#timer
        
        joinTime = time.time()#timer
        arcpy.JoinField_management(addrPoints, addrPointFields.objectId, outputNear, "IN_FID", ["NEAR_FID", "NEAR_DIST"])
        arcpy.JoinField_management(addrPoints, "NEAR_FID", roads, roadFields.objectId, roadFields.aliasFields)
        print "Join  time: {}".format(time.time() - joinTime)#timer
        #arcpy.Delete_management(tempGdb)
        
        

if __name__ == '__main__':
    roads = r"C:\GIS\Work\Roads.gdb\SL_County_Roads"#os.path.join(os.path.dirname(__file__), os.pardir, r"data\SampleData.gdb\Roads_SGID")
    addressPoints = r"C:\GIS\Work\AddressPoints.gdb\SL_County_AddrPoints"#os.path.join(os.path.dirname(__file__), os.pardir, r"data\SampleData.gdb\AddressPoints_SGID")
    
    totalTime = time.time()#timer
    aliasAdder = Main();
    aliasAdder.start(roads, addressPoints, "outputDirectory")
    print "Total Time: {}".format(time.time() - totalTime)