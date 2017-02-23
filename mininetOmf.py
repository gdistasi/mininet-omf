#!/usr/bin/python

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import Intf
from mininet.node import OVSSwitch
from mininet.node import OVSController
from mininet.node import OVSKernelSwitch
from mininet.nodelib import LinuxBridge
from mininet.node import Host
from functools import partial
from shutil import copyfile
import fileinput
import time


from xml.dom import minidom
import mysql.connector

setLogLevel( 'info' )

#c0 = OVSController( 'c0', port=6633 )



class OMFInventory:
    
    def __init__(self):
        self.cnx = mysql.connector.connect(user='root', password='password',
                              host='127.0.0.1',
                              database='inventory')    
        self.cursor = self.cnx.cursor()
        self.cursor.execute("truncate testbeds;")
        self.cursor.execute("truncate nodes;")
        self.cursor.execute("truncate locations;")
    
        self.cursor.execute("INSERT into testbeds (name) values (\"mininet\");")
  
  
    def close(self):    
        self.cursor.close()
        self.cnx.close()


    def addNode(self, name, idn, ip, mac):
        updateLocation = ("INSERT into locations (name, testbed_id, id, switch_ip, switch_port)  "
                     "VALUES (%(hostname)s, 1, %(id)s, \" \", 0)" ) 
  
        dataLocation = {
            'hostname': name,
            'id': idn
        }
        
        self.cursor.execute(updateLocation, dataLocation)
  
        updateNode = ("INSERT into nodes (control_ip, control_mac, hostname, inventory_id, motherboard_id, location_id, disk, hrn)  "
                     "VALUES (%(control_ip)s, %(control_mac)s, %(hostname)s, 1, 0, %(location_id)s, \" \", %(hostname)s)" ) 
  
        dataNode = {
                'control_ip': ip,
                'control_mac': mac,
                'hostname': name,
                'location_id': idn
        }
        
        self.cursor.execute(updateNode, dataNode)


def setIps(nodes):
    
    i=0
    for n in nodes:
        intfs=n.intfs
        for ifn in intfs:
            if "wlan" in intfs[ifn].name:
                n.cmd("ifconfig %s 0.0.0.0 up" %intfs[ifn].name)
            else:
                n.cmd("ifconfig %s 10.0.0.%d up" %(intfs[ifn].name, i+1))
                      
        i+=1

def renameIface(node, intf, newname):
        "Rename interface"
        node.pexec('ifconfig %s down' % intf)
        node.pexec('ip link set %s name %s' % (intf, newname))
        node.pexec('ifconfig %s up' % newname)

def StartSshDaemons(nodes):
    pids=[]
    for n in nodes:
        pp=n.popen(["/usr/sbin/sshd"])
        pids.append(pp.pid) 
    return pids
        
def StopSshDaemons(expc, pids):
    for p in pids:
        expc.cmd("killall sshd")
        
    time.sleep(3)    
        
    for p in pids:
        expc.cmd("kill -9 sshd")



def renameInterfaces(nodes):
    for node in nodes:
        numEth=0
        numWlan=0
        for ifn in node.intfs:
            ifname=node.intfs[ifn].name
            if "eth" in ifname:
                newname="eth%d" %numEth
                renameIface(node, ifname, newname)
                numEth+=1
                node.intfs[ifn].name=newname
                node.nameToIntf[ifn]=None
                node.nameToIntf[newname]=node.intfs[ifn]
            elif "wlan" in ifname:
                newname="wlan%d" %numWlan
                renameIface(node, ifname, newname)
                numWlan+=1
                node.intfs[ifn].name=newname
                node.nameToIntf[ifn]=None
                node.nameToIntf[newname]=node.intfs[ifn]



def getControlIf(node):
    ctrlif=""
    
    for ifn in node.intfs:
        if "eth" in node.intfs[ifn].name:
            ctrlif=node.intfs[ifn].name
            
    return ctrlif
        



