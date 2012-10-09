var CKAN = CKAN || {};
CKAN.EuroMap = function($){


    var getBreakPoints = function(features,config){
            config = config || CKAN.EuroMap.config;
            var values = []
            for (var i = 0; i < features.length; i++){
                properties = features[i].properties || features[i].attributes;
                if (properties.packages != 0)
                    values.push(parseInt(properties.packages))
            }
            values.sort(function(a,b){return a -b})
            var points = [];
            var range = (values[values.length-1] - values[0]) / config.groups;
            for (var i = 0; i < config.groups; i++){
                if (i > 0)
                    points.push(values[0] + i*range)
            }

            return points;
        }

        var getColor = function(value,breaks,config){
            config = config || CKAN.EuroMap.config;
            if (value == 0)
                return config.colors[0]
             else
                for (var i = 0; i < breaks.length; i++) {
                    if (value < breaks[i])
                        return config.colors[i+1]
                };
                return config.colors[config.colors.length-1];
        }

        var getPopupText = function(properties){
            var popupText;

            popupText = "<div class=\"name\">"+properties.NAME+"</div>" +
                        "<div class=\"local_name\">"+properties.NAME_LOCAL+"</div>" +
                        "<div class=\"datasets\">";
            popupText += (properties.packages == 0) ? "No datasets yet" :
                "<a href=\"/dataset?extras_eu_country="+properties.NUTS+"\">"+properties.packages+" datasets</a>";
            popupText += "</div>";

            return popupText;

        }

    return {
        map:null,
        config: null,
        setup: function(){

            this.config["colors"] =  $.calculateColor(this.config.startColor,
                                                      this.config.endColor,
                                                      this.config.groups,1);


            var isHomePage = this.config.homePage;
            var mapDiv = (isHomePage) ? "map" : "map-large";

            var options = {
                crs:L.CRS.EPSG4326,
                attributionControl:false
            }

            if (!isHomePage){
                options['minZoom'] = 4;
                options['maxZoom'] = 7;
                var w = $("#content").width()
                $("#"+mapDiv).height((w < 500) ? w : 500);
            } else {
                options['dragging'] = options['touchZoom'] = options['scrollWheelZoom'] =
                options['doubleClickZoom'] =  options['zoomControl'] = false;
                options['minZoom'] = options['maxZoom'] = 3;
            }


            var map = new L.Map(mapDiv,options);

            map.setView(new L.LatLng(48.74,8.98), 4);

            map.on("layeradd",function(e){
                    if (e.layer instanceof L.Path)
                        e.layer.setStyle({
                            opacity: 1,
                            fillOpacity: 1,
                            color: "#C6C6C6",
                            weight: 1

                        });
                    });


            $.getJSON("/map/data.json",function(response){
               var breakPoints = getBreakPoints(response.features);
               var i = 1;

               var g = new L.GeoJSON();
               g.on('featureparse', function(e) {
                    color = getColor(e.properties.packages,breakPoints);
                    e.layer.setStyle({fillColor: color});
                    if (isHomePage){
                        var country = e.properties.NUTS
                        e.layer.on("click",function(e){
                            document.location = "/dataset?extras_eu_country=" + country;
                            return false;
                        });
                    } else {
                        var popupText = getPopupText(e.properties);
                        e.layer.bindPopup(popupText);
                    }
               });
               g.addGeoJSON(response);
               map.addLayer(g)
            });
            this.map = map;
        }
    }

}(jQuery);

$(document).ready(function(){
    CKAN.EuroMap.setup();
});
