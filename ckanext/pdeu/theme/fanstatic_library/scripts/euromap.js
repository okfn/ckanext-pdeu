
this.ckan.module('euromap', function($, _) {
	return {
		options: {
			startcolor: '#000000',
			endcolor: '#FFFFFF',
			groups: 1,
			homepage: false
		},
		map: false,
		breaks: false,
		colors: false,
		initialize: function() {
			$.proxyAll(this, /_on/);

			this.colors = $.calculateColor(this.options.startcolor,
			                               this.options.endcolor,
			                               this.options.groups,
			                               1);
			var linecolor = '#000000'
			var options = {
				crs: L.CRS.EPSG4326,
				attributionControl: false
			}

			if (this.options.homepage) {
				options.dragging = options.touchZoom = options.scrollWheelZoom =
				options.doubleClickZoom = options.zoomControl = false;
				options.minZoom = options.maxZoom = 3.2;
				linecolor = '#A8BADB';
			} else {
				options.minZoom = 4;
				options.maxZoom = 7;
			}

			this.map = new L.Map(this.el.prop('id'), options);
			this.map.setView(new L.LatLng(48.74, 8.98), 4);

			this.map.on('layeradd', function(e) {
				if (e.layer instanceof L.Path) {
					e.layer.setStyle({
						opacity: 1,
						fillOpacity: 1,
						color: linecolor,
						weight: 1.5
					});
				}
			});

			$.getJSON('/map/data.json', this._onHandleMapJSON);

		},
		_onHandleMapJSON: function(json) {
			this.breaks = this._onGetBreakPoints(json.features);
			var geo = new L.GeoJSON();
			geo.on('featureparse', this._onHandleMapFeatureParse);
			geo.addGeoJSON(json);
			this.map.addLayer(geo);
		},
		_onHandleMapFeatureParse: function(geo) {
			var color = this._onGetColor(geo.properties.packages);
			geo.layer.setStyle({fillColor: color});
			if (this.options.homepage){
				var country = geo.properties.NUTS;
				geo.layer.on('click', function(e) {
					document.location.href = '/dataset?extras_eu_country=' + country;
					return false;
				});
			} else {
				var popupText = this._onGetPopupHTML(geo.properties);
				geo.layer.bindPopup(popupText);
			}
		},
		_onGetBreakPoints: function(features) {
			var values = []
			for (var i = 0; i < features.length; i++){
				properties = features[i].properties || features[i].attributes;
				if (properties.packages != 0) {
					values.push(parseInt(properties.packages));
				}
			}
			values.sort(this._onSortBreakPointValues);
			var points = [];
			var range = ( values[values.length - 1] - values[0] ) / this.options.groups;
			for (var i = 0; i < this.options.groups; i++) {
				if (i > 0) {
					points.push(values[0] + i*range);
				}
			}
			return points;
		},
		_onSortBreakPointValues: function(a, b) {
			return a - b;
		},
		_onGetColor: function(value) {
			if (value == 0) {
				return this.colors[0];
			} else {
				for (var i = 0; i < this.breaks.length; i++) {
					if (value < this.breaks[i]) {
						return this.colors[i + 1];
					}
				}
			}
			return this.colors[this.colors.length - 1];
		},
		_onGetPopupHTML: function(properties) {
			var popupText;
            popupText = "<div class=\"name\">"+properties.NAME+"</div>" +
                        "<div class=\"local_name\">"+properties.NAME_LOCAL+"</div>" +
                        "<div class=\"datasets\">";
            popupText += (properties.packages == 0) ? "No datasets yet" :
                "<a href=\"/dataset?extras_eu_country="+properties.NUTS+"\">"+properties.packages+" datasets</a>";
            popupText += "</div>";

            return popupText;
		}
	};
});
