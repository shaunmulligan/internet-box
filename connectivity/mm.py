#!/usr/bin/python3

# script created for reading SMS messages from 3G modem connected to PC
# 1) it looks for modem
# 2) reads all SMS messages from modem
# 3) prints all found SMS messages to stdout only if total messages count
#    greater than SMS_STORE_COUNT (default is 3)
# 4) save all but SMS_STORE_COUNT messages to txt files and
#    delete them from modem

import sys
import dbus
from datetime import datetime
import json
import os

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

SMS_STORE_COUNT = 3
if 'SMS_STORE_COUNT' in os.environ:
    SMS_STORE_COUNT = int(os.environ['SMS_STORE_COUNT'])

# https://developer.gnome.org/ModemManager/unstable/ModemManager-Flags-and-Enumerations.html#MMSmsState
class MMSmsState(object):
    MM_SMS_STATE_UNKNOWN   = 0
    MM_SMS_STATE_STORED    = 1
    MM_SMS_STATE_RECEIVING = 2
    MM_SMS_STATE_RECEIVED  = 3
    MM_SMS_STATE_SENDING   = 4
    MM_SMS_STATE_SENT      = 5

# singleton: main app loop
class MainLoop(object):

    instance = None
    loop = None

    def __new__(cls, *args, **kwargs):
        if not cls.instance:
            cls.instance = super(MainLoop, cls).__new__(cls, *args, **kwargs)
        return cls.instance

    def __init__(self):
        if not self.loop:
            self.loop = GLib.MainLoop()
    
    def run(self):
        self.loop.run()
    
    def quit(self):
        self.loop.quit()

class DBus(object):

    system_bus = None
    dbus_proxy = None

    @staticmethod
    def type_cast(val):
        if val is None:
            return None
        elif isinstance(val, (dbus.String, dbus.ObjectPath)):
            return str(val)
        elif isinstance(val, (dbus.Int32, dbus.UInt32)):
            return int(val)
        elif isinstance(val, dbus.Array):
            return [DBus.type_cast(e) for e in val]
        return val

    def __init__(self, *args, **kwargs):
        super(DBus, self).__init__(*args, **kwargs)
        self.system_bus = dbus.SystemBus()

    # https://dbus.freedesktop.org/doc/dbus-python/tutorial.html#proxy-objects
    def setup_proxy_object(self, bus_name, object_path):
        self.dbus_proxy = self.system_bus.get_object(bus_name, object_path)

    def set_proxy_object(self, proxy_object):
        if isinstance(proxy_object, DBus):
            self.dbus_proxy = proxy_object.dbus_proxy
        elif isinstance(proxy_object, (dbus.Interface, dbus.proxies.ProxyObject)):
            self.dbus_proxy = proxy_object

    def get_proxy_object(self):
        return self.dbus_proxy

    def get_dbus_interface(self, interface):
        if self.dbus_proxy:
            return dbus.Interface(self.dbus_proxy, dbus_interface=interface)
        return None

    # https://dbus.freedesktop.org/doc/dbus-specification.html#standard-interfaces-objectmanager
    def get_objmanager_objects(self):
        if self.dbus_proxy:
            return self.get_dbus_interface('org.freedesktop.DBus.ObjectManager').GetManagedObjects()
        return {}

class DBusObject(DBus):
    
    obj_path = None
    
    def __init__(self, bus_name, path, *args, **kwargs):
        super(DBusObject, self).__init__(*args, **kwargs)
        self.obj_path = path
        self.setup_proxy_object(bus_name, path)
    
    def get_object_path(self):
        return self.obj_path

class ModemManagerObject(DBusObject):
    
    def __init__(self, obj_path, *args, **kwargs):
        super(ModemManagerObject, self).__init__(bus_name='org.freedesktop.ModemManager1', path=obj_path, *args, **kwargs)

    @staticmethod
    def object_path(obj, path = None):
        
        objbasepath = "/org/freedesktop/ModemManager1/%s/" % obj
        
        objid = None
        if isinstance(path, str) and objbasepath in path:
            objid = path.split('/')[-1]
        else:
            objid = path

        objpath = None
        try:
            objpath = "%s%d" % (objbasepath, int(objid))
        except (ValueError, TypeError):
            print("Bad object ID provided: %s" % objid, file=sys.stderr)

        return objpath

