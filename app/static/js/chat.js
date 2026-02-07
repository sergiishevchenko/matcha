(function() {
    var socket = io();
    var messagesDiv = document.getElementById('chat-messages');
    var form = document.getElementById('chat-form');
    var input = document.getElementById('message-input');

    if (!form) return;

    var receiverId = parseInt(form.dataset.receiverId, 10);
    var sendUrl = form.dataset.sendUrl;

    function scrollToBottom() {
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    scrollToBottom();

    socket.on('connect', function() {
        socket.emit('mark_read', {sender_id: receiverId});
    });

    socket.on('new_message', function(data) {
        if (data.sender_id === receiverId) {
            var div = document.createElement('div');
            div.className = 'message received';
            div.innerHTML = '<div class="message-content">' + escapeHtml(data.content) + '</div>' +
                            '<div class="message-time">' + data.created_at.split(' ')[1] + '</div>';
            messagesDiv.appendChild(div);
            scrollToBottom();
            socket.emit('mark_read', {sender_id: receiverId});
        }
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        var content = input.value.trim();
        if (!content) return;
        fetch(sendUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({receiver_id: receiverId, content: content})
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                var div = document.createElement('div');
                div.className = 'message sent';
                div.innerHTML = '<div class="message-content">' + escapeHtml(data.message.content) + '</div>' +
                                '<div class="message-time">' + data.message.created_at.split(' ')[1] + '</div>';
                messagesDiv.appendChild(div);
                scrollToBottom();
                input.value = '';
            }
        });
    });

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
})();
