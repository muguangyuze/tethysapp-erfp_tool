from crontab import CronTab
import datetime
from getpass import getuser
from glob import glob
import netCDF4 as NET
import numpy as np
import os
from shutil import move
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import ObjectDeletedError
from django.http import JsonResponse

#django imports
from django.contrib.auth.decorators import user_passes_test

#tethys imports
from tethys_dataset_services.engines import GeoServerSpatialDatasetEngine

#local imports
from .model import (DataStore, Geoserver, MainSettings, SettingsSessionMaker,
                    Watershed, WatershedGroup)

from .functions import (check_shapefile_input_files,
                        delete_old_watershed_prediction_files,
                        delete_old_watershed_files, 
                        delete_old_watershed_kml_files, find_most_current_files, 
                        format_name, get_cron_command, get_reach_index, 
                        handle_uploaded_file, user_permission_test)
                        
@user_passes_test(user_permission_test)
def data_store_add(request):
    """
    Controller for adding a data store.
    """
    if request.is_ajax() and request.method == 'POST':
        #get/check information from AJAX request
        post_info = request.POST
        data_store_name = post_info.get('data_store_name')
        data_store_type_id = post_info.get('data_store_type_id')
        data_store_endpoint = post_info.get('data_store_endpoint')
        data_store_api_key = post_info.get('data_store_api_key')
    
        #initialize session
        session = SettingsSessionMaker()
        
        #check to see if duplicate exists
        num_similar_data_stores  = session.query(DataStore) \
            .filter(
                or_(
                    DataStore.name == data_store_name, 
                    DataStore.api_endpoint == data_store_endpoint
                )
            ) \
            .count()
        if(num_similar_data_stores > 0):
            return JsonResponse({ 'error': "A data store with the same name or api endpoint exists." })
            
        #add Data Store
        session.add(DataStore(data_store_name, data_store_type_id, data_store_endpoint, data_store_api_key))
        session.commit()
        session.close()
        
        return JsonResponse({ 'success': "Data Store Sucessfully Added!" })

    return JsonResponse({ 'error': "A problem with your request exists." })

@user_passes_test(user_permission_test)
def data_store_delete(request):
    """
    Controller for deleting a data store.
    """
    if request.is_ajax() and request.method == 'POST':
        #get/check information from AJAX request
        post_info = request.POST
        data_store_id = post_info.get('data_store_id')
    
        if int(data_store_id) != 1:
            try:
                #initialize session
                session = SettingsSessionMaker()
                #update data store
                data_store  = session.query(DataStore).get(data_store_id)
                session.delete(data_store)
                session.commit()
                session.close()
            except IntegrityError:
                return JsonResponse({ 'error': "This data store is connected with a watershed! Must remove connection to delete." })
            return JsonResponse({ 'success': "Data Store Sucessfully Deleted!" })
        return JsonResponse({ 'error': "Cannot change this data store." })
    return JsonResponse({ 'error': "A problem with your request exists." })

@user_passes_test(user_permission_test)
def data_store_update(request):
    """
    Controller for updating a data store.
    """
    if request.is_ajax() and request.method == 'POST':
        #get/check information from AJAX request
        post_info = request.POST
        data_store_id = post_info.get('data_store_id')
        data_store_name = post_info.get('data_store_name')
        data_store_api_endpoint = post_info.get('data_store_api_endpoint')
        data_store_api_key = post_info.get('data_store_api_key')
    
        if int(data_store_id) != 1:
            #initialize session
            session = SettingsSessionMaker()
            #update data store
            data_store  = session.query(DataStore).get(data_store_id)
            data_store.name = data_store_name
            data_store.api_endpoint= data_store_api_endpoint    
            data_store.api_key = data_store_api_key
            session.commit()
            session.close()
            return JsonResponse({ 'success': "Data Store Sucessfully Updated!" })
        return JsonResponse({ 'error': "Cannot change this data store." })
    return JsonResponse({ 'error': "A problem with your request exists." })

@user_passes_test(user_permission_test)
def geoserver_add(request):
    """
    Controller for adding a geoserver.
    """
    if request.is_ajax() and request.method == 'POST':
        #get/check information from AJAX request
        post_info = request.POST
        geoserver_name = post_info.get('geoserver_name')
        geoserver_url = post_info.get('geoserver_url')
        geoserver_username = post_info.get('geoserver_username')
        geoserver_password = post_info.get('geoserver_password')
    
        #check data
        if not geoserver_name or not geoserver_url or not \
            geoserver_username or not geoserver_password:
            return JsonResponse({ 'error': "Missing input data." })
        #clean url
        geoserver_url = geoserver_url.strip()
        if geoserver_url.endswith('/'):
            geoserver_url = geoserver_url[:-1]
        #initialize session
        session = SettingsSessionMaker()
        
        #check to see if duplicate exists
        num_similar_geoservers  = session.query(Geoserver) \
            .filter(
                or_(
                    Geoserver.name == geoserver_name, 
                    Geoserver.url == geoserver_url
                )
            ) \
            .count()
        if(num_similar_geoservers > 0):
            session.close()
            return JsonResponse({ 'error': "A geoserver with the same name or url exists." })
            
        #add Data Store
        session.add(Geoserver(geoserver_name.strip(), geoserver_url.strip(),
                              geoserver_username.strip(), geoserver_password.strip()))
        session.commit()
        session.close()
        return JsonResponse({ 'success': "Geoserver Sucessfully Added!" })

    return JsonResponse({ 'error': "A problem with your request exists." })

