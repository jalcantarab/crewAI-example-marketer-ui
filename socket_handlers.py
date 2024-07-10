from flask_socketio import emit


def register_handlers(socketio):
    @socketio.on('connect')
    def handle_connect():
        emit('connected', {'data': 'Connected'})

    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected')

    @socketio.on('start_task')
    def handle_start_task(data):
        # This could be used to start a task from the frontend if needed
        pass
