from shared import app 
import status_state

@app.route('/set_down_internal')
def set_down_internal():
    status_state.status_up = False
    return "Status set to DOWN (internal)", 200

@app.route('/set_up_internal')
def set_up_internal():
    status_state.status_up = True
    return "Status set to UP (internal)", 200
