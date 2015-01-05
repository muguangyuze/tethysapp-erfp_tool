import datetime
from django.http import JsonResponse
from django.shortcuts import render
from glob import glob
import json
import netCDF4 as NET
import numpy as np
import os
from sqlalchemy import or_
#tethys imports
from tethys_datasets.engines import CkanDatasetEngine, HydroShareDatasetEngine

#local import
from .model import (BaseLayer, DataStore, DataStoreType, Geoserver, MainSettings,
                    SettingsSessionMaker, Watershed)
                    
from .forms import KMLUploadFileForm

def load_prediction_datasets():
    """
    Loads prediction datasets from data store
    """
    session = SettingsSessionMaker()
    for watershed in session.query(Watershed).all():
        #get data engine
        data_store = watershed.data_store
        data_engine = None
        if 'ckan' == data_store.data_store_type.code_name:
            data_engine = CkanDatasetEngine(endpoint=data_store.api_endpoint, apikey=data_store.api_key)
        elif 'hydroshare' == data_store.data_store_type.code_name:
            data_engine = HydroShareDatasetEngine(endpoint=data_store.api_endpoint, apikey=data_store.api_key)
        #load current datasets
        if data_engine:
            query = {
                "app": "erfp_tool", 
                "watershed":watershed.watershed_name, 
                "subbasin":watershed.subbasin_name,
                }
            dataset_id = data_engine.search_datasets(query)  
            dataset_url = data_engine.get_dataset(dataset_id)
            #download dataset with urllib2?
            #extract datasets
            #remove old datasets
                    
def format_name(string):
    """
    Formats watershed name for code
    """
    return string.strip().replace(" ", "_").lower()

