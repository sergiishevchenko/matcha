(function() {
    var container = document.getElementById('videochat-container');
    if (!container) return;

    var socket = io();
    var roomId = container.dataset.roomId;
    var myUserId = parseInt(container.dataset.myUserId, 10);
    var myUserName = container.dataset.myUserName;
    var otherUserId = parseInt(container.dataset.otherUserId, 10);
    var otherUserName = container.dataset.otherUserName;
    var redirectUrl = container.dataset.redirectUrl;

    var localVideo = document.getElementById('local-video');
    var remoteVideo = document.getElementById('remote-video');
    var remotePlaceholder = document.getElementById('remote-placeholder');
    var statusEl = document.getElementById('call-status');
    var toggleVideoBtn = document.getElementById('toggle-video');
    var toggleAudioBtn = document.getElementById('toggle-audio');
    var endCallBtn = document.getElementById('end-call');

    var localStream = null;
    var peerConnection = null;
    var videoEnabled = true;
    var audioEnabled = true;

    var config = {
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' }
        ]
    };

    function updateStatus(text, className) {
        statusEl.textContent = text;
        statusEl.className = 'call-status ' + (className || '');
    }

    async function startCall() {
        try {
            localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            localVideo.srcObject = localStream;
            socket.emit('join_call', { room: roomId, user_id: myUserId });
            socket.emit('call_request', {
                target_user_id: otherUserId,
                caller_id: myUserId,
                caller_name: myUserName,
                room: roomId
            });
            updateStatus('Calling ' + otherUserName + '...');
        } catch (err) {
            updateStatus('Camera/mic access denied', 'error');
            console.error('Media error:', err);
        }
    }

    function createPeerConnection() {
        peerConnection = new RTCPeerConnection(config);
        localStream.getTracks().forEach(function(track) {
            peerConnection.addTrack(track, localStream);
        });
        peerConnection.ontrack = function(event) {
            remoteVideo.srcObject = event.streams[0];
            remotePlaceholder.style.display = 'none';
            updateStatus('Connected', 'connected');
        };
        peerConnection.onicecandidate = function(event) {
            if (event.candidate) {
                socket.emit('ice_candidate', { room: roomId, candidate: event.candidate });
            }
        };
        peerConnection.onconnectionstatechange = function() {
            if (peerConnection.connectionState === 'disconnected' || peerConnection.connectionState === 'failed') {
                updateStatus('Connection lost', 'error');
            }
        };
    }

    socket.on('user_joined', async function() {
        updateStatus('User joined, connecting...');
        createPeerConnection();
        var offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        socket.emit('offer', { room: roomId, offer: offer });
    });

    socket.on('offer', async function(data) {
        createPeerConnection();
        await peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));
        var answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);
        socket.emit('answer', { room: roomId, answer: answer });
    });

    socket.on('answer', async function(data) {
        await peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
    });

    socket.on('ice_candidate', async function(data) {
        if (peerConnection && data.candidate) {
            try {
                await peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
            } catch (e) {
                console.error('ICE error:', e);
            }
        }
    });

    socket.on('user_left', function() {
        updateStatus('User left the call', 'error');
        endCall(false);
    });

    socket.on('call_ended', function() {
        updateStatus('Call ended', '');
        endCall(false);
    });

    socket.on('call_declined', function() {
        updateStatus('Call declined', 'error');
    });

    toggleVideoBtn.addEventListener('click', function() {
        videoEnabled = !videoEnabled;
        localStream.getVideoTracks().forEach(function(track) {
            track.enabled = videoEnabled;
        });
        toggleVideoBtn.classList.toggle('active', !videoEnabled);
    });

    toggleAudioBtn.addEventListener('click', function() {
        audioEnabled = !audioEnabled;
        localStream.getAudioTracks().forEach(function(track) {
            track.enabled = audioEnabled;
        });
        toggleAudioBtn.classList.toggle('active', !audioEnabled);
    });

    function endCall(notify) {
        if (peerConnection) {
            peerConnection.close();
            peerConnection = null;
        }
        if (localStream) {
            localStream.getTracks().forEach(function(track) { track.stop(); });
        }
        if (notify) {
            socket.emit('call_ended', { room: roomId });
            socket.emit('leave_call', { room: roomId, user_id: myUserId });
        }
        setTimeout(function() {
            window.location.href = redirectUrl;
        }, 1000);
    }

    endCallBtn.addEventListener('click', function() {
        endCall(true);
    });

    window.addEventListener('beforeunload', function() {
        socket.emit('leave_call', { room: roomId, user_id: myUserId });
    });

    startCall();
})();