def configureAndStartOmf(expc, nodes):
    pids=[]
    files=[]
    
    expc.cmd("/etc/init.d/omf-aggmgr-5.4 start")
    
    pidsFile=open("/tmp/omfResctlPids", "w+")
    
    
    
    
    for n in nodes:
        name=n.name
        confFile="omf-resctl-%s.yaml" %name
        destFile = open(confFile , 'a' )

        for line in fileinput.input( "omf-resctl.mininet.yaml" ):
            line=line.replace("%hostname%", name).replace("%control_if%", getControlIf(n))
            destFile.write( line )

        destFile.close()
        
        log="omf-resctl-%s.log" %name
        flog=open(log,"w+")
        pr=n.popen(["omf-resctl-5.4", "-C", confFile, "--log stdout"], stdout=flog, stderr=flog)
                    #, "--log","omf-resctl-%s.log" %name ])
        pids.append(pr.pid)
        
        
        pidsFile.write("%d\n" % pr.pid )
        files.append(flog)
        
        
    return {'omfPids':pids, "logFiles":files}


def topology():
    "Create a network."
    
    
    privateDirs = [ ( '/var/log', '/tmp/%(name)s/var/log' ),
                    ( '/var/run', '/tmp/%(name)s/var/run' ),
                    ( '/etc/omf-resctl-5.4', '/tmp/%(name)s/etc/omf-resctl-5.4') ]
    
    #host = partial( Host,
    #                privateDirs=privateDirs )
    
    net = Mininet(  )

   
    print "*** Creating nodes"

    omf = OMFInventory()

    #omf EXP controller
    expc = net.addHost( 'expc' , ip="10.0.0.200",
                             inNamespace=False )

  
    xmldoc = minidom.parse('topology.xml')

    itemlist = xmldoc.getElementsByTagName('node')

    nodes=[]
    for s in itemlist:
        name = s.attributes['name'].value
        if "." in name:
            name = name[0:name.index('.')].replace('-','x')
        ifns=s.getElementsByTagName('interface')
        nRadios = ifns.length
        sta=net.addStation(name, wlans=nRadios)
        nodes.append(sta)
        
        
        
    print "*** Configuring wifi nodes"
    net.configureWifiNodes()
    
    s1=net.addSwitch("s1", cls=LinuxBridge)
    net.addLink( s1, expc )
    
    for n in nodes:
        net.addLink(s1,n)
    
    i=0
    for s in itemlist:
        sta=nodes[i]
        
        ifns=s.getElementsByTagName('interface')
    
        #adding interfaces to the node (in adhoc mode)
        for ifn in ifns:
            ch = ifn.getElementsByTagName('channel')[0].firstChild.data
            essid =  ifn.getElementsByTagName('essid')[0].firstChild.data
            mode = ifn.getElementsByTagName('mode')[0].firstChild.data
            
            if (mode=="adhoc"):
                net.addHoc(sta, ip='0.0.0.0', ssid='meshnet', mode="a", channel='%d' % int(ch))
            elif (mode=="station"):
                net.addHoc(sta, ip='0.0.0.0', ssid='meshnet', mode="a", channel='%d' % int(ch))
            elif (mode=="master"):
                net.addHoc(sta, ip='0.0.0.0', ssid='meshnet', mode="a", channel='%d' % int(ch))
            else:
                print "ERROR."
                abort()
            
            
        
        omf.addNode(sta.name, i, "10.0.0.%d"  %(i+1), "00:00:00:00:00:00")
        i+=1
            
  
    
    omf.close()
    
    print "*** Starting network"
    net.build()
    net.start()

    setIps(nodes)
    
    renameInterfaces(nodes)
    
    ret=configureAndStartOmf(expc, nodes)
    pids=ret['omfPids']
    logFi=ret['logFiles']
  
    sshPids=StartSshDaemons(nodes)
  
    print "*** Running CLI"
    CLI( net )


    for p in pids:
        expc.cmd("kill %d" %p)
    
    time.sleep(3)
    
    for p in pids:
        expc.cmd("kill -9 %d" %p)
    
    for f in logFi:
        f.close()
    
    StopSshDaemons(expc,sshPids)
    
    expc.cmd("/etc/init.d/omf-aggmgr-5.4 stop")
    
    print "*** Stopping network"
    net.stop()

    
    
if __name__ == '__main__':
    setLogLevel( 'info' )
    topology()