def handle_uploaded_file(f, file_path, file_name):
    if not os.path.exists(file_path):
        os.mkdir(file_path)
        
    with open(os.path.join(file_path,file_name), 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
            
def create_navigation_string(layer_name, layer_id):
    """
    Formats navigation links for kml layer
    """
    return ('                    <li class="dropdown">'
           '                      <a href="" class="dropdown-toggle" data-toggle="dropdown" role="button" aria-expanded="false">%s<span class="caret"></span></a>' % layer_name + \
           '                      <ul id="%s" class="dropdown-menu" role="menu">' % layer_id + \
           '                        <li><a class="zoom-to-layer" href="#">Zoom To Layer</a></li>'
           '                        <li class="divider"></li>'
           '                        <li><p style="margin-left:20px;"><input class="visible" type="checkbox"> Visibility </p></li>'
           '                        <li><label style="margin-left:15px;">Opacity</label>'
           '                            <input style="margin-left:15px; width:80%;" class="opacity" type="range" min="0" max="1" step="0.01">'
           '                        </li>'
           '                      </ul>'
           '                    </li>')

def format_watershed_title(watershed, subbasin):
    """
    Formats title for watershed in navigation
    """
    max_length = 30
    watershed = watershed.strip().replace("_"," ").title()
    subbasin = subbasin.strip().replace("_"," ").title()
    watershed_length = len(watershed)
    if(watershed_length>max_length):
        return watershed[:max_length-1].strip() + "..."
    max_length -= watershed_length
    subbasin_length = len(subbasin)
    if(subbasin_length>max_length):
        return (watershed + " (" + subbasin[:max_length-3].strip() + " ...)")
    return (watershed + " (" + subbasin + ")")

def home(request):
    """
    Controller for the app home page.
    """
    ##find all kml files to add to page    
    kml_file_location = os.path.join(os.path.dirname(os.path.realpath(__file__)),'public','kml')
    kml_info = []
    watersheds = sorted(os.listdir(kml_file_location))
    #add kml urls to list and add their navigation items as well
    group_id = 0
    navigation_string = ""
    for watershed in watersheds:
        one_layer_found = False
        subbasin = ""
        file_path = os.path.join(kml_file_location, watershed)
        kml_urls = {'watershed':watershed}
        #prepare kml files    
        drainage_line_kml = glob(os.path.join(file_path, '*drainage_line.kml'))
        if(len(drainage_line_kml)>0):
            one_layer_found = True
            drainage_line_kml = os.path.basename(drainage_line_kml[0])
            kml_urls['drainage_line'] = '/static/erfp_tool/kml/%s/%s' % (watershed, drainage_line_kml)
            subbasin = drainage_line_kml.split("-")[0]
            kml_urls['subbasin'] = subbasin
        catchment_kml = glob(os.path.join(file_path, '*catchment.kml'))
        if(len(catchment_kml)>0):
            catchment_kml = os.path.basename(catchment_kml[0])
            one_layer_found = True
            kml_urls['catchment'] = '/static/erfp_tool/kml/%s/%s' % (watershed, catchment_kml)
            if not subbasin:
                subbasin = catchment_kml.split("-")[0]
                kml_urls['subbasin'] = subbasin

        #prepare navigation string
        navigation_string += ('            <li><div id="%s-control">' % watershed + \
        '                <div class="collapse-control">'
        '                    <a class="closeall" data-toggle="collapse" data-target="#%s-layers">' % watershed + \
        '%s</a>' % format_watershed_title(watershed,subbasin) + \
        '                </div>'
        '                <div id="%s-layers" class="collapse in">' % watershed + \
        '                    <ul>')

        if('drainage_line' in kml_urls):
            navigation_string += create_navigation_string("Drainage Line", "layer" + str(group_id)+str(0))
        if('catchment' in kml_urls):
            navigation_string += create_navigation_string("Catchment", "layer" + str(group_id)+str(1))
        if(not one_layer_found):
            navigation_string +=   '<li>ERROR: NO LAYERS FOUND!</li>'          
        navigation_string += ('                    </ul>'
        '                </div> <!-- div: %s-layers -->' % watershed + \
        '            </div></li>  <!-- div: %s-control -->' % watershed)
        kml_info.append(kml_urls)
        group_id += 1
        
    #get the base layer information
    session = SettingsSessionMaker()
    #Query DB for settings
    main_settings  = session.query(MainSettings).order_by(MainSettings.id).first()
    base_layer = main_settings.base_layer
    #Bing_apiKey = "AiW41aALyX4pDfE0jQG93WywSHLih1ihycHtwbaIPmtpZEOuw1iloQuuBmwJm5UA";
 
    base_layer_info = {
                        'name': base_layer.name,
                        'api_key':base_layer.api_key,
                        }
            
    context = {
                'kml_info' : json.dumps(kml_info),
                'map_navigation' : navigation_string,
                'base_layer_info' : json.dumps(base_layer_info),
              }

    return render(request, 'erfp_tool/home.html', context)

def get_reach_index(reach_id, basin_files):
    """
    Gets the index of the reach from the COMID 
    """
    data_nc = NET.Dataset(basin_files[0])
    com_ids = data_nc.variables['COMID'][:]
    try:
        reach_index = np.where(com_ids==int(reach_id))[0][0]
    except Exception as ex:
        print ex
        reach_index = None
        pass
    return reach_index
    
def get_avaialable_dates_ajax(request):
    """""
    Finds a list of directories with valid data and returns dates in select2 format
    """""
    if request.is_ajax() and request.method == 'GET':
        #Query DB for path to rapid output
        session = SettingsSessionMaker()
        main_settings  = session.query(MainSettings).order_by(MainSettings.id).first()
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
        directories = sorted(os.listdir(path_to_watershed_files), reverse=True)
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
                if len(basin_files) >0 and get_reach_index(reach_id, basin_files):
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
            return JsonResponse({'error' : 'Recent forecasts for reach with id: ' + str(reach_id) + ' not found.'})    
 

def find_most_current_files(path_to_watershed_files, basin_name,start_folder):
    """""
    Finds the current output from downscaled ECMWF forecasts
    """""
    if(start_folder=="most_recent"):
        directories = sorted(os.listdir(path_to_watershed_files), reverse=True)
    else:
        directories = [start_folder]
    for directory in directories:    
        date = datetime.datetime.strptime(directory.split(".")[0],"%Y%m%d")
        time = directory.split(".")[-1]
        path_to_files = os.path.join(path_to_watershed_files, directory)
        if os.path.exists(path_to_files):
            basin_files = glob(os.path.join(path_to_files,
                                            "*"+basin_name+"*.nc"))
            if len(basin_files) >0:
                hour = int(time)/100
                return basin_files, date + datetime.timedelta(0,int(hour)*60*60)
    #there are no files found
    return None, None
    
def get_hydrograph_ajax(request):
    """""
    Plots all 52 ensembles with min, max, avg
    """""
    if request.is_ajax() and request.method == 'GET':
        #Query DB for path to rapid output
        session = SettingsSessionMaker()
        main_settings  = session.query(MainSettings).order_by(MainSettings.id).first()
        path_to_rapid_output = main_settings.local_prediction_files
        if not os.path.exists(path_to_rapid_output):
            return JsonResponse({'error' : 'Location of RAPID output files faulty. Please check settings.'})    
    
        #get/check information from AJAX request
        get_info = request.GET
        watershed_name = format_name(get_info['watershed_name']) if 'watershed_name' in get_info else None
        subbasin_name = format_name(get_info['subbasin_name']) if 'subbasin_name' in get_info else None
        reach_id = get_info.get('reach_id')
        start_folder = get_info.get('start_folder')
        
        if not reach_id or not watershed_name or not subbasin_name:
            return JsonResponse({'error' : 'AJAX request input faulty.'})
    
        #find/check current output datasets    
        path_to_output_files = os.path.join(path_to_rapid_output, watershed_name)
        basin_files, start_date = find_most_current_files(path_to_output_files,subbasin_name,start_folder)
        if not basin_files or not start_date:
            return JsonResponse({'error' : 'Recent forecast not found.'})
    
        #get/check the index of the reach
        reach_index = get_reach_index(reach_id, basin_files)
        if not reach_index:
            return JsonResponse({'error' : 'Reach with id: ' + str(reach_id) + ' not found.'})    
    
        #get information from datasets
        all_data_first_half = []
        all_data_second_half = []
        time = []
        for in_nc in basin_files:
            index = int(os.path.basename(in_nc)[:-3].split("_")[-1])
            data_nc = NET.Dataset(in_nc)
            qout = data_nc.variables['Qout']
            dataValues = qout[:,reach_index]
            
            if (len(dataValues)>len(time)):
                time = []
                for i in range(0,len(dataValues)):
                    next_time = int((start_date+datetime.timedelta(0,i*6*60*60)).strftime('%s'))*1000
                    time.append(next_time)
            all_data_first_half.append(dataValues[:40].clip(min=0))
            if(index < 52):
                all_data_second_half.append(dataValues[40:].clip(min=0))
            data_nc.close()
    
        #perform analysis on datasets
        all_data_first = np.array(all_data_first_half)
        all_data_second = np.array(all_data_second_half)
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
        return JsonResponse({     
                        "success" : "Data analysis complete!",
                        "max" : zip(time, max_series.tolist()),
                        "min" : zip(time, min_series.tolist()),
                        "mean" : zip(time, mean_series.tolist()),
                        "mean_plus_std" : zip(time, mean_plus_std.tolist()),
                        "mean_minus_std" : zip(time, mean_mins_std.tolist()),
                       
                    })

def settings(request):
    """
    Controller for the app settings page.
    """
    
    session = SettingsSessionMaker()
    # Query DB for base layers
    base_layers = session.query(BaseLayer).all()
    base_layer_list = []
    base_layer_api_keys = {}
    for base_layer in base_layers:
        base_layer_list.append((base_layer.name, base_layer.id))
        base_layer_api_keys[base_layer.id] = base_layer.api_key

    #Query DB for settings
    main_settings  = session.query(MainSettings).order_by(MainSettings.id).first()
    
    
    base_layer_input = {
                'display_text': 'Select a Base Layer',
                'name': 'base-layer-input',
                'multiple': False,
                'options': base_layer_list,
                'initial': main_settings.base_layer.name
                }

    base_layer_api_key_input = {
                'display_text': 'Base Layer API Key',
                'name': 'api-key-input',
                'placeholder': 'e.g.: a1b2c3-d4e5d6-f7g8h9',
                'icon_append':'glyphicon glyphicon-lock',
                'initial': main_settings.base_layer.api_key
              }
              
    ecmwf_rapid_input = {
                'display_text': 'Server Folder Location of ECMWF-RAPID files',
                'name': 'ecmwf-rapid-location-input',
                'placeholder': 'e.g.: /home/username/work/rapid/output',
                'icon_append':'glyphicon glyphicon-folder-open',
                'initial': main_settings.local_prediction_files
              }
              
    submit_button = {'buttons': [
                                 {'display_text': 'Submit',
                                  'name': 'submit-changes-settings',
                                  'attributes': 'id=submit-changes-settings',
                                  'type': 'submit'
                                  }
                                ],
                 }
              
    context = {
                'base_layer_input': base_layer_input,
                'base_layer_api_key_input': base_layer_api_key_input,
                'ecmwf_rapid_input': ecmwf_rapid_input,
                'submit_button': submit_button,
                'base_layer_api_keys': json.dumps(base_layer_api_keys),
              }

    return render(request, 'erfp_tool/settings.html', context)

def update_settings_ajax(request):
    """
    Controller for updating the settings.
    """
    if request.is_ajax() and request.method == 'POST':
        #get/check information from AJAX request
        post_info = request.POST
        base_layer_id = post_info.get('base_layer_id')
        api_key = post_info.get('api_key')
        local_prediction_files = post_info.get('ecmwf_rapid_location')
        #initialize session
        session = SettingsSessionMaker()
        
        #update main settings
        main_settings  = session.query(MainSettings).order_by(MainSettings.id).first()
        main_settings.base_layer_id = base_layer_id
        main_settings.local_prediction_files = local_prediction_files    
        main_settings.base_layer.api_key = api_key
        session.commit()
        
        return JsonResponse({ 'success': "Settings Sucessfully Updated!" })


def add_watershed(request):
    """
    Controller for the app add_watershed page.
    """
    #initialize session
    session = SettingsSessionMaker()

    watershed_name_input = {
                'display_text': 'Watershed Name',
                'name': 'watershed-name-input',
                'placeholder': 'e.g.: magdalena',
                'icon_append':'glyphicon glyphicon-home',
              }
              
    subbasin_name_input = {
                'display_text': 'Subbasin Name',
                'name': 'subbasin-name-input',
                'placeholder': 'e.g.: el_banco',
                'icon_append':'glyphicon glyphicon-tree-deciduous',
              }
              
    # Query DB for data stores
    data_stores = session.query(DataStore).all()
    data_store_list = []
    for data_store in data_stores:
        data_store_list.append((data_store.name + " (" + data_store.api_endpoint + ")", data_store.id))

    if(len(data_store_list) <= 0):
        data_store_list.append(('None', -1))
    data_store_select = {
                'display_text': 'Select a Data Store',
                'name': 'data-store-select',
                'options': data_store_list,
                'placeholder': 'Select a Data Store',
                }          
              
    # Query DB for geoservers
    geoservers = session.query(Geoserver).all()
    geoserver_list = []
    for geoserver in geoservers:
        geoserver_list.append(( "%s (%s)" % (geoserver.name, geoserver.url), geoserver.id))

    geoserver_select= {
                'display_text': 'Select a Geoserver',
                'name': 'geoserver-select',
                'options': geoserver_list,
                'placeholder': 'Select a Geoserver',
                }
                
    geoserver_drainage_line_input = {
                'display_text': 'Geoserver Drainage Line KML Layer',
                'name': 'geoserver-drainage-line-input',
                'placeholder': 'e.g.: Streams:Developed',
                'icon_append':'glyphicon glyphicon-link',
                'attributes':'class=hidden',
              }
    geoserver_catchment_input = {
                'display_text': 'Geoserver Catchment KML Layer',
                'name': 'geoserver-catchment-input',
                'placeholder': 'e.g.: Streams:Developed',
                'icon_append':'glyphicon glyphicon-link',
                'attributes':'class=hidden',
              }
              

    add_button = {'buttons': [
                                 {'display_text': 'Add Watershed',
                                  'icon': 'glyphicon glyphicon-plus',
                                  'style': 'success',
                                  'name': 'submit-add-watershed',
                                  'attributes': 'id=submit-add-watershed',
                                  'type': 'submit'
                                  }
                                ],
                 }

    context = {
                'watershed_name_input': watershed_name_input,
                'subbasin_name_input': subbasin_name_input,
                'data_store_select': data_store_select,
                'geoserver_select': geoserver_select,
                'geoserver_drainage_line_input': geoserver_drainage_line_input,
                'geoserver_catchment_input': geoserver_catchment_input,
                'add_button': add_button,
              }

    return render(request, 'erfp_tool/add_watershed.html', context)
    
def add_watershed_ajax(request):
    """
    Controller for ading a watershed.
    """
    if request.is_ajax() and request.method == 'POST':
        post_info = request.POST
        #get/check information from AJAX request
        watershed_name = post_info.get('watershed_name')
        subbasin_name = post_info.get('subbasin_name')
        data_store_id = post_info.get('data_store_id')
        geoserver_id = post_info.get('geoserver_id')
        geoserver_drainage_line_layer = post_info.get('geoserver_drainage_line_layer')
        geoserver_catchment_layer = post_info.get('geoserver_catchment_layer')
        #file_form = KMLUploadFileForm(request.POST,request.FILES)
        #if file_form.is_valid():
        if(int(geoserver_id) == 1):
            if 'drainage_line_kml_file' in request.FILES and 'catchment_kml_file' in request.FILES:
                kml_file_location = os.path.join(os.path.dirname(os.path.realpath(__file__)),'public','kml',format_name(watershed_name))
                handle_uploaded_file(request.FILES.get('drainage_line_kml_file'),kml_file_location, format_name(subbasin_name) + "-drainage_line.kml")
                handle_uploaded_file(request.FILES.get('catchment_kml_file'),kml_file_location, format_name(subbasin_name) + "-catchment.kml")
            else:
                return JsonResponse({ 'error': "File Upload Failed! Please check your KML files." })

        #initialize session
        session = SettingsSessionMaker()
        
        #check to see if duplicate exists
        num_similar_watersheds  = session.query(Watershed) \
            .filter(Watershed.watershed_name == watershed_name) \
            .filter(Watershed.subbasin_name == subbasin_name) \
            .count()
        if(num_similar_watersheds > 0):
            return JsonResponse({ 'error': "A watershed with the same name exists." })
            
        #add Data Store
        session.add(Watershed(watershed_name, subbasin_name, data_store_id, geoserver_id, geoserver_drainage_line_layer, geoserver_catchment_layer))
        session.commit()
        
        return JsonResponse({ 'success': "Watershed Sucessfully Added!" })

    return JsonResponse({ 'error': "A problem with your request exists." })

def add_data_store(request):        
    """
    Controller for the app add_data_store page.
    """
    #initialize session
    session = SettingsSessionMaker()

    data_store_name_input = {
                'display_text': 'Data Store Server Name',
                'name': 'data-store-name-input',
                'placeholder': 'e.g.: My CKAN Server',
                'icon_append':'glyphicon glyphicon-tag',
              }

    # Query DB for data store types
    data_store_types = session.query(DataStoreType).all()
    data_store_type_list = []
    for data_store_type in data_store_types:
        data_store_type_list.append((data_store_type.human_readable_name, data_store_type.id))

    data_store_type_select_input = {
                'display_text': 'Data Store Type',
                'name': 'data-store-type-select',
                'options': data_store_type_list,
                'initial': data_store_type_list[0][0]
                }          

    data_store_endpoint_input = {
                'display_text': 'Data Store API Endpoint',
                'name': 'data-store-endpoint-input',
                'placeholder': 'e.g.: http://ciwweb.chpc.utah.edu/api/3/action',
                'icon_append':'glyphicon glyphicon-cloud-download',
              }

    data_store_api_key_input = {
                'display_text': 'Data Store API Key',
                'name': 'data-store-api-key-input',
                'placeholder': 'e.g.: a1b2c3-d4e5d6-f7g8h9',
                'icon_append':'glyphicon glyphicon-lock',
              }

    add_button = {'buttons': [
                                 {'display_text': 'Add Data Store',
                                  'icon': 'glyphicon glyphicon-plus',
                                  'style': 'success',
                                  'name': 'submit-add-data-store',
                                  'attributes': 'id=submit-add-data-store',
                                  'type': 'submit'
                                  }
                                ],
                 }

    context = {
                'data_store_name_input': data_store_name_input,
                'data_store_type_select_input': data_store_type_select_input,
                'data_store_endpoint_input': data_store_endpoint_input,
                'data_store_api_key_input': data_store_api_key_input,
                'add_button': add_button,
              }
    return render(request, 'erfp_tool/add_data_store.html', context)
    
def add_data_store_ajax(request):
    """
    Controller for adding a data store.
    """
    if request.is_ajax() and request.method == 'POST':
        #get/check information from AJAX request
        post_info = request.POST
        data_store_name = post_info.get('data_store_name')
        print data_store_name
        data_store_type_id = post_info.get('data_store_type_id')
        print data_store_type_id
        data_store_endpoint = post_info.get('data_store_endpoint')
        print data_store_endpoint
        data_store_api_key = post_info.get('data_store_api_key')
        print data_store_api_key
    
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
        
        return JsonResponse({ 'success': "Data Store Sucessfully Added!" })

    return JsonResponse({ 'error': "A problem with your request exists." })

def manage_data_stores(request):        
    """
    Controller for the app add_data_store page.
    """
    #initialize session
    session = SettingsSessionMaker()

    # Query DB for data store types
    data_stores = session.query(DataStore).all()

    context = {
                'data_stores': data_stores,
              }
    return render(request, 'erfp_tool/manage_data_stores.html', context)
    
def add_geoserver(request):        
    """
    Controller for the app add_geoserver page.
    """
    geoserver_name_input = {
        'display_text': 'Geoserver Name',
        'name': 'geoserver-name-input',
        'placeholder': 'e.g.: My Geoserver',
        'icon_append':'glyphicon glyphicon-tag',
        }

    geoserver_url_input = {
        'display_text': 'Geoserver Url',
        'name': 'geoserver-url-input',
        'placeholder': 'e.g.: http://felek.cns.umass.edu:8080/geoserver/wms',
        'icon_append':'glyphicon glyphicon-cloud-download',
        }
              
 
    add_button = {'buttons': [
                                 {'display_text': 'Add Geoserver',
                                  'icon': 'glyphicon glyphicon-plus',
                                  'style': 'success',
                                  'name': 'submit-add-geoserver',
                                  'attributes': 'id=submit-add-geoserver',
                                  'type': 'submit'
                                  }
                                ],
                 }

    context = {
                'geoserver_name_input': geoserver_name_input,
                'geoserver_url_input': geoserver_url_input,
                'add_button': add_button,
              }
    return render(request, 'erfp_tool/add_geoserver.html', context)
 
def add_geoserver_ajax(request):
    """
    Controller for ading a geoserver.
    """
    if request.is_ajax() and request.method == 'POST':
        print "POST"
        #get/check information from AJAX request
        post_info = request.POST
        geoserver_name = post_info.get('geoserver_name')
        geoserver_url = post_info.get('geoserver_url')
    
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
            return JsonResponse({ 'error': "A geoserver with the same name or url exists." })
            
        #add Data Store
        session.add(Geoserver(geoserver_name, geoserver_url))
        session.commit()
        return JsonResponse({ 'success': "Geoserver Sucessfully Added!" })

    return JsonResponse({ 'error': "A problem with your request exists." })