@user_passes_test(user_permission_test)
def geoserver_delete(request):
    """
    Controller for deleting a geoserver.
    """
    if request.is_ajax() and request.method == 'POST':
        #get/check information from AJAX request
        post_info = request.POST
        geoserver_id = post_info.get('geoserver_id')
    
        if int(geoserver_id) != 1:
            #initialize session
            session = SettingsSessionMaker()
            try:
                #delete geoserver
                try:
                    geoserver = session.query(Geoserver).get(geoserver_id)
                except ObjectDeletedError:
                    session.close()
                    return JsonResponse({ 'error': "The geoserver to delete does not exist." })
                session.delete(geoserver)
                session.commit()
                session.close()
            except IntegrityError:
                session.close()
                return JsonResponse({ 'error': "This geoserver is connected with a watershed! Must remove connection to delete." })
            return JsonResponse({ 'success': "Geoserver sucessfully deleted!" })
        return JsonResponse({ 'error': "Cannot change this geoserver." })
    return JsonResponse({ 'error': "A problem with your request exists." })

@user_passes_test(user_permission_test)
def geoserver_update(request):
    """
    Controller for updating a geoserver.
    """
    if request.is_ajax() and request.method == 'POST':
        #get/check information from AJAX request
        post_info = request.POST
        geoserver_id = post_info.get('geoserver_id')
        geoserver_name = post_info.get('geoserver_name')
        geoserver_url = post_info.get('geoserver_url')
        geoserver_username = post_info.get('geoserver_username')
        geoserver_password = post_info.get('geoserver_password')
        #check data
        if not geoserver_id or not geoserver_name or not geoserver_url or not \
            geoserver_username or not geoserver_password:
            return JsonResponse({ 'error': "Missing input data." })
        #make sure id is id
        try:
            int(geoserver_id)
        except ValueError:
            return JsonResponse({'error' : 'Geoserver id is faulty.'})
        #clean url
        geoserver_url = geoserver_url.strip()
        if geoserver_url.endswith('/'):
            geoserver_url = geoserver_url[:-1]

        if int(geoserver_id) != 1:
            #initialize session
            session = SettingsSessionMaker()
            #check to see if duplicate exists
            num_similar_geoservers  = session.query(Geoserver) \
              .filter(
                  or_(Geoserver.name == geoserver_name,
                      Geoserver.url == geoserver_url)
                      ) \
              .filter(Geoserver.id != geoserver_id) \
              .count()
              
            if(num_similar_geoservers > 0):
                session.close()
                return JsonResponse({ 'error': "A geoserver with the same name or url exists." })
            #update geoserver
            try:
                geoserver = session.query(Geoserver).get(geoserver_id)
            except ObjectDeletedError:
                session.close()
                return JsonResponse({ 'error': "The geoserver to update does not exist." })
            
            geoserver.name = geoserver_name.strip()
            geoserver.url = geoserver_url.strip()    
            geoserver.username = geoserver_username.strip()    
            geoserver.password = geoserver_password.strip()    
            session.commit()
            session.close()
            return JsonResponse({ 'success': "Geoserver sucessfully updated!" })
        return JsonResponse({ 'error': "Cannot change this geoserver." })
    return JsonResponse({ 'error': "A problem with your request exists." })
    
def get_avaialable_dates(request):
    """""
    Finds a list of directories with valid data and returns dates in select2 format
    """""
    if request.is_ajax() and request.method == 'GET':
        #Query DB for path to rapid output
        session = SettingsSessionMaker()
        main_settings  = session.query(MainSettings).order_by(MainSettings.id).first()
        session.close()

        path_to_rapid_output = main_settings.local_prediction_files
        if not os.path.exists(path_to_rapid_output):
            return JsonResponse({'error' : 'Location of RAPID output files faulty. Please check settings.'})    
    
        #get/check information from AJAX request
        get_info = request.GET
        watershed_name = format_name(get_info['watershed_name']) if 'watershed_name' in get_info else None
        subbasin_name = format_name(get_info['subbasin_name']) if 'subbasin_name' in get_info else None
        reach_id = get_info.get('reach_id')
        if not reach_id or not watershed_name or not subbasin_name:
            return JsonResponse({'error' : 'AJAX request input faulty'})
    
        #find/check current output datasets    
        path_to_watershed_files = os.path.join(path_to_rapid_output, watershed_name)

        if not os.path.exists(path_to_watershed_files):
            return JsonResponse({'error' : 'Forecast for %s (%s) not found.' % (watershed_name, subbasin_name) })    
       
        directories = sorted([d for d in os.listdir(path_to_watershed_files) \
                            if os.path.isdir(os.path.join(path_to_watershed_files, d))],
                             reverse=True)
        output_directories = []
        directory_count = 0
        for directory in directories:
            date = datetime.datetime.strptime(directory.split(".")[0],"%Y%m%d")
            time = directory.split(".")[-1]
            path_to_files = os.path.join(path_to_watershed_files, directory)
            if os.path.exists(path_to_files):
                basin_files = glob(os.path.join(path_to_files,
                                                "*"+subbasin_name+"*.nc"))
                #only add directory to the list if valid                                    
                if len(basin_files) >0: # and get_reach_index(reach_id, basin_files):
                    hour = int(time)/100
                    output_directories.append({
                        'id' : directory, 
                        'text' : str(date + datetime.timedelta(0,int(hour)*60*60))
                    })
                    directory_count += 1
                #limit number of directories
                if(directory_count>64):
                    break                
        if len(output_directories)>0:
            return JsonResponse({     
                        "success" : "Data analysis complete!",
                        "output_directories" : output_directories,                   
                    })
        else:
            return JsonResponse({'error' : 'Recent forecasts for reach with id: %s not found.' % reach_id})    
     
