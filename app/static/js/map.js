(function() {
    var mapEl = document.getElementById('user-map');
    if (!mapEl) return;

    var defaultLat = parseFloat(mapEl.dataset.lat) || 46.5;
    var defaultLng = parseFloat(mapEl.dataset.lng) || 6.6;
    var apiUrl = mapEl.dataset.api;

    var map = L.map('user-map').setView([defaultLat, defaultLng], 10);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    var myIcon = L.divIcon({
        className: 'my-location-marker',
        html: '<div style="background:#e74c3c;width:16px;height:16px;border-radius:50%;border:3px solid #fff;box-shadow:0 2px 5px rgba(0,0,0,0.3);"></div>',
        iconSize: [22, 22],
        iconAnchor: [11, 11]
    });

    if (defaultLat && defaultLng) {
        L.marker([defaultLat, defaultLng], {icon: myIcon})
            .addTo(map)
            .bindPopup('<strong>You are here</strong>');
    }

    fetch(apiUrl)
        .then(function(r) { return r.json(); })
        .then(function(users) {
            users.forEach(function(u) {
                var photoHtml = u.photo
                    ? '<img src="/uploads/' + u.photo + '" alt="">'
                    : '<div style="width:60px;height:60px;background:#eee;border-radius:50%;margin:0 auto 0.5rem;line-height:60px;">?</div>';
                var statusClass = u.is_online ? 'online' : '';
                var statusText = u.is_online ? 'Online' : 'Offline';
                var popup = '<div class="user-popup">' +
                    photoHtml +
                    '<div class="name">' + u.first_name + '</div>' +
                    '<div class="status ' + statusClass + '">' + statusText + '</div>' +
                    '<a href="/profile/view/' + u.id + '">View Profile</a>' +
                    '</div>';
                L.marker([u.lat, u.lng]).addTo(map).bindPopup(popup);
            });
        });
})();