class DBusInterface(DBus):
    
    name = None
    interface = None
    properties = None

    def __init__(self,  dbus_interface,  *args, **kwargs):
        super(DBusInterface, self).__init__(*args, **kwargs)
        self.name = dbus_interface
        self.interface = self.get_dbus_interface(dbus_interface)
        self.set_properties()

    # https://dbus.freedesktop.org/doc/dbus-specification.html#standard-interfaces-properties
    def get_properties(self):
        try:
            if self.dbus_proxy:
                return self.dbus_proxy.GetAll(self.name, dbus_interface='org.freedesktop.DBus.Properties')
        except dbus.exceptions.DBusException as e:
            print("Can not get %s interface properties: %s" % (self.interface, e), file=sys.stderr)
        return None
    
    def set_properties(self):
        self.properties = self.get_properties()

    def get_property(self, name):
        if self.properties and name in self.properties:
            return DBus.type_cast(self.properties[name])
        return None

    def setup_signal(self, name, handler):
        self.interface.connect_to_signal(name, handler)


class MMModem(DBusInterface, ModemManagerObject):
    
    # parameters:
    # modem     could be Integer (aka Modem ID) or String. If String - it could
    #           contain number representing Modem ID or Modem Object Path
    def __init__(self, modem = None):
        path = ModemManagerObject.object_path('Modem', modem)
        super(MMModem, self).__init__(obj_path=path, dbus_interface='org.freedesktop.ModemManager1.Modem')
    
    # The equipment manufacturer, as reported by the modem. (eg 'huawei')
    def Manufacturer(self):
        return self.get_property('Manufacturer')

    # The equipment model, as reported by the modem. (eg 'E1550')
    def Model(self):
        return self.get_property('Model')

    # The identity of the device.
    # This will be the IMEI number for GSM devices and the hex-format ESN/MEID
    # for CDMA devices.
    def EquipmentIdentifier(self):
        return self.get_property('EquipmentIdentifier')
    
    # List of numbers (e.g. MSISDN in 3GPP) being currently handled by this modem.
    # return value: Array(String)
    def OwnNumbers(self):
        return self.get_property('OwnNumbers')

class MMModemSms(DBusInterface, ModemManagerObject):

    def __init__(self, sms):
        path = ModemManagerObject.object_path('SMS', sms)
        super(MMModemSms, self).__init__(obj_path=path, dbus_interface='org.freedesktop.ModemManager1.Sms')

    # Number to which the message is addressed.
    def Number(self):
        return self.get_property('Number')
    
    # Message text, in UTF-8.
    def Text(self):
        return self.get_property('Text')

    def State(self):
        return self.get_property('State')

    # Time when the first PDU of the SMS message arrived the SMSC, in ISO8601
    # format. This field is only applicable if the PDU type is
    # MM_SMS_PDU_TYPE_DELIVER or MM_SMS_PDU_TYPE_STATUS_REPORT.
    def Timestamp(self):
        stamp = self.get_property('Timestamp')
        if isinstance(stamp, str) and len(stamp) == 15:
            # convert into format %y%m%d%H%M%S%z and return
            return '{:0<17s}'.format(stamp)
        return None
    
    def get_datetime(self):
        stamp = self.Timestamp()
        if stamp:
            return datetime.strptime(stamp, '%y%m%d%H%M%S%z')
        return None
    
    def get_date(self):
        dt = self.get_datetime()
        if dt:
            return dt.strftime("%c %Z")
        return None

    def save(self, fname = None):
        if fname is None:
            fname = "%s-%s.txt" % (self.Number(), self.Timestamp())
        sms = {}
        for f in ['Number', 'Text', 'Timestamp']:
            sms[f] = self.get_property(f)
        sms['Date'] = self.get_date()
        with open(fname.lower(), 'w') as fp:
            json.dump(sms, fp, ensure_ascii=False, indent="\t", sort_keys=True)

        