def get_hydrograph(request):
    """""
    Plots all 52 ensembles with min, max, avg
    """""
    if request.method == 'GET':
        #Query DB for path to rapid output
        session = SettingsSessionMaker()
        main_settings  = session.query(MainSettings).order_by(MainSettings.id).first()
        session.close()
        path_to_rapid_output = main_settings.local_prediction_files
        if not os.path.exists(path_to_rapid_output):
            return JsonResponse({'error' : 'Location of RAPID output files faulty. Please check settings.'})    
    
        #get/check information from AJAX request
        get_info = request.GET
        watershed_name = format_name(get_info['watershed_name']) if 'watershed_name' in get_info else None
        subbasin_name = format_name(get_info['subbasin_name']) if 'subbasin_name' in get_info else None
        reach_id = get_info.get('reach_id')
        guess_index = get_info.get('guess_index')
        start_folder = get_info.get('start_folder')
        if not reach_id or not watershed_name or not subbasin_name or not start_folder:
            return JsonResponse({'error' : 'AJAX request input faulty.'})
    
        #find/check current output datasets    
        path_to_output_files = os.path.join(path_to_rapid_output, watershed_name)
        basin_files, start_date = find_most_current_files(path_to_output_files,subbasin_name,start_folder)
        if not basin_files or not start_date:
            return JsonResponse({'error' : 'Forecast for %s (%s) not found.' % (watershed_name, subbasin_name)})
    
        #get/check the index of the reach
        reach_index = get_reach_index(reach_id, guess_index, basin_files)
        if not reach_index:
            return JsonResponse({'error' : 'Reach with id: ' + str(reach_id) + ' not found.'})

        #get information from datasets
        all_data_first_half = []
        all_data_second_half = []
        high_res_data = []
        hrrr_data = []
        erfp_time = []
        hrrr_time = []
        for in_nc in basin_files:
            try:
                index_str = os.path.basename(in_nc)[:-3].split("_")[-1]
                try:
                    #ECMWF Ensembles
                    index = int(index_str)
                    data_nc = NET.Dataset(in_nc, mode="r")
                    dataValues = data_nc.variables['Qout'][:,reach_index]
                    data_nc.close()
                    if (len(dataValues)>len(erfp_time)):
                        erfp_time = []
                        for i in range(0,len(dataValues)):
                            next_time = int((start_date+datetime.timedelta(0,i*6*60*60)) \
                                            .strftime('%s'))*1000
                            erfp_time.append(next_time)
                    all_data_first_half.append(dataValues[:40].clip(min=0))
                    if(index < 52):
                        all_data_second_half.append(dataValues[40:].clip(min=0))
                    if(index == 52):
                        high_res_data = dataValues
                except ValueError:
                    if index_str.lower() == "hrrr":
                        #WRF-Hydro Ensemble
                        data_nc = NET.Dataset(in_nc, mode="r")
                        #convert data from cfs to cms
                        hrrr_data = data_nc.variables['Qout'][:,reach_index] * 0.0283168 
                        data_nc.close()
                        if not hrrr_time:
                            for i in range(0,len(hrrr_data)):
                                next_time = int((start_date+datetime.timedelta(0,i*1*60*60)) \
                                                .strftime('%s'))*1000
                                hrrr_time.append(next_time)
                    pass
            except Exception, e:
                print e
                pass
        return_data = {}
        if erfp_time:
            #perform analysis on datasets
            all_data_first = np.array(all_data_first_half, dtype=np.float64)
            all_data_second = np.array(all_data_second_half, dtype=np.float64)
            #get mean
            mean_data_first = np.mean(all_data_first, axis=0)
            mean_data_second = np.mean(all_data_second, axis=0)
            mean_series = np.concatenate([mean_data_first,mean_data_second])
            #get std dev
            std_dev_first = np.std(all_data_first, axis=0)
            std_dev_second = np.std(all_data_second, axis=0)
            std_dev = np.concatenate([std_dev_first,std_dev_second])
            #get max
            max_data_first = np.amax(all_data_first, axis=0)
            max_data_second = np.amax(all_data_second, axis=0)
            max_series = np.concatenate([max_data_first,max_data_second])
            #get min
            min_data_first = np.amin(all_data_first, axis=0)
            min_data_second = np.amin(all_data_second, axis=0)
            min_series = np.concatenate([min_data_first,min_data_second])
            #mean plus std
            mean_plus_std = mean_series + std_dev
            #mean minus std
            mean_mins_std = (mean_series - std_dev).clip(min=0)
            #return results of analysis
            return_data["max"] = zip(erfp_time, max_series.tolist())
            return_data["min"] = zip(erfp_time, min_series.tolist())
            return_data["mean"] = zip(erfp_time, mean_series.tolist())
            return_data["mean_plus_std"] = zip(erfp_time, mean_plus_std.tolist())
            return_data["mean_minus_std"] = zip(erfp_time, mean_mins_std.tolist())
            if len(high_res_data) > 0:
                return_data["high_res"] = zip(erfp_time,high_res_data.tolist())
        if hrrr_time:
            return_data["hrrr_data"] = zip(hrrr_time,hrrr_data.tolist())
        return_data["success"] = "Data analysis complete!"
        return JsonResponse(return_data)
                    
