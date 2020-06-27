import os
import processing
import uuid
import tempfile
from qgis.core import QgsVectorLayer, QgsField
from .byra_validate import ByRaValidate
from PyQt5.QtCore import pyqtRemoveInputHook, QVariant
import pdb

class ByRaPreprocessor:
  
  def __init__(self, validator: ByRaValidate):
    self.hraFolder = validator.hraFolder
    self.gearFolder = validator.gearFolder
    self.mgmtShp = validator.mgmtShp
    self.habSuitFolder = validator.habSuitFolder
    self.species = validator.species
    self.gear = validator.gear
    
    exposurePath = os.path.expanduser(
      os.path.join(validator.outputFolder, \
                   'Spatially_Explicit_Criteria', \
                   'Exposure'))
    if not os.path.exists(exposurePath):
      os.makedirs(exposurePath)
    self.exposureFolder = exposurePath

  # Fishing intensity
  def intensitySEC(self):
    # Iterate through species and gear
    result = []
    for sp in self.species:
      for g in self.gear[sp]:
        sp_shp = os.path.join(self.habSuitFolder, "{0}.shp".format(sp))
        gear_shp = os.path.join(self.gearFolder, "{0}.shp".format(g))
        fixgear_params = { 'INPUT' : gear_shp,
                           'OUTPUT' : 'memory:' }
        dissgear_params = { 'FIELD' : ['Rating'],
                            'OUTPUT' : 'memory:' }
        fixsp_params = { 'INPUT' : sp_shp,
                         'OUTPUT' : 'memory:' }
        disssp_params = { 'FIELD' : ['Rating'],
                          'OUTPUT' : 'memory:' }
        intensitySEC_shp = os.path.join(self.exposureFolder, "{0}_{1}_intensity.shp".format(sp, g))
        params = { 'OVERLAY' : sp_shp,
                   'OUTPUT' : intensitySEC_shp }
        # Clip gear to habitat suitability shapefile
        try:
          fixed_gear = processing.run('qgis:fixgeometries', fixgear_params)
          dissgear_params['INPUT'] = fixed_gear['OUTPUT']
          dissolved_gear = processing.run('qgis:dissolve', dissgear_params)
          params['INPUT'] = dissolved_gear['OUTPUT']
          
          fixed_sp = processing.run('qgis:fixgeometries', fixsp_params)
          disssp_params['INPUT'] = fixed_gear['OUTPUT']
          dissolved_sp = processing.run('qgis:dissolve', disssp_params)
          params['OVERLAY'] = dissolved_sp['OUTPUT']
          
          processing.run('qgis:clip', params)
          result.append((sp, g, True))
        except:
          result.append((sp, g, False))
    # Return results
    return result
        

  # Likelihood of interaction
  def likInterSEC(self):
    # Iterate through species and gear
    result = []
    for sp in self.species:
      for g in self.gear[sp]:
        sp_shp = os.path.join(self.habSuitFolder, "{0}.shp".format(sp))
        gear_shp = os.path.join(self.gearFolder, "{0}.shp".format(g))
        fixgear_params = { 'INPUT' : gear_shp,
                           'OUTPUT' : 'memory:' }
        dissgear_params = { 'FIELD' : ['Rating'],
                            'OUTPUT' : 'memory:' }
        fixsp_params = { 'INPUT' : sp_shp,
                         'OUTPUT' : 'memory:' }
        disssp_params = { 'FIELD' : ['Rating'],
                          'OUTPUT' : 'memory:' }
        likinterSEC_shp = os.path.join(self.exposureFolder, "{0}_{1}_likelihood_of_interaction.shp".format(sp, g))
        params = { 'INPUT_FIELDS' : ['Rating'],
                   'OVERLAY_FIELDS' : ['Rating'],
                   'OUTPUT' : likinterSEC_shp }
        # Intersect gear with habitat suitability shapefile
        try:
          fixed_gear = processing.run('qgis:fixgeometries', fixgear_params)
          dissgear_params['INPUT'] = fixed_gear['OUTPUT']
          dissolved_gear = processing.run('qgis:dissolve', dissgear_params)
          params['INPUT'] = dissolved_gear['OUTPUT']
          
          fixed_sp = processing.run('qgis:fixgeometries', fixsp_params)
          disssp_params['INPUT'] = fixed_sp['OUTPUT']
          dissolved_sp = processing.run('qgis:dissolve', disssp_params)
          params['OVERLAY'] = dissolved_sp['OUTPUT']
          
          processing.run('qgis:intersection', params)
          # Load the intersected shapefile and add a new field for the rating
          likinterSEC_lyr = QgsVectorLayer(likinterSEC_shp)
          likinterSEC_lyr.dataProvider().addAttributes([QgsField('TMP', QVariant.Int)])
          likinterSEC_lyr.updateFields()
          # New rating is based on sum of input ratings: 2,3 -> 1, 4 -> 2, 5,6 -> 3
          for f in likinterSEC_lyr.getFeatures():
            rating_sum = f['RATING'] + f['RATING_2']
            if rating_sum <= 3:
              new_rating = 1
            if rating_sum == 4:
              new_rating = 2
            if rating_sum >= 5:
              new_rating = 3
            # 2 is the index of the new TMP field
            likinterSEC_lyr.dataProvider().changeAttributeValues({f.id(): {2: new_rating}})
          # Delete old fields, create a new RATING based on TMP
          likinterSEC_lyr.dataProvider().deleteAttributes([0, 1])
          likinterSEC_lyr.dataProvider().addAttributes([QgsField('RATING', QVariant.Int)])
          likinterSEC_lyr.updateFields()
          for f in likinterSEC_lyr.getFeatures():
            new_rating = f['TMP']
            # 1 is the index of the new RATING field
            likinterSEC_lyr.dataProvider().changeAttributeValues({f.id(): {1: new_rating}})
          likinterSEC_lyr.dataProvider().deleteAttributes([0])
          result.append((sp, g, True))
        except:
          result.append((sp, g, False))
    # Return results
    return result

  # Status of management
  def mgmtSEC(self):
    # Iterate through species and gear
    result = []
    for sp in self.species:
      for g in self.gear[sp]:
        gear_shp = os.path.join(self.gearFolder, "{0}.shp".format(g))
        mgmt_shp = self.mgmtShp
        mgmtSEC_shp = os.path.join(self.exposureFolder, "{0}_{1}_current_status_of_management.shp".format(sp, g))
        fixgear_params = { 'INPUT' : gear_shp,
                           'OUTPUT' : 'memory:' }
        dissgear_params = { 'FIELD' : ['Rating'],
                            'OUTPUT' : 'memory:' }
        fixmgmt_params = { 'INPUT' : mgmt_shp,
                           'OUTPUT' : 'memory:' }  
        dissmgmt_params = { 'FIELD' : ['Rating'],
                            'OUTPUT' : 'memory:' }      
        union_params = { 'OUTPUT' : 'memory:' }
        clip_params = { 'OUTPUT' : mgmtSEC_shp }
        # Union gear with management shapefile, calculate rating, then clip to gear
        try:
          fixed_gear = processing.run('qgis:fixgeometries', fixgear_params)
          dissgear_params['INPUT'] = fixed_gear['OUTPUT']
          dissolved_gear = processing.run('qgis:dissolve', dissgear_params)
          union_params['INPUT'] = dissolved_gear['OUTPUT']
          clip_params['OVERLAY'] = dissolved_gear['OUTPUT']
          
          fixed_mgmt = processing.run('qgis:fixgeometries', fixmgmt_params)
          dissmgmt_params['INPUT'] = fixed_mgmt['OUTPUT']
          dissolved_mgmt = processing.run('qgis:dissolve', dissmgmt_params)
          union_params['OVERLAY'] = dissolved_mgmt['OUTPUT']
          
          mgmt_gear_union = processing.run('qgis:union', union_params)
          clip_params['INPUT'] = mgmt_gear_union['OUTPUT']
          processing.run('qgis:clip', clip_params)
          
          # Load the unioned shapefile and add a new field for the rating
          mgmtSEC_lyr = QgsVectorLayer(mgmtSEC_shp)
          mgmtSEC_lyr.dataProvider().addAttributes([QgsField('TMP', QVariant.Int)])
          mgmtSEC_lyr.updateFields()
          # Get index of "TMP" field
          tmp_fld = mgmtSEC_lyr.fields().indexFromName('TMP')
          # New rating is based on mgmt ratings. Anything outside ('Rating_2' is null) gets a 3.
          for f in mgmtSEC_lyr.getFeatures():
            new_rating = f['RATING_2']
            if not type(new_rating) is int:
              new_rating = 3
            mgmtSEC_lyr.dataProvider().changeAttributeValues({f.id(): {tmp_fld: new_rating}})
          # Delete old fields, create a new RATING based on TMP
          # Get index of "Rating", "Rating_2" fields
          delete_flds = [mgmtSEC_lyr.fields().indexFromName(f) for f in ['Rating', 'Rating_2']]
          mgmtSEC_lyr.dataProvider().deleteAttributes(delete_flds)
          mgmtSEC_lyr.dataProvider().addAttributes([QgsField('RATING', QVariant.Int)])
          mgmtSEC_lyr.updateFields()
          # Get index of new "RATING" field
          rating_fld = mgmtSEC_lyr.fields().indexFromName('RATING')
          for f in mgmtSEC_lyr.getFeatures():
            new_rating = f['TMP']
            mgmtSEC_lyr.dataProvider().changeAttributeValues({f.id(): {rating_fld: new_rating}})
          # Delete TMP field
          tmp_fld = mgmtSEC_lyr.fields().indexFromName('TMP')
          mgmtSEC_lyr.dataProvider().deleteAttributes([tmp_fld])
          result.append((sp, g, True))
        except:
          result.append((sp, g, False))
    # Return results
    return result
    