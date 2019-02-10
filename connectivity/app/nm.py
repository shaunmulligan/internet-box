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

def activate_connection(name='resin-wifi'):
    # Find the connection

    connections = NetworkManager.Settings.ListConnections()
    connections = dict([(x.GetSettings()['connection']['id'], x) for x in connections])
    conn = connections[name]

    # Find a suitable device
    ctype = conn.GetSettings()['connection']['type']
    if ctype == 'vpn':
        for dev in NetworkManager.NetworkManager.GetDevices():
            if dev.State == NetworkManager.NM_DEVICE_STATE_ACTIVATED and dev.Managed:
                break
        else:
            print("No active, managed device found")
            raise NameError('No active, managed device found')
    else:
        dtype = {
            '802-11-wireless': NetworkManager.NM_DEVICE_TYPE_WIFI,
            '802-3-ethernet': NetworkManager.NM_DEVICE_TYPE_ETHERNET,
            'gsm': NetworkManager.NM_DEVICE_TYPE_MODEM,
        }.get(ctype,ctype)
        devices = NetworkManager.NetworkManager.GetDevices()

        for dev in devices:
            if dev.DeviceType == dtype and dev.State == NetworkManager.NM_DEVICE_STATE_DISCONNECTED:
                break
        else:
            print("No suitable and available %s device found" % ctype)
            raise NameError("No suitable and available %s device found" % ctype)

    # And connect
    return NetworkManager.NetworkManager.ActivateConnection(conn, dev, "/")