@user_passes_test(user_permission_test)
def settings_update(request):
    """
    Controller for updating the settings.
    """
    if request.is_ajax() and request.method == 'POST':
        #get/check information from AJAX request
        post_info = request.POST
        base_layer_id = post_info.get('base_layer_id')
        api_key = post_info.get('api_key')
        local_prediction_files = post_info.get('ecmwf_rapid_location')

        #update cron jobs
        try:
            morning_hour = int(post_info.get('morning_hour'))
            evening_hour = int(post_info.get('evening_hour'))
            cron_manager = CronTab(user=getuser())
            cron_manager.remove_all(comment="erfp-dataset-download")
            cron_command = get_cron_command()
            if cron_command:
                #add new times   
                cron_job_morning = cron_manager.new(command=cron_command, 
                                           comment="erfp-dataset-download")
                cron_job_morning.minute.on(0)
                cron_job_morning.hour.on(morning_hour)
                cron_job_evening = cron_manager.new(command=cron_command, 
                                           comment="erfp-dataset-download")
                cron_job_evening.minute.on(0)
                cron_job_evening.hour.on(evening_hour)
            else:
               JsonResponse({ 'error': "Location of virtual environment not found. No changes made." }) 
       
            #writes content to crontab
            cron_manager.write()
        except (TypeError, ValueError):
            return JsonResponse({ 'error': "Error with unput for time." })
        except Exception:
            return JsonResponse({ 'error': "CRON setup error." })

        #initialize session
        session = SettingsSessionMaker()
        #update main settings
        main_settings  = session.query(MainSettings).order_by(MainSettings.id).first()
        main_settings.base_layer_id = base_layer_id
        main_settings.local_prediction_files = local_prediction_files    
        main_settings.base_layer.api_key = api_key
        main_settings.morning_hour = morning_hour
        main_settings.evening_hour = evening_hour
        session.commit()
        session.close()

        return JsonResponse({ 'success': "Settings Sucessfully Updated!" })

