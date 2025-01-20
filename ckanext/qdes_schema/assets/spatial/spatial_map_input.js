/**
 * Create spatial map input.
 * The rectangle will populate the lower left and upper right,
 * and marker will populate the centroid.
 *
 * All those fields id selector can be adjustable via data attributes:
 * - data-module-lower-left => field selector
 * - data-module-upper-right => field selector
 * - data-module-centroid => field selector
 * - data-module-geometry => field selector
 * - data-module-extent => geojson
 * - data-module-max-bounds => geojson
 *
 * Things to note, GeoSpatial software (Leaflet and Leaflet Draw) has inconsistency,
 * in this case, when drawing (Leaflet Draw lib) will return lng lat BUT labeled as lat lng, it is soo misleading.
 * And when the value passed to Leaflet, it assume accept the correct lat lng format.
 * This make the GeoJSON result inconsistent and hard to work with,
 * for workaround there is a method _convertBoundsFromLngLatToLatLng() to handle this mapping.
 *
 * See more here https://macwright.com/lonlat/.
 */
this.ckan.module('spatial-map-input', function (jQuery, _) {
    // Add arrow control.
    // This arrow buttons are not OOTB feature from leaflet,
    // below code was copied from spatial_query.js
    L.Control.Arrow = L.Control.extend({
        options: {
            position: 'topleft'
        },

        onAdd: function (map) {
            var arrowName = 'leaflet-control-arrow',
                barName = 'leaflet-bar',
                partName = barName + '-part',
                container = L.DomUtil.create('div', arrowName + ' ' + barName);

            this._map = map;

            this._moveUpButton = this._createButton('', 'Move up',
                arrowName + '-up ' +
                partName + ' ' +
                partName + '-up',
                container, this._move('up'), this);

            this._moveLeftButton = this._createButton('', 'Move left',
                arrowName + '-left ' +
                partName + ' ' +
                partName + '-left',
                container, this._move('left'), this);

            this._moveRightButton = this._createButton('', 'Move right',
                arrowName + '-right ' +
                partName + ' ' +
                partName + '-right',
                container, this._move('right'), this);

            this._moveDownButton = this._createButton('', 'Move down',
                arrowName + '-down ' +
                partName + ' ' +
                partName + '-down',
                container, this._move('down'), this);


            return container;
        },

        onRemove: function () {

        },

        _move: function (direction) {
            var d = [0, 0];
            var self = this;

            switch (direction) {
                case 'up':
                    d[1] = -10;
                    break;
                case 'down':
                    d[1] = 10;
                    break;
                case 'left':
                    d[0] = -10;
                    break;
                case 'right':
                    d[0] = 10;
                    break;
            }
            return function () {
                self._map.panBy(d);
            };
        },

        _createButton: function (html, title, className, container, fn, context) {
            var link = L.DomUtil.create('a', className, container);
            link.innerHTML = html;
            link.href = '#';
            link.title = title;

            var stop = L.DomEvent.stopPropagation;

            L.DomEvent
                .on(link, 'click', stop)
                .on(link, 'mousedown', stop)
                .on(link, 'dblclick', stop)
                .on(link, 'click', L.DomEvent.preventDefault)
                .on(link, 'click', fn, context);

            return link;
        }
    });

    var mapContainer = 'spatial-map-input-container';

    return {
        // Define the spatial map input related variables.
        markerLayer: null,
        rectangleLayer: null,
        baseLayerUrl: 'https://stamen-tiles-c.a.ssl.fastly.net/terrain/{z}/{x}/{y}.png',
        leafletBaseLayerOptions: {attribution: false},
        editableLayers: new L.FeatureGroup(),
        map: new L.Map(mapContainer, {
            attributionControl: false,
            zoom: 5,
            zoomDelta: 0.25,
            zoomSnap: 0.25,
            minZoom: 3.75
        }),
        options: {},
        lowerLeftFieldElement: null,
        upperRightFieldElement: null,
        centroidFieldElement: null,
        geometryFieldElement: null,
        mapContainerVisible: false,

        // This is the first method that get triggered.
        initialize: function () {
            var spatialMapInput = this;

            // Init field elements.
            this.lowerLeftFieldElement = jQuery(this.options.lowerLeft);
            this.upperRightFieldElement = jQuery(this.options.upperRight);
            this.centroidFieldElement = jQuery(this.options.centroid);
            this.geometryFieldElement = jQuery(this.options.geometry);

            // Hack to make leaflet use a particular location to look for images
            L.Icon.Default.imagePath = this.options.site_url + 'js/vendor/leaflet/1.9.3/images/';

            jQuery.proxyAll(this, /_on/);
            this.el.ready(this._onReady);

            // Specific to QDES.
            // Since the map container is collapse within an accordion,
            // the leatlet not able to correctly calculate the canvas to draw the map,
            // so let's listen to visibility changes and trigger browser resize, and reset the bounds.
            jQuery('.display-group-spatial > input[name=tabs]').on('change', function (e) {
                if (jQuery(this).is(':checked')) {
                    spatialMapInput.map.invalidateSize(true);
                    if (spatialMapInput.lowerLeftFieldElement.val().length > 0 && spatialMapInput.upperRightFieldElement.val().length > 0) {
                        spatialMapInput.map.fitBounds(spatialMapInput.editableLayers.getBounds());
                    }
                    else {
                        spatialMapInput._setDefaultBounds();
                    }
                }
            });
        },

        _onReady: function () {
            // Setup map.
            this.map.addControl(new L.Control.Arrow);
            this._setDefaultBounds();
            this._setMaxBounds();

            // Add tile layer.
            L.tileLayer(this.options.map_config['custom.url'] || baseLayerUrl, this.leafletBaseLayerOptions).addTo(this.map);

            // Store editable layers.
            this.map.addLayer(this.editableLayers);

            // Add draw controller.
            var drawControl = new L.Control.Draw({
                position: 'topright',
                draw: {
                    circle: false,
                    circlemarker: false,
                    polygon: false,
                    polyline: false
                },
                edit: {
                    featureGroup: this.editableLayers
                }
            });
            this.map.addControl(drawControl);

            // Draw default rectangle and centroid if data exist.
            if (this.lowerLeftFieldElement.val().length > 0 && this.upperRightFieldElement.val().length > 0) {
                this._drawRectangle();
            }
            if (this.centroidFieldElement.val().length > 0) {
                this._drawMarker();
            }

            // Listen to draw:created event.
            this.map.on('draw:created', this._onDrawCreated);

            // Listen to edited map draw:edited event.
            this.map.on('draw:edited', this._onDrawEdited);

            // // Listen to deleted map draw:deleted event.
            this.map.on('draw:deleted', this._onDrawDeleted);

            // Setup event listener to lower left, upper right, centroid and geometry field.
            this.lowerLeftFieldElement.on('change', this._onChangeLowerLeftUpperRight);
            this.upperRightFieldElement.on('change', this._onChangeLowerLeftUpperRight);
            this.centroidFieldElement.on('change', this._onChangeCentroid);
            this.geometryFieldElement.on('change', this._onChangeGeometry);
        },

        _setDefaultBounds: function () {
            // Set a map view that contains the given geographical bounds with the maximum zoom level possible.
            if (this.options.extent) {
                var defaultBounds = new L.GeoJSON(this.options.extent).getBounds();
                this.map.fitBounds(defaultBounds);
            }
        },

        _setMaxBounds: function () {
            // Restrict the view to the given geographical bounds,
            // bouncing the user back if the user tries to pan outside the view.
            if (this.options.maxBounds) {
                var maximumBounds = new L.GeoJSON(this.options.maxBounds).getBounds();
                this.map.setMaxBounds(maximumBounds);
            }
        },

        _onDrawCreated: function (e) {
            var type = e.layerType,
                layer = e.layer,
                existingLayer = null;

            // Need to check if the rectangle is exist.
            // If so, replace it with the new drawn marker.
            switch (type) {
                case 'rectangle':
                    existingLayer = this.rectangleLayer;

                    // Let's beat the inconsistency by mapping them lat lng.
                    // The Leaflet Draw (layer variable) return lng as lat, and lat as lng.
                    var correctLatLngBounds = this._convertBoundsFromLngLatToLatLng(layer.getBounds());
                    var rectangle = L.rectangle(correctLatLngBounds);
                    this.rectangleLayer = layer;
                    this._populateLowerLeft(rectangle.getBounds());
                    this._populateUpperRight(rectangle.getBounds());
                    break;
                case 'marker':
                    existingLayer = this.markerLayer;
                    this.markerLayer = layer;
                    this._populateCentroid(layer);
                    break
                default:
                    existingLayer = null;
            }
            if (existingLayer) {
                this.editableLayers.removeLayer(existingLayer);
            }

            // At this line, we assume the layer is clean,
            // let's add the newly drawn marker/rectangle to the layer.
            this.editableLayers.addLayer(layer);
        },

        _onDrawEdited: function (e) {
            var spatialMapInput = this;
            e.layers.eachLayer(function (layer) {
                if (layer instanceof L.Rectangle) {
                    // Let's beat the inconsistency by mapping them lat lng.
                    // The Leaflet Draw (layer variable) return lng as lat, and lat as lng.
                    var correctLatLngBounds = spatialMapInput._convertBoundsFromLngLatToLatLng(layer.getBounds());
                    var rectangle = L.rectangle(correctLatLngBounds);
                    spatialMapInput.rectangleLayer = layer;
                    spatialMapInput._populateLowerLeft(rectangle.getBounds());
                    spatialMapInput._populateUpperRight(rectangle.getBounds());
                }

                if (layer instanceof L.Marker) {
                    spatialMapInput.markerLayer = layer;
                    spatialMapInput._populateCentroid(layer);
                }
            });
        },

        _onDrawDeleted: function (e) {
            var spatialMapInput = this;
            e.layers.eachLayer(function (layer) {
                if (layer instanceof L.Rectangle) {
                    spatialMapInput.rectangleLayer = null;
                    spatialMapInput.lowerLeftFieldElement.val('');
                    spatialMapInput.upperRightFieldElement.val('');
                }

                if (layer instanceof L.Marker) {
                    spatialMapInput.markerLayer = null;
                    spatialMapInput.centroidFieldElement.val('');
                }
            });
        },

        _convertBoundsFromLngLatToLatLng: function (boundsLngLat) {
            var southWest = boundsLngLat.getSouthWest();
            var northEast = boundsLngLat.getNorthEast();

            return L.latLngBounds([southWest.lng, southWest.lat], [northEast.lng, northEast.lat])
        },

        _populateLowerLeft: function (bounds) {
            var southWest = bounds.getSouthWest();
            var geometry = {
                "type":"Point",
                "coordinates": [southWest.lat, southWest.lng]
            }
            this.lowerLeftFieldElement.val(JSON.stringify(geometry));
        },

        _populateUpperRight: function (bounds) {
            var northEast = bounds.getNorthEast();
            var geometry = {
                "type":"Point",
                "coordinates": [northEast.lat, northEast.lng]
            }
            this.upperRightFieldElement.val(JSON.stringify(geometry));
        },

        _populateCentroid: function (marker) {
            this.centroidFieldElement.val(JSON.stringify(marker.toGeoJSON().geometry));
        },

        _onChangeLowerLeftUpperRight: function (e) {
            // Do not re-draw based on lower left/upper right IF there is geometry value.
            if (this.geometryFieldElement.val().length > 0) {
                this._onChangeGeometry()
            }
            else {
                this._drawRectangle();
            }
        },
        
        _onChangeCentroid: function (e) {
            this._drawMarker();
        },
        
        _onChangeGeometry: function (e) {
            // Auto calculate the lower left and upper right
            // and then trigger _onChangeLowerLeftUpperRight so that the map will be redrew.
            if (this.geometryFieldElement.val().trim().length > 0) {
                var geometry = JSON.parse(this.geometryFieldElement.val()).coordinates;
                var bounds = L.polygon(geometry).getBounds();
                this._populateLowerLeft(bounds);
                this._populateUpperRight(bounds);
            }

            // Trigger map re-draw.
            this._drawRectangle();
        },

        _lowerLeftUpperRightToRectangle: function () {
            // Get lower left and upper right geoJSON coordinates.
            if (this.lowerLeftFieldElement.val().trim().length > 0 && this.upperRightFieldElement.val().trim().length > 0) {
                var lowerLeft = L.GeoJSON.coordsToLatLng(JSON.parse(this.lowerLeftFieldElement.val()).coordinates);
                var upperRight = L.GeoJSON.coordsToLatLng(JSON.parse(this.upperRightFieldElement.val()).coordinates);
                if (lowerLeft && upperRight) {
                    var bounds = L.latLngBounds(lowerLeft, upperRight);
                    return L.rectangle(bounds);
                }
            }

            return null;
        },

        _centroidToMarker: function () {
            // Get centroid geoJSON coordinates.
            if (this.centroidFieldElement.val().length > 0) {
                var centroid = L.GeoJSON.coordsToLatLng(JSON.parse(this.centroidFieldElement.val()).coordinates);
                if (centroid) {
                    return L.marker(centroid);
                }
            }

            return null;
        },

        _drawRectangle: function () {
            var rectangle = this._lowerLeftUpperRightToRectangle();
            if (rectangle) {
                if (this.rectangleLayer) {
                    this.editableLayers.removeLayer(this.rectangleLayer);
                }

                this.rectangleLayer = rectangle;
                this.editableLayers.addLayer(this.rectangleLayer);

                // Let's zoom it to this newly drawn rectangle.
                this.map.fitBounds(this.editableLayers.getBounds());
            }
        },

        _drawMarker: function () {
            // Get centroid geoJSON coordinates.
            var centroid = this._centroidToMarker();
            if (centroid) {
                if (this.markerLayer) {
                    this.editableLayers.removeLayer(this.markerLayer);
                }

                this.markerLayer = centroid;
                this.editableLayers.addLayer(this.markerLayer);
            }
        }
    }
});
