from tethys_apps.base import DatasetService, TethysAppBase, url_map_maker
from tethys_apps.base import PersistentStore

class ECMWFRAPIDFloodPredictionTool(TethysAppBase):
    """
    Tethys app class for ECMWF-RAPID Flood Prediction Tool.
    """

    name = 'ECMWF-RAPID Flood Prediction Tool'
    index = 'erfp_tool:home'
    icon = 'erfp_tool/images/icon.gif'
    package = 'erfp_tool'
    root_url = 'erfp-tool'
    color = '#34495e'
        
    def url_maps(self):
        """
        Add controllers
        """
        UrlMap = url_map_maker(self.root_url)

        url_maps = (UrlMap(name='home',
                           url='erfp-tool',
                           controller='erfp_tool.controllers.home'),
                    UrlMap(name='settings',
                           url='erfp-tool/settings',
                           controller='erfp_tool.controllers.settings'),
                    UrlMap(name='add-watershed',
                           url='erfp-tool/add-watershed',
                           controller='erfp_tool.controllers.add_watershed'),
                    UrlMap(name='add-geoserver',
                           url='erfp-tool/add-geoserver',
                           controller='erfp_tool.controllers.add_geoserver'),
                    UrlMap(name='add-data-store',
                           url='erfp-tool/add-data-store',
                           controller='erfp_tool.controllers.add_data_store'),
                    UrlMap(name='get_reach_statistical_hydrograph_ajax',
                           url='erfp-tool/get-hydrograph',
                           controller='erfp_tool.controllers.get_hydrograph_ajax'),
                    UrlMap(name='get_avaialable_dates_ajax',
                           url='erfp-tool/get-avaialable-dates',
                           controller='erfp_tool.controllers.get_avaialable_dates_ajax'),
                    UrlMap(name='update_settings_ajax',
                           url='erfp-tool/settings/update',
                           controller='erfp_tool.controllers.update_settings_ajax'),
                    UrlMap(name='add_data_store_ajax',
                           url='erfp-tool/add-data-store/submit',
                           controller='erfp_tool.controllers.add_data_store_ajax'),
                    UrlMap(name='add_watershed_ajax',
                           url='erfp-tool/add-watershed/submit',
                           controller='erfp_tool.controllers.add_watershed_ajax'),
                    UrlMap(name='add_geoserver_ajax',
                           url='erfp-tool/add-geoserver/submit',
                           controller='erfp_tool.controllers.add_geoserver_ajax'),
        )
        return url_maps
        
    def persistent_stores(self):
        """
        Add one or more persistent stores
        """
        stores = (PersistentStore(name='settings_db',
                                  initializer='init_stores:init_erfp_settings_db',
                                  spatial=False
                ),
        )

        return stores

    def dataset_services(self):
        """
        Add one or more dataset services
        """
        dataset_services = (DatasetService(name='ciwweb',
                                           type='ckan',
                                           endpoint='http://ciwweb.chpc.utah.edu/api/3/action',
                                           apikey='8dcc1b34-0e09-4ddc-8356-df4a24e5be87'
                                           ),
        )

        return dataset_services
