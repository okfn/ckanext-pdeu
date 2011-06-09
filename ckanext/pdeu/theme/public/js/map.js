var CKAN = CKAN || {};
CKAN.EuroMap = function($){

    var featuresLayer = null;

    var selectControl = null;
    var selectedFeature = null;
    
    var guessBestAnchorPoint = function(geometry){
        if (geometry.components.length == 1){
            return geometry.getBounds().getCenterLonLat();
        } else {
            var areas = [];
            var largest_area, largest_component;
            for (var i = 0; i < geometry.components.length;i++){
                area = geometry.components[i].getArea();
                if (!largest_area || largest_area < area){
                    largest_area = area;
                    largest_component = geometry.components[i]
                }
            }
            return largest_component.getBounds().getCenterLonLat(); 
        }
    }

    var onFeatureSelect = function(event){

        var feature = event.feature;
        selectedFeature = feature;

        var html = "<div class=\"popup\">";
        html += "<div class=\"name\">" + feature.attributes.NAME +"</div>";
        html += "<div class=\"address\">" + feature.attributes.NAME_LOCAL+"</div>"

        var popup = new OpenLayers.Popup.FramedCloud("Feature Info",
            guessBestAnchorPoint(feature.geometry),
            null,
            html,
            null, true, onPopupClose);

        feature.popup = popup;
        CKAN.EuroMap.map.addPopup(popup);

        return false;

    }
    
    var onPopupClose = function(event){
        avoidNextClick = true;
        
        selectControl.unselect(selectedFeature);
        selectedFeature = null;
    }

    var onFeatureUnselect = function(event){
        CKAN.EuroMap.map.removePopup(event.feature.popup);
        event.feature.popup.destroy();
        event.feature.popup = null;
    }
    

    var getFeatureStyles = function(){

        // Default properties for all rules
        var defaultStyle = new OpenLayers.Style({
            "cursor":"pointer",
            "fillColor":"#E6E6E6",
            "strokeColor":"#000000"
        });
        var selectStyle = new OpenLayers.Style({
            "cursor":"pointer",
            "fillColor":"#CC0000",
            "strokeWidth":"1.5"
        });

        defaultStyle.addRules([
            new OpenLayers.Rule({
                filter: new OpenLayers.Filter.Comparison({
                    type: "==",
                    property: "datasets",
                    value: 0
                }),
                symbolizer: {
                    "fillColor":'#FFFFFF'
                }
            }),
            new OpenLayers.Rule({
                elseFilter: true,
                symbolizer: {
                    "fillColor": "#00FF00"
                }
            })
            ]);

         styleMap = new OpenLayers.StyleMap({
            "default":defaultStyle,
            "select":selectStyle})
       
        return styleMap;
    }

    

    // Public
    
    return {
        map: null,
        setup: function(){
            // Set element positions
            //$("#loading").css("left",$(window).width()/2 - $("#loading").width()/2);


            // Set map div size
            var w = $("#content").width()
            $("#map").width((w < 600) ? w : 600);
            $("#map").height((w < 400) ? w : 400);


            // Create a new map
            var map = new OpenLayers.Map("map" ,
            {
               /* 
                projection: new OpenLayers.Projection("EPSG:900913"),
                
                displayProjection: new OpenLayers.Projection("EPSG:4326"),
                units: "m",
                   maxResolution: 156543.0339,
    maxExtent: new OpenLayers.Bounds(-20037508.34, -20037508.34,
                                     20037508.34, 20037508.34), 
*/              maxExtent: new OpenLayers.Bounds(-33.32,26.72,47.02,72.23),
                fallThrough: true,
                controls: [
                new OpenLayers.Control.Navigation()
                ],
                theme:"/js/libs/openlayers/theme/default/style.css"
            });

            // Create layers to add
            var layers = [
            //osm = new OpenLayers.Layer.OSM("Simple OSM Map"),
            euro = new OpenLayers.Layer.Vector("Europa", {
                            strategies: [new OpenLayers.Strategy.Fixed()],
                            //projection: new OpenLayers.Projection("EPSG:900913"),
                            protocol: new OpenLayers.Protocol.HTTP({
                                url: "/map/data.json",
                                format: new OpenLayers.Format.GeoJSON()
                            }),
                            styleMap: getFeatureStyles(),
                            isBaseLayer: true
                        })
            ];
            map.addLayers(layers);
        
            // Create two selection controls,one for the hover/highlight and one
            // for the click/popup
            var hoverSelectControl = new OpenLayers.Control.SelectFeature(
                [euro],
                {
                    "hover": true,
                    "multiple": false,
                    "highlightOnly":true
                }
                );
            map.addControl(hoverSelectControl);
            hoverSelectControl.activate();
            selectControl = new OpenLayers.Control.SelectFeature(
                [euro],
                {
                    "hover": false,
                    "multiple": false,
                }
                );
            map.addControl(selectControl);
            selectControl.activate();

            euro.events.register("featureselected",this,onFeatureSelect);
            euro.events.register("featureunselected",this,onFeatureUnselect);

        
            
            map.setCenter(
                new OpenLayers.LonLat(8.98,48.74),4
                );
            
            //map.zoomToMaxExtent()
            //map.zoomToExtent(new OpenLayers.Bounds(-33.32,26.72,47.02,72.23),true);
            
            this.map = map;

        }
    }


}(jQuery);

OpenLayers.ImgPath = "/js/libs/openlayers/img/";
$(document).ready(function(){
    CKAN.EuroMap.setup();
});