@user_passes_test(user_permission_test)    
def watershed_add(request):
    """
    Controller for ading a watershed.
    """
    if request.is_ajax() and request.method == 'POST':
        post_info = request.POST
        #get/check information from AJAX request
        watershed_name = post_info.get('watershed_name')
        subbasin_name = post_info.get('subbasin_name')
        folder_name = format_name(watershed_name) if watershed_name else None
        file_name = format_name(subbasin_name) if subbasin_name else None
        data_store_id = post_info.get('data_store_id')
        geoserver_id = post_info.get('geoserver_id')
        #REQUIRED TO HAVE drainage_line from one of these
        #layer names
        geoserver_drainage_line_layer = post_info.get('geoserver_drainage_line_layer')
        geoserver_catchment_layer = post_info.get('geoserver_catchment_layer')
        geoserver_gage_layer = post_info.get('geoserver_gage_layer')
        kml_drainage_line_layer = ""
        kml_catchment_layer = ""
        kml_gage_layer = ""
        #shape files
        drainage_line_shp_file = request.FILES.getlist('drainage_line_shp_file')
        catchment_shp_file = request.FILES.getlist('catchment_shp_file')
        gage_shp_file = request.FILES.getlist('gage_shp_file')
        #kml files
        drainage_line_kml_file = request.FILES.get('drainage_line_kml_file')
        catchment_kml_file = request.FILES.get('catchment_kml_file')
        gage_kml_file = request.FILES.get('gage_kml_file')
        
        geoserver_drainage_line_uploaded = False
        geoserver_catchment_uploaded = False
        geoserver_gage_uploaded = False
        
        #CHECK DATA
        #make sure information exists 
        if not watershed_name or not subbasin_name or not data_store_id \
            or not geoserver_id or not folder_name or not file_name:
            return JsonResponse({'error' : 'Request input missing data.'})
        #make sure ids are ids
        try:
            int(data_store_id)
            int(geoserver_id)
        except ValueError:
            return JsonResponse({'error' : 'One or more ids are faulty.'})
        #make sure one layer exists
        if(int(geoserver_id)==1):
            if not drainage_line_kml_file:
                return JsonResponse({'error' : 'Missing drainage line KML file.'})
        else:
            if not drainage_line_shp_file and not geoserver_drainage_line_layer:
                return JsonResponse({'error' : 'Missing geoserver drainage line.'})
            #check shapefiles
            if drainage_line_shp_file:
                missing_extenstions = check_shapefile_input_files(drainage_line_shp_file)
                if missing_extenstions:
                    return JsonResponse({'error' : 'Missing geoserver drainage line files with extensions %s.' % \
                                        (", ".join(missing_extenstions)) })
            if catchment_shp_file:
                missing_extenstions = check_shapefile_input_files(catchment_shp_file)
                if missing_extenstions:
                    return JsonResponse({'error' : 'Missing geoserver catchment files with extensions %s.' % \
                                        (", ".join(missing_extenstions)) })
            if gage_shp_file:
                missing_extenstions = check_shapefile_input_files(gage_shp_file)
                if missing_extenstions:
                    return JsonResponse({'error' : 'Missing geoserver gage files with extensions %s.' % \
                                        (", ".join(missing_extenstions)) })
        #initialize session
        session = SettingsSessionMaker()
        #check to see if duplicate exists
        num_similar_watersheds  = session.query(Watershed) \
            .filter(Watershed.folder_name == folder_name) \
            .filter(Watershed.file_name == file_name) \
            .count()
        if(num_similar_watersheds > 0):
            session.close()
            return JsonResponse({ 'error': "A watershed with the same name exists." })

        #COMMIT
        #upload files if files present
        if(int(geoserver_id) == 1):
            #LOCAL UPLOAD
            if drainage_line_kml_file:
                kml_file_location = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                 'public','kml',folder_name)
                kml_drainage_line_layer = "%s-drainage_line.kml" % file_name
                handle_uploaded_file(drainage_line_kml_file,
                                     kml_file_location, kml_drainage_line_layer)
                #upload catchment kml if exists
                if catchment_kml_file:
                    kml_catchment_layer = "%s-catchment.kml" % file_name
                    handle_uploaded_file(catchment_kml_file,kml_file_location, 
                                         kml_catchment_layer)
                #uploade gage kml if exists
                if gage_kml_file:
                    kml_gage_layer = "%s-gage.kml" % file_name
                    handle_uploaded_file(gage_kml_file,kml_file_location, 
                                         kml_gage_layer)
            else:
                session.close()
                return JsonResponse({ 'error': "File Upload Failed! Please check your KML files." })
        elif drainage_line_shp_file:
            #GEOSERVER UPLOAD
            """
            engine = GeoServerSpatialDatasetEngine(endpoint="%s/rest" % watershed.geoserver.url, 
                                       username=watershed.geoserver.username,
                                       password=watershed.geoserver.password)
            """
            resource_workspace = 'erfp'
            """
            engine.create_workspace(workspace_id=resource_workspace, uri='tethys.ci-water.org')
            """
            #TODO: REMOVE PAST GEOSERVER FILES ASSOCIATED WITH WATERSHED IF UPLOADED
            resource_name = "%s-%s-%s" % (folder_name, file_name, 'drainage_line')
            geoserver_drainage_line_layer = '{0}:{1}'.format(resource_workspace, resource_name)
            """        
            # Do create shapefile
            engine.create_shapefile_resource(geoserver_drainage_line_layer, shapefile_base=drainage_line_shp_file,
                                                  overwrite=True)
            """
            geoserver_drainage_line_uploaded = True
            if catchment_shp_file:
                #upload file
                resource_name = "%s-%s-%s" % (folder_name, file_name, 'catchment')
                geoserver_catchment_layer = '{0}:{1}'.format(resource_workspace, resource_name)
                """
                # Do create shapefile
                engine.create_shapefile_resource(geoserver_catchment_layer, shapefile_base=catchment_shp_file,
                                                      overwrite=True)
                """
                geoserver_catchment_uploaded = True
            if gage_shp_file:
                #upload file
                resource_name = "%s-%s-%s" % (folder_name, file_name, 'gage')
                geoserver_gage_layer = '{0}:{1}'.format(resource_workspace, resource_name)
                """
                # Do create shapefile
                engine.create_shapefile_resource(geoserver_gage_layer, shapefile_base=gage_shp_file,
                                                      overwrite=True)
                """
                geoserver_gage_uploaded = True
            #TODO: make geoserver layer upload function

        #add watershed
        watershed = Watershed(watershed_name.strip(), subbasin_name.strip(), folder_name.strip(), 
                              file_name.strip(), data_store_id, geoserver_id, 
                              geoserver_drainage_line_layer.strip(),
                              geoserver_catchment_layer.strip(),
                              geoserver_gage_layer.strip(),
                              geoserver_drainage_line_uploaded,
                              geoserver_catchment_uploaded,
                              geoserver_gage_uploaded,
                              kml_drainage_line_layer.strip(),
                              kml_catchment_layer.strip(),
                              kml_gage_layer.strip()
                              )
        session.add(watershed)
        session.commit()
        session.close()

        return JsonResponse({ 'success': "Watershed Sucessfully Added!" })

    return JsonResponse({ 'error': "A problem with your request exists." })

