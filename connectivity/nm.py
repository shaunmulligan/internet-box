import NetworkManager
c = NetworkManager.const

def get_active_connections():
    connections = []
    for conn in NetworkManager.NetworkManager.ActiveConnections:
        settings = conn.Connection.GetSettings()['connection']
        if (settings['type'] != "bridge"):
            connections.append({"name": settings['id'], "type": settings['type'], "default": conn.Default, "devices": [x.Interface for x in conn.Devices] })
    return connections

def get_global_state():
    return {"state": c('state', NetworkManager.NetworkManager.State) }