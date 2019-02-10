#!/usr/bin/env python

import dbus, sys, time

class AccessPoint:
    'AP control class'
    ap_state=0

    def __init__(self, ssid='netbox', password='12345678', iface='wlan0'):
        self.ssid = ssid
        self.password = password
        our_uuid = '2b0d0f1d-b79d-43af-bde1-71744625642e'

        s_con = dbus.Dictionary({
            'type': '802-11-wireless',
            'uuid': our_uuid,
            'id': 'Test Hotspot'})

        s_wifi = dbus.Dictionary({
            'ssid': dbus.ByteArray(ssid.encode("utf-8")),
            'mode': "ap",
            'band': "bg",
            'channel': dbus.UInt32(1)})

        s_wsec = dbus.Dictionary({
            'key-mgmt': 'wpa-psk',
            'psk': password})

        s_ip4 = dbus.Dictionary({'method': 'shared'})
        s_ip6 = dbus.Dictionary({'method': 'ignore'})

        con = dbus.Dictionary({
            'connection': s_con,
            '802-11-wireless': s_wifi,
            '802-11-wireless-security': s_wsec,
            'ipv4': s_ip4,
            'ipv6': s_ip6
            })
        bus = dbus.SystemBus()
        service_name = "org.freedesktop.NetworkManager"
        proxy = bus.get_object(service_name, "/org/freedesktop/NetworkManager/Settings")
        settings = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Settings")
        iface = iface
        proxy = bus.get_object(service_name, "/org/freedesktop/NetworkManager")
        nm = dbus.Interface(proxy, "org.freedesktop.NetworkManager")
        devpath = nm.GetDeviceByIpIface(iface)

        self.our_uuid = our_uuid
        self.con = con
        self.settings = settings
        self.bus = bus
        self.nm = nm
        self.devpath = devpath
        self.service_name = service_name
    
    def up(self):
        
        # Find our existing hotspot connection
        connection_path = None
        for path in self.settings.ListConnections():
            proxy = self.bus.get_object(self.service_name, path)
            settings_connection = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Settings.Connection")
            config = settings_connection.GetSettings()
            if config['connection']['uuid'] == self.our_uuid:
                connection_path = path
                break

        # If the hotspot connection didn't already exist, add it
        if not connection_path:
            connection_path = self.settings.AddConnection(self.con)
        
        proxy = self.bus.get_object(self.service_name, self.devpath)
        acpath = self.nm.ActivateConnection(connection_path, self.devpath, "/")
        proxy = self.bus.get_object(self.service_name, acpath)
        active_props = dbus.Interface(proxy, "org.freedesktop.DBus.Properties")

        # Wait for the hotspot to start up
        start = time.time()
        while time.time() < start + 10:
            state = active_props.Get("org.freedesktop.NetworkManager.Connection.Active", "State")
            if state == 2:  # NM_ACTIVE_CONNECTION_STATE_ACTIVATED
                print("Access point started")
                AccessPoint.ap_state = 1
                return AccessPoint.ap_state
            time.sleep(1)
        print("Failed to start access point")
        AccessPoint.ap_state = 0
        
        return AccessPoint.ap_state

    def down(self):
        proxy = self.bus.get_object(self.service_name, self.devpath)
        device = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Device")

        device.Disconnect()
        AccessPoint.ap_state = 0

        return AccessPoint.ap_state

