// OpenSeadragon Bookmark URL plugin 0.0.2

(function() {

    var $ = window.OpenSeadragon;

    if (!$) {
        $ = require('openseadragon');
        if (!$) {
            throw new Error('OpenSeadragon is missing.');
        }
    }

    // ----------
    $.Viewer.prototype.bookmarkUrl = function() {
        var self = this;

        var updateTimeout;

        var parseHash = function() {
            var params = {};
            var hash = window.location.hash.replace(/^#/, '');
            if (hash) {
                var parts = hash.split('&');
                parts.forEach(function(part) {
                    var subparts = part.split('=');
                    var key = subparts[0];
                    var value = parseFloat(subparts[1]);
                    if (!key || isNaN(value)) {
                        console.error('bad hash param', part);
                    } else {
                        params[key] = value;
                    }
                });
            }

            return params;
        };

        var updateUrl = function() {
            // We only update once it's settled, so we're not constantly flashing the URL.
            clearTimeout(updateTimeout);
            updateTimeout = setTimeout(function() {
                var zoom = self.viewport.getZoom();
                var pan = self.viewport.getCenter();
                var url = location.pathname + '#zoom=' + zoom + '&x=' + pan.x + '&y=' + pan.y;
                history.replaceState({}, '', url);
            }, 100);
        };

        var useParams = function(params) {
            var zoom = self.viewport.getZoom();
            var pan = self.viewport.getCenter();

            if (params.zoom !== undefined && params.zoom !== zoom) {
                self.viewport.zoomTo(params.zoom, null, true);
            }

            if (params.x !== undefined && params.y !== undefined && (params.x !== pan.x || params.y !== pan.y)) {
                self.viewport.panTo(new $.Point(params.x, params.y), true);
            }
        };

        var params = parseHash();

        if (this.world.getItemCount() === 0) {
            this.addOnceHandler('open', function() {
                useParams(params);
            });
        } else {
            useParams(params);
        }

        this.addHandler('zoom', updateUrl);
        this.addHandler('pan', updateUrl);

        // Note that out own replaceState calls don't trigger hashchange events, so this is only if
        // the user has modified the URL (by pasting one in, for instance).
        window.addEventListener('hashchange', function() {
            useParams(parseHash());
        }, false);
    };

})();
