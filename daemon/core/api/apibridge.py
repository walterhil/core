#
# CORE
# Copyright (c)2016 the Boeing Company.
# See the LICENSE file included in this distribution.
#
# authors: Rod Santiago
#          John Kharouta
#



import core_pb2
import struct, threading, traceback, sys
from core.api import coreapi, corewrapper
from core.experiments import ExperimentStore

wrapper = corewrapper
legacy = coreapi

API2HDRFMT = "H"
API2HDRSIZ = struct.calcsize(API2HDRFMT)
   



class CoreApiBridge(object):
    
    def __init__(self, handler):
        # The collector is used for gathering node messages sent by the core session, 
        # for example, during INSTANTIATION as nodes are started until RUNTIME.
        self.collector = None

        # The currently associated (added or joined) experiment
        self.assocExperiment = None

        # Mutex
        self.lock = threading.Lock()

        # Reference to the owning handler in the core-daemon
        self.handler = handler


    def recvmsg(self):
        ''' Receive data, parse a CoreMessage and queue it onto an existing
        session handler's queue, if available.
        '''

        try:
            hdr = self.handler.request.recv(API2HDRSIZ)
        except Exception, e:
            raise IOError, "error receiving API 2 header (%s)" % e

        if len(hdr) != API2HDRSIZ:
            if len(hdr) == 0:
                raise EOFError, "client disconnected"
            else:            
                raise IOError, "invalid message header size"
                
        dataToRead = struct.unpack(API2HDRFMT, hdr)[0]
        data = ""
        while len(data) < dataToRead:
            data += self.handler.request.recv(dataToRead - len(data))

        msgs = self.processApi2Message(data)

        return msgs

    def dispatchreplies(self, replies):
        ''' Dispatch a reply to a previously received message.
        '''
        api2Replies = self.processLegacyCoreMessage(replies)
        if api2Replies:
            for reply in api2Replies:
                try:
                    # send to API2 client 
                    self.handler.request.sendall(reply)
                except Exception, e:
                    self.warn("Error sending reply data: %s" % e)


    def sendall(self, data):
        ''' The daemon calls this method with legacy API data. Convert first
        API2 then send.
        '''

        try:
            msgs = self.processLegacyCoreMessage((data,))
            if msgs:
                for msg in msgs:
                    self.handler.request.sendall(msg)
        except Exception, e:
            print "-"*60
            traceback.print_exc(file=sys.stdout)
            print "-"*60
            raise e





    def processApi2Message(self, data):
        message = core_pb2.CoreMessage()
        message.ParseFromString(data)
        if message.HasField('session'):
            return self.processApi2SessionMsg(message.session,
                                                       message.purpose)
        if message.HasField('experiment'):
            return self.processApi2ExperimentMsg(message.experiment, 
                                                 message.purpose)
        if message.HasField('event'):
            return self.processApi2Event(message.event, 
                                         message.purpose)
            
    def processLegacyCoreMessage(self, messages):
        api2msgs = []
        for msgstr in messages:
            # Unpack the message
            parser = wrapper.CoreMessageParser(msgstr)
            if parser.getType() == legacy.CORE_API_REG_MSG:
                regMsg = parser.createWrapper()
                '''
                print "RegisterMessage"
                print "\twireless=", regMsg.getWireless()
                print "\tmobility=", regMsg.getMobility()
                print "\tutility=", regMsg.getUtility()
                print "\texec=",  regMsg.getExecsrv()
                print "\tgui=", regMsg.getGui()
                print "\temul=", regMsg.getEmulsrv()
                print "\tsess=", regMsg.getSession()
                '''
            elif parser.getType() == legacy.CORE_API_SESS_MSG:
                sessMsg = parser.createWrapper()
                '''
                print "SessionMessage"
                print "\tnumber=",  sessMsg.getNumber()
                print "\tname=",  sessMsg.getName()
                print "\tfile=",  sessMsg.getFile()
                print "\tnodecount=",  sessMsg.getNodecount()
                print "\tdate=",  sessMsg.getDate()
                print "\tthumb=",  sessMsg.getThumb()
                print "\tuser=",  sessMsg.getUser()
                print "\topaque=",  sessMsg.getOpaque()
                '''
                sessions = sessMsg.getNumber().split("|")
                port_num = int(sessions[0])
                newMsg = core_pb2.CoreMessage()
                newMsg.session.clientId = 'client' + sessions[0]
                newMsg.session.port_num = port_num

                # List active experiments in the server
                '''
                for sid in sessions:
                    sid = int(sid)
                    if sid == 0:
                        continue
                    session = session.server.getsession(sessionid=sid, useexisting=True)
                    if session is None:
                        print "Invalid session ID received from daemon"
                        continue
                    if hasattr(session, 'experiment'):
                        newMsg.session.all_exps.add(session.experiment.id)
                    else:
                        newMsg.session.all_exps.add(str(sid))
                '''

                newMsg.purpose = core_pb2.ADD
                api2msgs.append(CoreApiBridge.packApi2(newMsg))
            elif parser.getType() == legacy.CORE_API_EVENT_MSG:
                event = parser.createWrapper()
                '''
                print "Event:"
                print "\tnode=", event.getNode()
                print "\ttype=", event.getType()
                print "\tname=", event.getName()
                print "\tdata=", event.getData()
                print "\ttime=", event.getTime()
                print "\tsessions=", event.getSession()
                '''
                if event.getType() == legacy.CORE_EVENT_RUNTIME_STATE:
                    newMsg = core_pb2.CoreMessage()
                    newMsg.purpose = core_pb2.STATE_CHANGE
                    newMsg.event.state = core_pb2.RUNTIME
                    api2msgs.append(CoreApiBridge.packApi2(newMsg))
                    with self.lock:
                        if self.collector:
                            self.collector.experiment.running = True
                        else:
                            raise RuntimeError, "runtime entered without an instantiated experiment"
                        api2msgs.append(CoreApiBridge.packApi2(self.collector))
                        self.collector = None

            elif parser.getType() == legacy.CORE_API_NODE_MSG:
                node = parser.createWrapper()
                print "Node:"
                print "\tnumber=", node.getNumber()
                print "\ttype=", node.getType()
                print "\tname=", node.getName()
                print "\tipaddr=", node.getIpaddr()
                print "\tmacaddr=", node.getMacaddr()
                print "\tip6addr=", node.getIp6addr()
                print "\tmodel=", node.getModel()
                print "\temusrv=", node.getEmusrv()
                print "\tsession=", node.getSession()
                print "\txpos=", node.getXpos()
                print "\typos=", node.getYpos()
                print "\tcanvas=", node.getCanvas()
                print "\temuid=", node.getEmuid()
                print "\tnetid=", node.getNetid()
                print "\tservices=", node.getServices()
                print "\tlat=", node.getLat()
                print "\tlon=", node.getLong()
                print "\talt=", node.getAlt()
                print "\ticon=", node.getIcon()
                print "\topaque=", node.getOpaque()
                '''
                if handler.session.getstate() == legacy.CORE_EVENT_INSTANTIATION_STATE:
                '''

                api2_node=None
                api2_dev=None
                with self.lock:
                    for a_node in self.assocExperiment.nodes:
                        if a_node.idx == node.getNumber():
                            api2_node = core_pb2.Node()
                            break
                    if not api2_node:
                        for a_device in self.assocExperiment.devices:
                            if a_device.idx == node.getNumber():
                                api2_dev = core_pb2.Device()
                                break
                    if api2_node:
                        api2_obj = api2_node
                    else:
                        api2_obj = api2_dev

                    if not api2_obj:
                        raise RuntimeError, "Node %d not in experiment" % (node.getNumber())

                    api2_obj.idx = node.getNumber()
                    if node.getEmuid() is not None: api2_obj.emu_id=node.getEmuid()
                    if node.getName() is not None:  api2_obj.name=node.getName()
                    if node.getXpos() is not None:  api2_obj.location.x_pos=node.getXpos()
                    if node.getYpos() is not None:  api2_obj.location.y_pos=node.getYpos()

                    if self.collector:
                        if api_node:
                            self.collector.experiment.nodes.add().CopyFrom(api_node)
                        else:
                            self.collector.experiment.devices.add().CopyFrom(api_device)
                        
                newMsg = core_pb2.CoreMessage()
                newMsg.purpose = core_pb2.MODIFY
                if api_node:
                    newMsg.node = api_node
                else:
                    newMsg.device = api_device
                api2msgs.append(CoreApiBridge.packApi2(newMsg))

            else:
                print "received message type", parser.getType()
        return api2msgs

    @staticmethod
    def packApi2(message):
        ''' Pack an API2 message for transmission
        '''
        data = message.SerializeToString()
        return struct.pack(API2HDRFMT, len(data)) + data

    def processApi2SessionMsg(self, message, purpose):
        print 'Received session request message'
        if purpose == core_pb2.ADD:
            legacymsgs = []
            legacymsgs.append(wrapper.RegMsg.instantiate(0, gui='true'))
            return legacymsgs
            # The response will be sent to the API2 client when a legacy session message is received from the daemon
        elif purpose == core_pb2.DELETE:
            # TODO: shutdown session
            pass
        else:
            print 'Received invalid purpose for SESSION'


    def processApi2ExperimentMsg(self, exp, purpose):
        if purpose == core_pb2.ADD:
            if ExperimentStore.addExperiment(exp):
                response = core_pb2.CoreMessage()
                response.experiment.experimentId = exp.experimentId;
                response.purpose = purpose

                # Start a collector for gathering node messages instantiated in the core session
                with self.lock:
                    if not self.collector:
                        self.assocExperiment = exp
                        self.collector = response
                    else:
                        raise RuntimeError, "Instantiation of experiment while another is active"
                self.handler.request.sendall(CoreApiBridge.packApi2(response)) # TODO: Fix this
                return self.translateApi2ExperimentMsg(exp)
            else:
                return self.Api2Error("unable to add experiment")
        elif purpose == core_pb2.MODIFY:
            # Detect if a change in state is requested
            if exp.HasField('running'):
                if exp.running:
                    # TODO: Check for a state transition
                    # transition to instantiation state (legacy)
                    msgs = []
                    msgs.append(wrapper.EventMsg.instantiate(
                        legacy.CORE_EVENT_INSTANTIATION_STATE))
                    return msgs
                else:
                    # TODO: Check for transition from running to not running
                    # transition to data collection state (legacy)
                    msgs = []
                    msgs.append(wrapper.EventMsg.instantiate(
                        legacy.CORE_EVENT_DATACOLLECT_STATE))
                    return msgs
            else:
                print "Unsupported experiment modification received"


    def translateApi2ExperimentMsg(self, message):
        print 'Received experiment message'
        msgs = []
        # Flag need to be 0 otherwise CORE will not enter runtime state (per JavaAdaptor, need verification)
        msgs.append(wrapper.SessionMsg.instantiate(
            0, "0", 
            nodecount=str(len(message.nodes) + len(message.devices))))
        # Quickly transition through the definition and configuration states
        msgs.append(wrapper.EventMsg.instantiate(
            legacy.CORE_EVENT_DEFINITION_STATE))
        msgs.append(wrapper.EventMsg.instantiate(
            legacy.CORE_EVENT_CONFIGURATION_STATE))

        # Send location
        # TODO: Add this info to the Experiment
        msgs.append(wrapper.ConfMsg.instantiate(obj="location",
                                                dataTypes=(9,9,9,9,9,9),
                                                dataValues='0|0| 47.5766974863|-122.125920191|0.0|150.0'))

        # TODO
        # Send control net configuration
        # send node types
        # send services

        # send nodes
        devices = {}
        for node in message.nodes:
            if node.idx in devices:
                raise IOError, "received experiment with node/device duplicates"
            devices[node.idx] = node
            # TODO: Add other fields
            msgs.append(wrapper.NodeMsg.instantiate(
                legacy.CORE_API_ADD_FLAG|legacy.CORE_API_STR_FLAG,
                node.idx,
                str(node.name)))

        for device in message.devices:
            if device.idx in devices:
                raise IOError, "received experiment with node/device duplicates"
            devices[device.idx] = device
            # TODO: Add other fields
            msgs.append(wrapper.NodeMsg.instantiate(
                legacy.CORE_API_ADD_FLAG|legacy.CORE_API_STR_FLAG,
                device.idx,
                str(device.name),
                type = legacy.CORE_NODE_SWITCH)) # TODO: Update this later

        for network in message.networks:
            for channel in network.channels:
                if len(channel.endpoints) == 2:
                    ep0 = channel.endpoints[0]
                    ep1 = channel.endpoints[1]
                    if ep0.dev_idx not in devices or ep1.dev_idx not in devices:
                        raise IOError, "received channel message with invalid first endpoint device (%d)" % (ep0.dev_idx)
                    if ep1.dev_idx not in devices:
                        raise IOError, "received channel message with invalid second endpoint device (%d)" % (ep1.dev_idx)
                    if ep0.intf_idx in devices[ep0.dev_idx].interfaces:
                        raise IOError, "received channel message with invalid first endpoint interface (%d)" % (ep0.intf_idx)
                    if ep1.intf_idx in devices[ep1.dev_idx].interfaces:
                        raise IOError, "received channel message with invalid second endpoint interface (%d)" % (ep1.intf_idx)

                    if0 = devices[ep0.dev_idx].interfaces[ep0.intf_idx]
                    if1 = devices[ep1.dev_idx].interfaces[ep1.intf_idx]
                    
                    msgs.append(wrapper.LinkMsg.instantiate(legacy.CORE_API_ADD_FLAG,
                                                            ep0.dev_idx,ep0.intf_idx,
                                                            ep1.dev_idx,ep1.intf_idx,
                                                            if1ip4=if0.ip4_addr if if0.HasField("ip4_addr") else None, 
                                                            if2ip4=if1.ip4_addr if if1.HasField("ip4_addr") else None))
                                                       
        # TODO
        # send metadata

        return msgs


    def processApi2Event(self, event, purpose):
        print 'Received event'