@user_passes_test(user_permission_test)
def watershed_delete(request):
    """
    Controller for deleting a watershed.
    """
    if request.is_ajax() and request.method == 'POST':
        #get/check information from AJAX request
        post_info = request.POST
        watershed_id = post_info.get('watershed_id')
        #make sure ids are ids
        try:
            int(watershed_id)
        except ValueError:
            return JsonResponse({'error' : 'Watershed id is faulty.'})    
        
        if watershed_id:
            #initialize session
            session = SettingsSessionMaker()
            #get watershed to delete
            try:
                watershed  = session.query(Watershed).get(watershed_id)
            except ObjectDeletedError:
                return JsonResponse({ 'error': "The watershed to delete does not exist." })
            main_settings  = session.query(MainSettings).order_by(MainSettings.id).first()
            #remove watershed kml and prediction files
            delete_old_watershed_files(watershed, main_settings.local_prediction_files)
            #TODO: remove geoserver files?
            
            #delete watershed from database
            session.delete(watershed)
            session.commit()
            session.close()

            return JsonResponse({ 'success': "Watershed sucessfully deleted!" })
        return JsonResponse({ 'error': "Cannot delete this watershed." })
    return JsonResponse({ 'error': "A problem with your request exists." })
    
@user_passes_test(user_permission_test)
def watershed_update(request):
    """
    Controller for updating a watershed.
    """
    if request.is_ajax() and request.method == 'POST':
        post_info = request.POST
        #get/check information from AJAX request
        watershed_id = post_info.get('watershed_id')
        watershed_name = post_info.get('watershed_name')
        subbasin_name = post_info.get('subbasin_name')
        folder_name = format_name(watershed_name) if watershed_name else None
        file_name = format_name(subbasin_name) if subbasin_name else None
        data_store_id = post_info.get('data_store_id')
        geoserver_id = post_info.get('geoserver_id')
        #REQUIRED TO HAVE drainage_line from one of these
        #layer names
        geoserver_drainage_line_layer = post_info.get('geoserver_drainage_line_layer')
        geoserver_catchment_layer = post_info.get('geoserver_catchment_layer')
        geoserver_gage_layer = post_info.get('geoserver_gage_layer')
        kml_drainage_line_layer = post_info.get('kml_drainage_line_layer')
        kml_catchment_layer = post_info.get('kml_catchment_layer')
        kml_gage_layer = post_info.get('kml_gage_layer')
        #shape files
        drainage_line_shp_file = request.FILES.getlist('drainage_line_shp_file')
        catchment_shp_file = request.FILES.getlist('catchment_shp_file')
        gage_shp_file = request.FILES.getlist('gage_shp_file')
        #kml files
        drainage_line_kml_file = request.FILES.get('drainage_line_kml_file')
        catchment_kml_file = request.FILES.get('catchment_kml_file')
        gage_kml_file = request.FILES.get('gage_kml_file')
        
        geoserver_drainage_line_uploaded = False
        geoserver_catchment_uploaded = False
        geoserver_gage_uploaded = False

        #CHECK INPUT
        #check if variables exist
        if not watershed_id or not watershed_name or not subbasin_name or not data_store_id \
            or not geoserver_id or not folder_name or not file_name:
            return JsonResponse({'error' : 'Request input missing data.'})
        #make sure ids are ids
        try:
            int(watershed_id)
            int(data_store_id)
            int(geoserver_id)
        except ValueError:
            return JsonResponse({'error' : 'One or more ids are faulty.'})
        #make sure one layer exists
        if(int(geoserver_id)==1):
            if not drainage_line_kml_file and not kml_drainage_line_layer:
                return JsonResponse({'error' : 'Missing drainage line KML file.'})
        else:
            if not drainage_line_shp_file and not geoserver_drainage_line_layer:
                return JsonResponse({'error' : 'Missing geoserver drainage line.'})
            #check shapefiles
            if drainage_line_shp_file:
                missing_extenstions = check_shapefile_input_files(drainage_line_shp_file)
                if missing_extenstions:
                    return JsonResponse({'error' : 'Missing geoserver drainage line files with extensions %s.' % \
                                        (", ".join(missing_extenstions)) })
            if catchment_shp_file:
                missing_extenstions = check_shapefile_input_files(catchment_shp_file)
                if missing_extenstions:
                    return JsonResponse({'error' : 'Missing geoserver catchment files with extensions %s.' % \
                                        (", ".join(missing_extenstions)) })
            if gage_shp_file:
                missing_extenstions = check_shapefile_input_files(gage_shp_file)
                if missing_extenstions:
                    return JsonResponse({'error' : 'Missing geoserver gage files with extensions %s.' % \
                                        (", ".join(missing_extenstions)) })
            
        #COMMIT    
        #initialize session
        session = SettingsSessionMaker()
        #check to see if duplicate exists
        num_similar_watersheds  = session.query(Watershed) \
            .filter(Watershed.folder_name == folder_name) \
            .filter(Watershed.file_name == file_name) \
            .filter(Watershed.id != watershed_id) \
            .count()
        if(num_similar_watersheds > 0):
            return JsonResponse({ 'error': "A watershed with the same name exists." })
        
        #get desired watershed
        try:
            watershed  = session.query(Watershed).get(watershed_id)
        except ObjectDeletedError:
            return JsonResponse({ 'error': "The watershed to update does not exist." })
            
        main_settings  = session.query(MainSettings).order_by(MainSettings.id).first()

        #upload files to local server if ready
        if(int(geoserver_id) == 1):
            old_kml_file_location = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                 'public','kml',watershed.folder_name)
            new_kml_file_location = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                 'public','kml',folder_name)
            kml_drainage_line_layer = "%s-drainage_line.kml" % file_name
            kml_catchment_layer = "%s-catchment.kml" % file_name
            kml_gage_layer = "%s-gage.kml" % file_name
            #add new directory if it does not exist                
            try:
                os.mkdir(new_kml_file_location)
            except OSError:
                pass

            #if the name of watershed or subbasin is changed, update file name/location
            if(folder_name != watershed.folder_name or file_name != watershed.file_name):
                if(watershed.geoserver_id == 1):
                    #move drainage line kml
                    if watershed.kml_drainage_line_layer:
                        try:
                            move(os.path.join(old_kml_file_location, watershed.kml_drainage_line_layer),
                                 os.path.join(new_kml_file_location, kml_drainage_line_layer))
                        except IOError:
                            pass
                    #move catchment kml
                    if watershed.kml_catchment_layer:
                        try:
                            move(os.path.join(old_kml_file_location, watershed.kml_catchment_layer),
                                 os.path.join(new_kml_file_location, kml_catchment_layer))
                        except IOError:
                            pass
                    #move gage kml
                    if watershed.kml_gage_layer:
                        try:
                            move(os.path.join(old_kml_file_location, watershed.kml_gage_layer),
                                 os.path.join(new_kml_file_location, kml_gage_layer))
                        except IOError:
                            pass
                    #remove old directory if exists
                    try:
                        os.rmdir(old_kml_file_location)
                    except OSError:
                        pass
                #remove local prediction files
                delete_old_watershed_prediction_files(watershed.folder_name, 
                                                      main_settings.local_prediction_files)
            #upload new files if they exist
            if(drainage_line_kml_file):
                handle_uploaded_file(drainage_line_kml_file, new_kml_file_location, kml_drainage_line_layer)
            if(catchment_kml_file):
                handle_uploaded_file(catchment_kml_file, new_kml_file_location, kml_catchment_layer)
            if(gage_kml_file):
                handle_uploaded_file(gage_kml_file, new_kml_file_location, kml_gage_layer)
        else:
            #remove old kml files           
            delete_old_watershed_kml_files(watershed)

            if(folder_name != watershed.folder_name or file_name != watershed.file_name):
                #remove old prediction files if not on local server
                delete_old_watershed_prediction_files(watershed.folder_name, 
                                                      main_settings.local_prediction_files)
            #TODO: GEOSERVER UPLOAD
            """
            engine = GeoServerSpatialDatasetEngine(endpoint="%s/rest" % watershed.geoserver.url, 
                                       username=watershed.geoserver.username,
                                       password=watershed.geoserver.password)
            """
            resource_workspace = 'erfp'
            """
            engine.create_workspace(workspace_id=resource_workspace, uri='tethys.ci-water.org')
            """
            if drainage_line_shp_file:
                #TODO: remove old geoserver layer if uploaded
                resource_name = "%s-%s-%s" % (folder_name, file_name, 'drainage_line')
                geoserver_drainage_line_layer = '{0}:{1}'.format(resource_workspace, resource_name)
                """        
                # Do create shapefile
                engine.create_shapefile_resource(geoserver_drainage_line_layer, shapefile_base=drainage_line_shp_file,
                                                      overwrite=True)
                """
                geoserver_drainage_line_uploaded = True
            if catchment_shp_file:
                #TODO: remove old geoserver layer if uploaded
                resource_name = "%s-%s-%s" % (folder_name, file_name, 'catchment')
                geoserver_catchment_layer = '{0}:{1}'.format(resource_workspace, resource_name)
                """
                # Do create shapefile
                engine.create_shapefile_resource(geoserver_catchment_layer, shapefile_base=catchment_shp_file,
                                                      overwrite=True)
                """
                geoserver_catchment_uploaded = True
            if gage_shp_file:
                #TODO: remove old geoserver layer if uploaded
                resource_name = "%s-%s-%s" % (folder_name, file_name, 'gage')
                geoserver_gage_layer = '{0}:{1}'.format(resource_workspace, resource_name)
                """
                # Do create shapefile
                engine.create_shapefile_resource(geoserver_gage_layer, shapefile_base=gage_shp_file,
                                                      overwrite=True)
                """
                geoserver_gage_uploaded = True
            
        #change watershed attributes
        watershed.watershed_name = watershed_name.strip()
        watershed.subbasin_name = subbasin_name.strip()
        watershed.folder_name = folder_name.strip()
        watershed.file_name = file_name.strip()
        watershed.data_store_id = data_store_id
        watershed.geoserver_id = geoserver_id
        watershed.geoserver_drainage_line_layer = geoserver_drainage_line_layer.strip()
        watershed.geoserver_catchment_layer = geoserver_catchment_layer.strip()
        watershed.geoserver_gage_layer = geoserver_gage_layer.strip()
        watershed.geoserver_drainage_line_uploaded = geoserver_drainage_line_uploaded
        watershed.geoserver_catchment_uploaded = geoserver_catchment_uploaded
        watershed.geoserver_gage_uploaded = geoserver_gage_uploaded
        watershed.kml_drainage_line_layer = kml_drainage_line_layer.strip()
        watershed.kml_catchment_layer = kml_catchment_layer.strip()
        watershed.kml_gage_layer = kml_gage_layer.strip()
        
        #update database
        session.commit()
        session.close()

        return JsonResponse({ 'success': "Watershed sucessfully updated!" })

    return JsonResponse({ 'error': "A problem with your request exists." })

