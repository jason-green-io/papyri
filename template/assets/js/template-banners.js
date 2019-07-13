{% for banner in banners %}
L.marker([{{banner.X}}, {{banner.X}}], {icon: L.icon({
        iconUrl: '/test/banners/{{banner.overlayId}}.png'
})}).addTo(map);
{% endfor %}
