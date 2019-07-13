/*
 * leaflet.map-hash.js
 */

L.Map.mergeOptions({
	urlHash: false
});

L.Map.include({
	_onHashChange: function () {
		var center;
		var hash = L.parseParamString(window.location.hash.slice(1));
		var zoom;

		function isNum(n) {
			return typeof n === 'number';
		}

		if (isNum(hash.lng) && isNum(hash.lat)) {
			center = new L.LatLng(hash.lat, hash.lng);
		} else if (isNum(hash.lon) && isNum(hash.lat)) { // lon as lng
			center = new L.LatLng(hash.lat, hash.lon);
		} else if (isNum(hash.x) && isNum(hash.y)) { // cartesian coordinates
			center = this.options.crs.unproject(new L.Point(hash.x, hash.y));
		} else {
			center = this.getCenter();
		}

		if (isNum(hash.zoom)) {
			zoom = hash.zoom;
		}

		this.setView(center, zoom); // (re)sets hash through moveend handler
	},

	_setHash: function () {
		var center = this.getCenter();
		var zoom = this.getZoom();
		var decimals = 5;

		window.history.replaceState(null, '', '#' + [ // no history
			'lng='  + center.lng.toFixed(decimals),
			'lat='  + center.lat.toFixed(decimals),
			'zoom=' + zoom
		].join(';'));
	}
});

L.Map.addInitHook(function () {
	if (this.options.urlHash) {
		this.whenReady(function () {
			L.DomEvent.on(window, 'hashchange', this._onHashChange, this);

			this.on('moveend', this._setHash);

			if (window.location.hash) {
				this._onHashChange();
			}
		});
	}
});

/* utility/helper method */

L.parseParamString = function (str, result) { // key=value;k2=v2&k3=v3
	function parse(s) {
		switch (s) {
			case 'null':
				return null;
			case 'false':
				return false;
			case 'true':
				return true;
			default:
				var n = parseFloat(s);
				return !isNaN(n) && isFinite(s) ? n : decodeURIComponent(s.replace(/\+/g, ' '));
		}
	}

	result = result || {};
	str.replace(/([^&;=]+)=([^&;]*)/gi, function (match, key, value) {
		result[decodeURIComponent(key)] = parse(value);
	});

	return result;
};
