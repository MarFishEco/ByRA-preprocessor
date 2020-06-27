import os
import csv
import re
from qgis.core import QgsVectorLayer
from PyQt5.QtCore import pyqtRemoveInputHook
import pdb

class ByRaValidate:
  
  def __init__(self, _hraFolder: str, _gearFolder: str, _gearType: int, _mgmtShp: str, 
               _habSuitFolder: str, _intensity: bool, _likInter: bool, _mgmtStatus: bool,
               _outputFolder: str):
    self.hraFolder = _hraFolder
    self.gearFolder = _gearFolder
    self.gearType = _gearType
    self.mgmtShp = _mgmtShp
    self.habSuitFolder = _habSuitFolder
    self.intensity = _intensity
    self.likInter = _likInter
    self.mgmtStatus = _mgmtStatus
    self.outputFolder = os.path.expanduser(_outputFolder)
    self.species = []
    self.gear = {}
  
  EXTENT = 0
  DENSITY = 1
        
  def __srFile(self, _species):
    filename = '{}_ratings.csv'.format(_species)
    return os.path.join(self.hraFolder, filename)
  
  def __getSpecies(self):
    # Isolate species name from species ratings file e.g. DolphinHigh
    def getSpecies(_srFile):
      speciesRegex = "(?P<species>.*)_ratings.csv"
      speciesMatch = re.match(speciesRegex, _srFile)
      if speciesMatch is not None:
        return speciesMatch.group("species")
      
    srFiles = os.listdir(self.hraFolder)
    self.species = [s for s in map(getSpecies, srFiles) if s is not None]
  
  def __getGears(self):
    def getSpeciesGears(_species):
      srContents = list(open(self.__srFile(_species)))

      # Use regex to isolate gear name from entire line e.g. HookLine
      def getGear(s):
        gearRegex = "{0}/(?P<gear>.*) OVERLAP.*".format(_species)
        gearMatch = re.match(gearRegex, s)
        if gearMatch is not None:
          return gearMatch.group("gear")
      
      return [g for g in map(getGear, srContents) if g is not None]

    for s in self.species:
      self.gear[s] = getSpeciesGears(s)
  
  # Check if a shapefile has a field called "Rating"
  def hasRating(_shp):
    try:
      shp = QgsVectorLayer(_shp)
      fields = [f.name() for f in shp.fields()]
      return "Rating" in fields
    except:
      return False
      
  # Validate HRA folder
  def checkHra(self):
    # HRA folder must:
    ## Be an existing folder
    if not os.path.isdir(self.hraFolder):
      return 'NOHRAFOLDER'
    ## Contain one or more "[species]_ratings.csv" files
    self.__getSpecies()
    if not self.species:
      return 'NOSRFILES'
    ## Define one or more gears for each species
    self.__getGears()
    for s in self.species:
      if not self.gear[s]:
        return 'MISSINGGEAR:{}'.format(s)
    return 'PASS'
    
  # Validate gear coverage folder based on gear type
  def checkGear(self):
    # If gear type is set to Density...
    if self.gearType == ByRaValidate.DENSITY:
      ## There must be a gear shapefile for all gears in HRA files
      for s in self.species:
        for g in self.gear[s]:
          gearShp = os.path.join(self.gearFolder, '{}.shp'.format(g))
          if not os.path.isfile(gearShp):
            return 'NOGEARSHP:{}:{}'.format(s, g)
      ## Gear shapefiles must have a Rating field
      for s in self.species:
        for g in self.gear[s]:
          gearShp = os.path.join(self.gearFolder, '{}.shp'.format(g))
          if not ByRaValidate.hasRating(gearShp):
            return 'NOGEARRTG:{}:{}'.format(s, g)
      return 'PASS'
    # If gear type is set to Extent...
    if self.gearType == ByRaValidate.EXTENT:
      ## There must be a gear shapefile for all gears in HRA files
      for s in self.species:
        for g in self.gear[s]:
          gearShp = os.path.join(self.gearFolder, '{}.shp'.format(g))
          if not os.path.isfile(gearShp):
            return 'NOGEARSHP:{}'.format(g)
      return 'PASS'
    raise Exception('Something wrong with gearType')
  
  # Validate habitat suitability folder
  def checkHabSuit(self):
    ## All species in HRA folder must have a habitat suitability shapefile
    for s in self.species:
      habSuitShp = os.path.join(self.habSuitFolder, '{}.shp'.format(s))
      if not os.path.isfile(habSuitShp):
        return 'NOHABSHP:{}'.format(s)
    ## All habitat suitability shapefiles must have a Rating field
    for s in self.species:
      habSuitShp = os.path.join(self.habSuitFolder, '{}.shp'.format(s))
      if not ByRaValidate.hasRating(habSuitShp):
        return 'NOHABRTG:{}'.format(s)
    return 'PASS'
    
  # Validate management shapefile
  def checkMgmt(self):
    ## Shapefile must exist
    if not os.path.isfile(self.mgmtShp):
      return 'NOMGMTSHP'
    ## Shapefile must have Rating field
    if not ByRaValidate.hasRating(self.mgmtShp):
      return 'NOMGMTRTG'
    return 'PASS'
      
  def runChecks(self):    

    #pyqtRemoveInputHook()
    #pdb.set_trace()
    
    # Validate HRA folder
    hraCheck = self.checkHra()
    if not hraCheck == 'PASS':
      return hraCheck
        
    # Output folder must exist
    if not os.path.isdir(self.outputFolder):
      return 'NOOUTPUT'
        
    # If Intensity is checked, then:
    if self.intensity:
      ## Gear type must be density
      if not self.gearType == ByRaValidate.DENSITY:
        return 'INTENSITYDENSITY'
      ## Gear data must be valid
      gearCheck = self.checkGear()
      if not gearCheck == 'PASS':
        return gearCheck
      ## Habitat suitability data must be valid
      habSuitCheck = self.checkHabSuit()
      if not habSuitCheck == 'PASS':
        return habSuitCheck
      
    # If Likelihood of Interaction is checked, then:
    if self.likInter:
      ## Gear type must be density
      if not self.gearType == ByRaValidate.DENSITY:
        return 'LIKINTERDENSITY'
      ## Gear data must be valid
      gearCheck = self.checkGear()
      if not gearCheck == 'PASS':
        return gearCheck
      ## Habitat suitability data must be valid
      habSuitCheck = self.checkHabSuit()
      if not habSuitCheck == 'PASS':
        return habSuitCheck
        
    # If Status of Current Management is checked, then:
    if self.mgmtStatus:
      ## Managment shapefile must be valid
      mgmtCheck = self.checkMgmt()
      if not mgmtCheck == 'PASS':
        return mgmtCheck
      ## Gear data must be valid
      gearCheck = self.checkGear()
      if not gearCheck == 'PASS':
        return gearCheck
    
    return 'PASS'