@user_passes_test(user_permission_test)
def watershed_group_add(request):
    """
    Controller for adding a watershed_group.
    """
    if request.is_ajax() and request.method == 'POST':
        #get/check information from AJAX request
        post_info = request.POST
        watershed_group_name = post_info.get('watershed_group_name')
        watershed_group_watershed_ids = post_info.getlist('watershed_group_watershed_ids[]')
        if not watershed_group_name or not watershed_group_watershed_ids:
            return JsonResponse({ 'error': 'AJAX request input faulty' })
        #initialize session
        session = SettingsSessionMaker()
        
        #check to see if duplicate exists
        num_similar_watershed_groups  = session.query(WatershedGroup) \
            .filter(WatershedGroup.name == watershed_group_name) \
            .count()
        if(num_similar_watershed_groups > 0):
            return JsonResponse({ 'error': "A watershed group with the same name." })
            
        #add Watershed Group
        group = WatershedGroup(watershed_group_name)

        #update watersheds
        watersheds  = session.query(Watershed) \
                .filter(Watershed.id.in_(watershed_group_watershed_ids)) \
                .all()
        for watershed in watersheds:
            group.watersheds.append(watershed)
        session.add(group)
        session.commit()
        session.close()

        return JsonResponse({ 'success': "Watershed group sucessfully added!" })

    return JsonResponse({ 'error': "A problem with your request exists." })
    