# signal handlers
def message_added(path, received):
    print("Message received: path=%s; received=%s" % (path, received))
#    MainLoop().quit()

class MMModemMessaging(DBusInterface):

    def __init__(self, modem):
        if not isinstance(modem, MMModem):
            modem = MMModem(modem)        
        self.set_proxy_object(modem)
        super(MMModemMessaging, self).__init__(dbus_interface='org.freedesktop.ModemManager1.Modem.Messaging')

    # The list of SMS object paths.
    def Messages(self):
        return self.get_property('Messages')

    # return SMS object (MMModemSms)
    # parameters:
    #   sms     is SMS object path or object ID; if not provided - return all
    #           SMS objects
    def get_sms(self, sms = None, reverse=True):
        if sms is None:
            # sort by date
            return sorted(
                filter(
                    lambda x: x.State() == MMSmsState.MM_SMS_STATE_RECEIVED,
                    list(
                        map(
                            lambda x: MMModemSms(x),
                            self.Messages()
                        )
                    )
                ),
                key=lambda x: x.get_datetime(),
                reverse=reverse
            )
        smspath = ModemManagerObject.object_path('SMS', sms)
        if smspath in self.Messages():
            return MMModemSms(smspath)
        return None
    
    def delete(self, sms):
        smspath = None
        if isinstance(sms, MMModemSms):
            smspath = sms.get_object_path()
        else:
            smspath = ModemManagerObject.object_path('SMS', sms)
        if smspath in self.Messages():
            self.interface.Delete(dbus.ObjectPath(smspath))
    
    def signal_added(self, handler = message_added):
        self.setup_signal('Added', handler)


class ModemManager(ModemManagerObject):

    modems = None

    def __init__(self):
        # https://www.freedesktop.org/software/ModemManager/api/latest/ref-dbus-bus-name.html
        # https://www.freedesktop.org/software/ModemManager/api/latest/ref-dbus-object-manager.html
        super(ModemManager, self).__init__(obj_path='/org/freedesktop/ModemManager1')
        self.modems = self.get_modems_list()

    # return list of modem object paths
    def get_modems_list(self):
        modems = []
        # https://www.freedesktop.org/software/ModemManager/api/latest/ref-dbus-standard-interfaces-objectmanager.html
        for p in self.get_objmanager_objects():
            if isinstance(p, dbus.ObjectPath):
                modems += [str(p)]
        return modems

    # return MMModem object for specified modem (if exists)
    def get_modem(self, modem):
        mpath = ModemManagerObject.object_path('Modem', modem)
        if mpath in self.modems:
            return MMModem(mpath)
        return None

    # get MMModem object for first modem from list of installed in the system
    def get_first(self):
        if self.modems:
            return self.get_modem(self.modems[0])
        return None

    # filter existing modems by some value matching to Modem property
    # if value is not provided - return first modem from the list
    # if filtered only one modem - return its MMModem object
    # otherwise - return list of MMModem objects for filtered modems
    def get_modem_by(self, name = 'OwnNumbers', value = None):
        if value is None:
            return self.get_first()
        elif name in ['Manufacturer', 'Model', 'EquipmentIdentifier',
                      'OwnNumbers', 'PrimaryPort', 'State']:
            modems = list(
                        filter(lambda x: value in x.get_property(name),
                            map(lambda x: MMModem(x), self.modems)))
            if len(modems) == 1:
                return modems[0]
            return modems
        return None

def main():
    
#    DBusGMainLoop(set_as_default=True)
    
    mm = ModemManager()
    m = mm.get_first()
    
    if m:
        ms = MMModemMessaging(m)
#        ms.signal_added()

        cnt = 0
        messages = ms.get_sms()
        if len(messages) > SMS_STORE_COUNT:
            for m in messages:
                print("%s (%s): %s" % (m.Number(), m.get_date(), m.Text()))
                cnt += 1
                if cnt > SMS_STORE_COUNT:
                    m.save()
                    ms.delete(m)

#        MainLoop().run()

main()