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

    var onFeatureSelectHomePage = function(event){
        var feature = event.feature;
        selectedFeature = feature;
        document.location = "/package?extras_eu_country=" + feature.attributes.NUTS;
        return false; 
    }

    var onFeatureSelect = function(event){

        var feature = event.feature;
        selectedFeature = feature;

        var html = "<div class=\"popup\">";
        html += "<div class=\"name\">" + feature.attributes.NAME +"</div>";
        html += "<div class=\"local_name\">" + feature.attributes.NAME_LOCAL+"</div>"
        html += "<div class=\"packages\">";
        if (feature.attributes.packages){
            html += "<a href=\"/dataset?extras_eu_country=" + feature.attributes.NUTS + "\">" +
                feature.attributes.packages+" packages";
        } else {
            html += "No packages yet";
        }
        html += "</a></div>"

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

    var getBreakPoints = function(groups){

        var values = []
        for (var i = 0; i < featuresLayer.features.length; i++){
            ft = featuresLayer.features[i]
            if (ft.attributes.packages != 0)
                values.push(parseInt(ft.attributes.packages))
        }
        values.sort(function(a,b){return a -b})
        var points = [];
        var range = (values[values.length-1] - values[0]) / groups;
        for (var i = 0; i < groups; i++){
            if (i > 0)
                points.push(values[0] + i*range)
        }

        return points;

    }

    var setupStyles = function(){
        var config = CKAN.EuroMap.config;
        var groups = 5;
        var colors = $.calculateColor(config.startColor,config.endColor,config.groups,1);
        var breakPoints = getBreakPoints(groups);

        // Default properties for all rules
        var defaultStyle = new OpenLayers.Style({
            "cursor":"pointer",
            "strokeColor":"#c6c6c6",
            "strokeWidth":"0.8",
        });
        var selectStyle = new OpenLayers.Style({
            "fillColor":"#faf4c8",
        });

        // Create rules according to the actual values
        var rules = []

        // Countries with no packages
        rules.push(
            new OpenLayers.Rule({
                filter: new OpenLayers.Filter.Comparison({
                    type: "==",
                    property: "packages",
                    value: 0
                }),
                symbolizer: {
                    "fillColor":'#FFFFFF'
                }
            }))

        var min, max;
        for (var i = 0; i < breakPoints.length; i++) {
            if (i < breakPoints.length -1){
                min = (i == 0) ? 1 : breakPoints[i - 1];
                max = breakPoints [i];

                rules.push(
                    new OpenLayers.Rule({
                        filter: new OpenLayers.Filter.Logical({
                            type: "&&",
                            filters: [
                                new OpenLayers.Filter.Comparison({
                                    type: "<=",
                                    property: "packages",
                                    value: max
                                }),
                                new OpenLayers.Filter.Comparison({
                                    type: ">",
                                    property: "packages",
                                    value: min
                                })]
                        }),
                        symbolizer: {"fillColor": colors[i]}
                    }));
            } else {
                min = breakPoints[i]
                rules.push(
                    new OpenLayers.Rule({
                        filter: new OpenLayers.Filter.Comparison({
                                    type: ">",
                                    property: "packages",
                                    value: min
                                }),
                        symbolizer: {"fillColor": colors[i]}
                    }));
            }
        };


        defaultStyle.addRules(rules);

        styleMap = new OpenLayers.StyleMap({
            "default":defaultStyle,
            "select":selectStyle})

        featuresLayer.styleMap = styleMap;
        featuresLayer.redraw();
    }

    // Public
    return {
        map: null,
        setup: function(){

            var isHomePage = this.config.homePage;
            var mapDiv = (isHomePage) ? "map" : "map-large";
            // Set map div size
            var w = $("#content").width()
            $("#"+mapDiv).width((w < 600) ? w : 600);
            $("#"+mapDiv).height((w < 400) ? w : 400);

            var controls = (isHomePage) ? [] : [
                    new OpenLayers.Control.Navigation(),
                    new OpenLayers.Control.PanZoomBar()
                ]

            var options = {
                //projection: new OpenLayers.Projection("EPSG:900913"),
                projection: new OpenLayers.Projection("EPSG:4326"),
               /*
                displayProjection: new OpenLayers.Projection("EPSG:4326"),
                units: "m",
                maxResolution: 156543.0339,
                maxExtent: new OpenLayers.Bounds(-20037508.34, -20037508.34,
                                     20037508.34, 20037508.34),
                */
                //maxExtent: new OpenLayers.Bounds(-33.32,26.72,47.02,72.23),
                maxExtent: new OpenLayers.Bounds(-33.32,26.72,47.02,72.23),
                //maxExtent: new OpenLayers.Bounds(-1,1,1,1),
                
                fallThrough: true,
                controls: controls ,
                theme:"/js/libs/openlayers/theme/default/style.css"
            };
            if (!isHomePage){
                options["maxScale"] = 30000000;
                options["minScale"] = 6000000;
                options["numZoomLevels"] = 3;

            }
            // Create a new map
            var map = new OpenLayers.Map(mapDiv ,options);

            // Create layers to add
            var layers = [
            euro = new OpenLayers.Layer.Vector("Europa", {
                            strategies: [new OpenLayers.Strategy.Fixed()],
                            protocol: new OpenLayers.Protocol.HTTP({
                                url: "/map/data.json",
                                format: new OpenLayers.Format.GeoJSON()
                            }),
                            isBaseLayer: true
                        })
            ];
            map.addLayers(layers);
            featuresLayer = euro

            // Create two selection controls,one for the hover/highlight and one
            // for the click/popup
            var hoverSelectControl = new OpenLayers.Control.SelectFeature(
                [euro],
                {"hover": true,"multiple": false,"highlightOnly":true});
            map.addControl(hoverSelectControl);
            hoverSelectControl.activate();

            selectControl = new OpenLayers.Control.SelectFeature(
                [euro],
                {"hover": false,"multiple": false});
            map.addControl(selectControl);
            selectControl.activate();

            euro.events.register("featureselected",this, (isHomePage) ? onFeatureSelectHomePage : onFeatureSelect);
            if (!isHomePage) euro.events.register("featureunselected",this,onFeatureUnselect);
            euro.events.register("featuresadded",this,setupStyles);

            map.setCenter(new OpenLayers.LonLat(8.98,48.74),3);

            this.map = map;

        }
    }

}(jQuery);

OpenLayers.ImgPath = "/js/libs/openlayers/img/";
$(document).ready(function(){
    CKAN.EuroMap.setup();
});