@user_passes_test(user_permission_test)
def watershed_group_delete(request):
    """
    Controller for deleting a watershed group.
    """
    if request.is_ajax() and request.method == 'POST':
        #get/check information from AJAX request
        post_info = request.POST
        watershed_group_id = post_info.get('watershed_group_id')
    
        
        if watershed_group_id:
            #initialize session
            session = SettingsSessionMaker()
            #get watershed group to delete
            watershed_group  = session.query(WatershedGroup).get(watershed_group_id)
            
            #delete watershed group from database
            session.delete(watershed_group)
            session.commit()
            session.close()

            return JsonResponse({ 'success': "Watershed group sucessfully deleted!" })
        return JsonResponse({ 'error': "Cannot delete this watershed group." })
    return JsonResponse({ 'error': "A problem with your request exists." })
    
@user_passes_test(user_permission_test)
def watershed_group_update(request):
    """
    Controller for updating a watershed_group.
    """
    if request.is_ajax() and request.method == 'POST':
        #get/check information from AJAX request
        post_info = request.POST
        watershed_group_id = post_info.get('watershed_group_id')
        watershed_group_name = post_info.get('watershed_group_name')
        watershed_group_watershed_ids = post_info.getlist('watershed_group_watershed_ids[]')
        if watershed_group_id and watershed_group_name and watershed_group_watershed_ids:
            #initialize session
            session = SettingsSessionMaker()
            #check to see if duplicate exists
            num_similar_watershed_groups  = session.query(WatershedGroup) \
                .filter(WatershedGroup.name == watershed_group_name) \
                .filter(WatershedGroup.id != watershed_group_id) \
                .count()
            if(num_similar_watershed_groups > 0):
                return JsonResponse({ 'error': "A watershed group with the same name exists." })

            #get watershed group
            watershed_group  = session.query(WatershedGroup).get(watershed_group_id)
            watershed_group.name = watershed_group_name
            #find new watersheds
            new_watersheds  = session.query(Watershed) \
                    .filter(Watershed.id.in_(watershed_group_watershed_ids)) \
                    .all()

            #remove old watersheds
            for watershed in watershed_group.watersheds:
                if watershed not in new_watersheds:
                    watershed_group.watersheds.remove(watershed)
                
            #add new watersheds        
            for watershed in new_watersheds:
                if watershed not in watershed_group.watersheds:
                    watershed_group.watersheds.append(watershed)
            
            session.commit()
            session.close()
            return JsonResponse({ 'success': "Watershed group successfully updated." })
        return JsonResponse({ 'error': "Data missing for this watershed group." })
    return JsonResponse({ 'error': "A problem with your request exists." })