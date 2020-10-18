#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Author: Chaddy Huussin <chaddy.hv@gmail.com>"

import os
import shutil
import random
import string
import json
import time
import argparse
import logging
import requests
import tarfile
import subprocess
from datetime import datetime

logging.basicConfig(format="%(levelname)s [%(asctime)s] %(message)s", level=logging.INFO)

SNIFF = "tshark -i lo -f  \"{}\" -n -q -w {} 2>&1 &"
GETH_PARAMS = "{} {} --datadir {} --nodiscover --verbosity 5 --networkid 31337 {} --rpc --rpcaddr 127.0.0.1 --rpcport {} --rpcapi admin,db,eth,debug,miner,net,shh,txpool,personal,web3,quorum,{}  --emitcheckpoints --port {} >> {}/node.log 2>&1 &"
GETH_ADD_RAFT = "{} attach {}/geth.ipc --exec \"raft.addPeer('{}')\""
GETH_EXECUTE_RPC = "{} attach {}/geth.ipc --exec \"{}\""
GETH_UNLOCK_ACCOUNT = "{} attach {}/geth.ipc -exec \"web3.personal.unlockAccount('{}', '{}')\""
ISTANBUL_SETUP_NETWORK = "setup --num {} --nodes --quorum --save --verbose"

RES = os.getenv("RES_PATH", os.path.join(os.path.dirname(os.path.join(os.path.realpath(__file__))), 'res'))
GETH = os.getenv("GETH_PATH", os.path.join(RES, 'bin', 'geth'))
GETH_DEBUG = os.getenv("GETH_DEBUG_PATH", os.path.join(RES, 'bin', 'geth-debug'))
GO_DEBUGGER = os.getenv("GO_DEBUGGER_PATH", os.path.join(RES, 'bin', 'gdlv'))
ISTANBUL = os.getenv("ISTANBUL_PATH", os.path.join(RES, 'bin', 'istanbul'))
TESSERA = os.getenv("TESSERA_PATH", os.path.join(RES, 'bin', 'tessera.jar'))
BOOTNODE = os.getenv("BOOTNODE_PATH", os.path.join(RES, 'bin', 'bootnode'))

# Arguments
parser = argparse.ArgumentParser(description='Quorum Network Maker')

parser.add_argument('--stop', action='store_true', help="Stop Existing Network")
parser.add_argument('--raft', action='store_true', default=True, help="Bootstrap raft network")
parser.add_argument('--istanbul', action='store_true', default=False, help="Bootstrap istanbul network")
parser.add_argument('--run', action='store_true', help="Run Existing Network")
parser.add_argument('--buildRaft', action='store_true', help="Build raft network")
parser.add_argument('--restartPrivacy', action='store_true', help="Restart Tessera Network")
parser.add_argument('--skipGeth', type=str, help="skip running geth instead print formed command. Use comma separation for multiple nodes(ex, 1,2,3,4)  or '*' for all nodes")
parser.add_argument('--debug', type=str, help="Rung golang binary Debug for specified nodes. Use comma separation for multiple nodes(ex, 1,2,3,4)  or '*' for all nodes")
parser.add_argument('--sniff', action='store_true', help="Sniff network traffic")
parser.add_argument('--sniffClear', action='store_true', help="Clearn sniffing data")
parser.add_argument('--sniffName', type=str, default='', help="Sniff session name. Time format if not set")
parser.add_argument('--sniffStop', action='store_true', help="Stop traffic sniffing")
parser.add_argument('--reset', action='store_true', help="Reset chain information")
parser.add_argument('--getContracts', action='store_true', help="Get Information about all the contracts in the network")
parser.add_argument('--container', action='store_true', help="Build Docker container based infrastructure. NOT IMPLEMENTED YET")
parser.add_argument('--containerServer', type=str, default='unix://var/run/docker.sock', help="Docker server location")
parser.add_argument('--contract', type=str, help='Path to contract to deploy. This is contract.sol file')
parser.add_argument('--account', type=str, help='An existing ethereum account address to use to deploy contract from. if not set a random one will be picked')
parser.add_argument('--password', type=str, help='An existing ethereum account password')
parser.add_argument('--sender', type=str, help='The node index to use as sender of the transaction. if not set a random one will be picked')
parser.add_argument('--contractsOf', type=str, help='Show all contract creation transaction of account')
parser.add_argument('--transactionsOf', type=str, help='Show Accounts Transactions')
parser.add_argument('--privateFor', type=str, help='Nodes index to use (ex. 1,2,3,4). will set privateFor to its the geth tx manager addresses for each node')
parser.add_argument('--info', action='store_true', help="Print information information")
parser.add_argument('--build', action='store_true', help="Build Network")
parser.add_argument('--private', action='store_true', help="Build With Privacy feature enabled")
parser.add_argument('--permissioned', action='store_true', help="Build With Permission feature nabled")
parser.add_argument('--size', type=int, default=7, help="Network size")
parser.add_argument('--accounts', type=int, default=8, help="Total number of Accounts")
parser.add_argument('--workspace', type=str, default='workspace', help="Network workspace folder")
parser.add_argument('--ether', type=int, default=1000000000000000000000000000, help="Initial Account Funding Value")
parser.add_argument('--raftStartPort', type=int, default=50400, help="Raft Start Port")
parser.add_argument('--gethStartPort', type=int, default=21000, help="Geth peering Start Port")
parser.add_argument('--rpcStartPort', type=int, default=22000, help="RPC Start Port")
parser.add_argument('--txTpStartPort', type=int, default=9080, help="Tessera Third Party Start Port")
parser.add_argument('--tesserDebugPortStart', type=int, default=6900, help="Tessera Debug port start")
parser.add_argument('--txQtStartPort', type=int, default=22000, help="Tessera Quorum Transaction Start Port")
parser.add_argument('--txPpStartPort', type=int, default=9000, help="Tessera Peer Network Start Port")
parser.add_argument('--istanbulStartPort', type=int, default=30300, help="Istanbul start port")
parser.add_argument('--gethParams', type=str, default="", help="Additional geth parameters")
parser.add_argument('--update', action="store_true", help="Update binaries")

# Collect Arguments
args = parser.parse_args()

def download(src, dst):
    r = requests.get(src, allow_redirects=True)
    open(dst, 'wb').write(r.content)


def extract(src, dst):
    my_tar = tarfile.open(src)
    my_tar.extractall(dst)
    my_tar.close()
    
if args.update:
    ## Tessera https://oss.sonatype.org/service/local/repositories/releases/content/com/jpmorgan/quorum/tessera-app/0.10.6/tessera-app-0.10.6-app.jar
    ## Quorum https://bintray.com/quorumengineering/quorum/download_file?file_path=v2.7.0/geth_v2.7.0_darwin_amd64.tar.gz
    ## Istanbul https://bintray.com/api/ui/download/quorumengineering/istanbul-tools/istanbul-tools_v1.0.3_darwin_amd64.tar.gz
    ## Bootnode https://bintray.com/api/ui/download/quorumengineering/geth-bootnode/bootnode_v1.9.7_darwin_amd64.tar.gz
    logging.info("updating {}".format(VERSIONS))
    if not os.path.exists(".siteth-tmp"):
        os.mkdir(".siteth-tmp")

    geth_path = "https://bintray.com/quorumengineering/quorum/download_file?file_path=v{}/geth_v{}_darwin_amd64.tar.gz".format(VERSIONS['geth'], VERSIONS['geth'])
    tessera_path = "https://oss.sonatype.org/service/local/repositories/releases/content/com/jpmorgan/quorum/tessera-app/{}/tessera-app-{}-app.jar".format(VERSIONS['tessera'], VERSIONS['tessera'])
    istanbul_path = "https://bintray.com/api/ui/download/quorumengineering/istanbul-tools/istanbul-tools_v{}_darwin_amd64.tar.gz".format(VERSIONS['istanbul'])
    bootnode_path = "https://bintray.com/api/ui/download/quorumengineering/geth-bootnode/bootnode_v{}_darwin_amd64.tar.gz".format(VERSIONS['bootnode'])

    logging.info("Downloading {}".format(geth_path))
    download(geth_path,".siteth-tmp/geth.tar.gz")
    extract(".siteth-tmp/geth.tar.gz","./res/bin")

    logging.info("Downloading {}".format(tessera_path))
    download(tessera_path, "./res/bin/tessera.jar")

    logging.info("Downloading {}".format(istanbul_path))
    download(istanbul_path,".siteth-tmp/istanbul.tar.gz")
    extract(".siteth-tmp/istanbul.tar.gz","./res/bin")

    logging.info("Downloading {}".format(bootnode_path))
    download(bootnode_path, ".siteth-tmp/bootnode.tar.gz")
    extract(".siteth-tmp/bootnode.tar.gz", "./res/bin")

    shutil.rmtree(".siteth-tmp")

if not args.skipGeth:
    args.skipGeth = []
else:
    args.skipGeth = args.skipGeth.split(',')

if args.istanbul:
    args.raft = False

if not args.build and not os.path.exists(os.path.abspath(args.workspace)):
    logging.warning("Workspace can't be found".format(args.workspace))
    exit(0)

if args.build and args.raft:
    # 1 - Generate workspace structure
    logging.info('Generating Workspace')
    # Clean workspace if exists
    if os.path.exists(args.workspace):
        shutil.rmtree(args.workspace)

    # Generate workspace folders tree
    os.mkdir(args.workspace)
    os.mkdir(os.path.join(args.workspace, 'net-info'))
    os.mkdir(os.path.join(args.workspace, 'net-info', 'tessera'))
    os.mkdir(os.path.join(args.workspace, 'net-info', 'traffic'))
    os.mkdir(os.path.join(args.workspace, 'net-info', 'helpers'))
    os.mkdir(os.path.join(args.workspace, 'net-info', 'accounts'))
    [os.mkdir(os.path.join(args.workspace, 'node-{}'.format(o))) for o in range(1, args.size + 1)]

    # 2 - Generate accounts
    logging.info('Generating Accounts')
    # Generate passwords
    for account in range(1, args.accounts + 1):
        with open(os.path.join(args.workspace, 'net-info', 'accounts', 'account-{}.pass'.format(account)),
                  'w') as passFile:
            passFile.write(''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)]))

    # Generate Accounts
    accounts = []
    for account in range(1, args.accounts + 1):
        accountAddress = str(os.popen("{} --datadir {} account new --password {}".format(GETH,
                                                                                         os.path.join(os.path.abspath(
                                                                                             args.workspace),
                                                                                             'net-info'),
                                                                                         os.path.join(os.path.abspath(
                                                                                             args.workspace),
                                                                                             'net-info',
                                                                                             'accounts',
                                                                                             'account-{}.pass'.format(
                                                                                                 account)))
                                      ).read()).replace("Address: {", "").replace("}", "").replace("\n", "")

        accountAddress = accountAddress.replace("Your new key was generatedPublic address of the key:   ", "").replace(
            "Path of the secret key file", "")
        if ":" in accountAddress:
            accountAddress = accountAddress.split(":")[0]

        if not accountAddress.startswith("0x"):
            accountAddress = "0x{}".format(accountAddress)

        with open(os.path.join(args.workspace, 'net-info', 'accounts', 'account-{}.pass'.format(account)),
                  'r') as passFile:
            accountPassword = passFile.read()
            accounts.append({'account': accountAddress, 'pass': accountPassword})

    with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'accounts.json'), 'w') as accountsFile:
        accountsFile.write(json.dumps(accounts))
        shutil.rmtree(os.path.join(os.path.abspath(args.workspace), 'net-info', 'accounts'))
        os.mkdir(os.path.join(os.path.abspath(args.workspace), 'net-info', 'accounts'))
        for account in accounts:
            with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'accounts',
                                   '{}.pass'.format(account['account'].replace('0x', ''))), 'w') as passWrite:
                passWrite.write(account['pass'])
    # Copy keystore
    for node in range(1, args.size + 1):
        shutil.copytree(os.path.join(os.path.abspath(args.workspace), 'net-info', 'keystore'),
                        os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node), 'keystore'))

    # Generate Genesis file
    logging.info("Generate Genesis file")
    genesis = {}
    with open(os.path.join(RES, 'other', 'genesis.json')) as genesisFile:
        genesis = json.load(genesisFile)
        for o in accounts:
            genesis['alloc'][o['account'].replace('0x', '')] = {"balance": '{}'.format(args.ether)}
        with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'genesis.json'), 'w') as genWriter:
            json.dump(genesis, genWriter)

    # Generate Node Keys
    logging.info("Generate Nodes Keys")
    for node in range(1, args.size + 1):
        os.popen("{} --genkey={}".format(BOOTNODE, os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node),
                                                                'nodekey')))

    logging.info("Generate Enodes")
    staticNodes = []
    for node in range(1, args.size + 1):
        if not os.path.exists(os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node), 'nodekey')):
            time.sleep(1)
        os.popen("{} --nodekey={}/nodekey --writeaddress > {}/enode".format(
            BOOTNODE,
            os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node)),
            os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node))
        ))

    logging.info("Generate static-nodes.json")
    endode = 'enode://{}@127.0.0.1:{}?discport=0&raftport={}&rpcport={}'
    raftPort = args.raftStartPort
    rpcPort = args.rpcStartPort
    gethStartPort = args.gethStartPort

    time.sleep(1)
    for node in range(1, args.size + 1):
        raftPort = raftPort + 1
        rpcPort = rpcPort + 1
        gethStartPort = gethStartPort + 1
        with open(os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node), 'enode'), 'r') as enodeReader:
            enode = enodeReader.read().replace('\n', '')
            staticNodes.append(endode.format(enode, gethStartPort, raftPort, rpcPort))
    with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'static-nodes.json'), 'w') as staticWriter:
        staticWriter.write(json.dumps(staticNodes))

    for node in range(1, args.size + 1):
        shutil.copy(os.path.join(os.path.abspath(args.workspace), 'net-info', 'static-nodes.json'),
                    os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node), 'static-nodes.json'))

    if args.permissioned:
        logging.info("Generate permissioned-nodes.json")
        with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'permissioned-nodes.json'),
                  'w') as permissionWriter:

            permissioned = [entry.split("?")[0] for entry in staticNodes]
            permissionWriter.write(json.dumps(permissioned))

        for node in range(1, args.size + 1):
            logging.info("Generate permissioned entries for node-{}".format(node))
            shutil.copy(os.path.join(os.path.abspath(args.workspace), 'net-info', 'permissioned-nodes.json'),
                        os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node),
                                     'permissioned-nodes.json'))

    logging.info("Write genesis states")
    for node in range(1, args.size + 1):
        os.popen("{} --datadir {} init {}/genesis.json".format(
            GETH,
            os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node)),
            os.path.join(os.path.abspath(args.workspace), 'net-info'))
        ).read()

if args.sniffClear:
    os.popen("killall -9 tshark 2>&1")
    logging.info("Clear Traffic information")
    shutil.rmtree(os.path.join(os.path.abspath(args.workspace), 'net-info', 'traffic'))
    os.mkdir(os.path.join(os.path.abspath(args.workspace), 'net-info', 'traffic'))
    logging.info("Traffic information was cleared")
if args.stop:
    logging.info("Stoping Network")
    os.popen("killall -9 geth 2>&1")
    os.popen("killall java 2>&1")
    os.popen("killall tshark 2>&1")
    os.popen("killall gdlv 2>&1")
    os.popen("killall -9 geth-debug 2>&1")
    logging.info("Network processes has been terminated")

if args.restartPrivacy:
    logging.info("Stopping privacy network")
    os.popen("killall java 2>&1")
    logging.info("Restart privacy network")
    debug_target = []
    debug_port = args.tesserDebugPortStart
    if args.debug:
        if args.debug == '*':
            debug_target = [o for o in range(1, len(staticNodes) + 1)]
        else:
            debug_target = [int(o) for o in args.debug.replace(' ', '').split(",") if o != '']

        logging.info("Debugging the following geth, tessera instances {}".format(debug_target))

    private = True if args.private else True if len(
        os.listdir(os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera'))) > 0 else False
    if private:
        logging.info("Run Tessera network")
        for node in range(1, args.size + 1):
            if debug_target:
                debug_port = debug_port + 1
            time.sleep(1)
            # clean transaction manager IPC
            tm = os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'node-{}-tx'.format(node),
                              'tm.ipc')
            if os.path.exists(tm):
                os.remove(tm)
            nodetx = os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'node-{}-tx'.format(node))
            exec = ''
            if node in debug_target:
                exec = "java {} -jar {} -configfile {} >> {}/tessera.log 2>&1 &".format(
                    '-Xdebug -Xrunjdwp:transport=dt_socket,address=localhost:{},server=y,suspend=n'.format(debug_port),
                    TESSERA,
                    os.path.join(nodetx, 'tessera-config.json'),
                    nodetx
                )
            else:
                exec = "java -jar {} -configfile {} >> {}/tessera.log 2>&1 &".format(
                    TESSERA,
                    os.path.join(nodetx, 'tessera-config.json'),
                    nodetx
                )
            os.popen(exec)

        tesseraNetworkNotReady = True
        while (tesseraNetworkNotReady):
            time.sleep(1)
            count = 0
            for node in range(1, args.size + 1):
                if os.path.exists(
                        os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'node-{}-tx'.format(node),
                                     'tm.ipc')):
                    count = count + 1
            if count >= args.size:
                tesseraNetworkNotReady = False
        logging.info("Tessera infrastructure was successfully bootstrapped")

if args.buildRaft:
    logging.info("Building Raft Consensus Network")
    # Read static node information
    staticNodes = []
    endode = 'enode://{}@127.0.0.1:{}?discport=0&raftport={}'
    raftPort = args.raftStartPort
    rpcPort = args.rpcStartPort
    gethStartPort = args.gethStartPort

    time.sleep(1)
    staticNodesSize = 0
    with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'static-nodes.json'), 'r') as reader:
        staticNodesSize = len(json.load(reader))

    for node in range(1, staticNodesSize + 1):
        raftPort = raftPort + 1
        rpcPort = rpcPort + 1
        gethStartPort = gethStartPort + 1
        with open(os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node), 'enode'), 'r') as enodeReader:
            enode = enodeReader.read().replace('\n', '')
            staticNodes.append(endode.format(enode, gethStartPort, raftPort))

    raft_peers = range(1, len(staticNodes) + 1)
    raftPort = args.raftStartPort
    rpcPort = args.rpcStartPort
    time.sleep(1)
    for current_peer in raft_peers:
        time.sleep(1)
        with open(os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(current_peer), 'enode'),
                  'r') as enodeReader:
            current_enode = enodeReader.read().replace('\n', '')
            for peer in staticNodes:
                if current_enode not in peer:
                    os.popen(GETH_ADD_RAFT.format(GETH, os.path.join(os.path.abspath(args.workspace),
                                                                     'node-{}'.format(current_peer)), peer)).read()
        current_peer = current_peer + 1
    logging.info("Raft infrastructure was successfully bootstrapped")

if args.run:
    logging.info("Run Quorum Infrastructure")
    os.popen("killall -9 geth 2>&1")
    os.popen("killall -9 geth-debug 2>&1")
    os.popen("killall java 2>&1")
    os.popen("killall gdlv 2>&1")

    debug_target = []
    debug_port = args.tesserDebugPortStart
    if args.debug:
        if args.debug == '*':
            debug_target = [o for o in range(1, len(staticNodes) + 1)]
        else:
            debug_target = [int(o) for o in args.debug.replace(' ', '').split(",") if o != '']

        logging.info("Debugging the following geth, tessera instances {}".format(debug_target))

    private = True if args.private else True if len(
        os.listdir(os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera'))) > 0 else False
    if private:
        logging.info("Run Tessera network")
        for node in range(1, args.size + 1):
            if debug_target:
                debug_port = debug_port + 1
            time.sleep(1)
            # clean transaction manager IPC
            tm = os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'node-{}-tx'.format(node),
                              'tm.ipc')
            if os.path.exists(tm):
                os.remove(tm)
            nodetx = os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'node-{}-tx'.format(node))
            exec = ''
            if node in debug_target:
                exec = "java {} -jar {} -configfile {} >> {}/tessera.log 2>&1 &".format(
                    '-Xdebug -Xrunjdwp:transport=dt_socket,address=localhost:{},server=y,suspend=n'.format(debug_port),
                    TESSERA,
                    os.path.join(nodetx, 'tessera-config.json'),
                    nodetx
                )
            else:
                exec = "java -jar {} -configfile {} >> {}/tessera.log 2>&1 &".format(
                    TESSERA,
                    os.path.join(nodetx, 'tessera-config.json'),
                    nodetx
                )
            os.popen(exec)

        tesseraNetworkNotReady = True
        while (tesseraNetworkNotReady):
            time.sleep(1)
            count = 0
            for node in range(1, args.size + 1):
                if os.path.exists(
                        os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'node-{}-tx'.format(node),
                                     'tm.ipc')):
                    count = count + 1
            if count >= args.size:
                tesseraNetworkNotReady = False
        logging.info("Tessera infrastructure was successfully bootstrapped")

    # Read static node information
    staticNodes = []
    endode = 'enode://{}@127.0.0.1:{}?discport=0&raftport={}'
    raftPort = args.raftStartPort
    rpcPort = args.rpcStartPort
    gethStartPort = args.gethStartPort

    time.sleep(1)
    staticNodesSize = 0
    with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'static-nodes.json'), 'r') as reader:
        staticNodesSize = len(json.load(reader))

    for node in range(1, staticNodesSize + 1):
        raftPort = raftPort + 1
        rpcPort = rpcPort + 1
        gethStartPort = gethStartPort + 1
        with open(os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node), 'enode'), 'r') as enodeReader:
            enode = enodeReader.read().replace('\n', '')
            staticNodes.append(endode.format(enode, gethStartPort, raftPort))

    logging.info("Building geth infrastructure")
    raftPort = args.raftStartPort
    rpcPort = args.rpcStartPort
    gethStartPort = args.gethStartPort
    istanbulPort = args.istanbulStartPort

    for node in range(1, len(staticNodes) + 1):
        raftPort = raftPort + 1
        rpcPort = rpcPort + 1
        gethStartPort = gethStartPort + 1
        istanbulPort = istanbulPort + 1

        isRaft = not os.path.exists(os.path.join(os.path.abspath(args.workspace), 'net-info', 'istanbul'))
        exec = ''
        consensus_param = '--raft --raftport {}'.format(
            raftPort) if isRaft else '--istanbul.blockperiod {} --syncmode full --mine --minerthreads 1'.format(
            args.size)
        if args.gethParams:
            exec = "{} --datadir {} ".format(GETH, os.path.join(os.path.abspath(args.workspace),
                                                                'node-{}'.format(node))) + args.gethparams
        else:
            nodetx = os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'node-{}-tx'.format(node))
            private = os.path.exists(nodetx)
            if private:
                geth_params = GETH_PARAMS.format(
                    GETH if node not in debug_target else GETH_DEBUG,
                    "--permissioned" if os.path.exists(
                        os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node),
                                     'permissioned-nodes.json')) else '',

                    os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node)),
                    consensus_param,
                    rpcPort,
                    'raft' if isRaft else 'istanbul',
                    gethStartPort if isRaft else istanbulPort,
                    os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node))
                )
                exec = "PRIVATE_CONFIG={}/tm.ipc nohup ".format(
                    nodetx) + geth_params if node not in debug_target else '{} exec {}'.format(GO_DEBUGGER, geth_params)
            else:
                geth_params = GETH_PARAMS.format(
                    GETH if node not in debug_target else GETH_DEBUG,
                    "--permissioned" if os.path.exists(
                        os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node),
                                     'permissioned-nodes.json')) else '',
                    os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node)),
                    consensus_param,
                    rpcPort,
                    'raft' if isRaft else 'istanbul',
                    gethStartPort if isRaft else istanbulPort,
                    os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node))
                )
                if node in debug_target:
                    exec = '{} exec {} '.format(GO_DEBUGGER, geth_params)
                else:
                    exec = geth_params

        if str(node) in args.skipGeth:
            print()
            print('skipGeth: {}'.format(exec))
            print()
        else:
            os.popen(exec).read()
            logging.info("Geth infrastructure was successfully bootstrapped")

            if args.debug and node in debug_target:
                logging.info("Debug was enabled waiting. Type next to continue")
                if private:
                    logging.info("Attach to the following endpoints for tessera debug sessions:")
                    debug_port = args.tesserDebugPortStart
                    for o in debug_target:
                        debug_port = debug_port + 1
                        logging.info("for node-tx-{} -> http://127.0.0.1:{}".format(o, debug_port))

                exit_waiting = False
                while (not exit_waiting and node in debug_target):
                    user_signal = input("> ")
                    if user_signal == 'next':
                        exit_waiting = True
                    if user_signal == 'stop':
                        logging.info("Stoping Network")
                        os.popen("killall -9 geth 2>&1")
                        os.popen("killall java 2>&1")
                        os.popen("killall tshark 2>&1")
                        os.popen("killall gdlv 2>&1")
                        os.popen("killall -9 geth-debug 2>&1")
                        logging.info("Network processes has been terminated")
                        exit(0)

    isRaft = not os.path.join(os.path.abspath(args.workspace), 'net-info', 'istanbul')
    if isRaft:
        logging.info("Building Raft Consensus Network")
        raft_peers = range(1, len(staticNodes) + 1)
        raftPort = args.raftStartPort
        rpcPort = args.rpcStartPort
        time.sleep(1)
        for current_peer in raft_peers:
            if str(current_peer) not in args.skipGeth:
                time.sleep(1)
                with open(os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(current_peer), 'enode'),
                          'r') as enodeReader:
                    current_enode = enodeReader.read().replace('\n', '')
                    for peer in staticNodes:
                        if current_enode not in peer:
                            os.popen(GETH_ADD_RAFT.format(GETH, os.path.join(os.path.abspath(args.workspace),
                                                                             'node-{}'.format(current_peer)),
                                                          peer)).read()
                current_peer = current_peer + 1
        logging.info("Raft infrastructure was successfully bootstrapped")

    # Read Accounts
    logging.info("Unlock Random Account in each node for operations")
    with open(os.path.join(args.workspace, 'net-info', 'accounts.json'), 'r') as accountsReader:
        accounts = json.load(accountsReader)

    for node in range(1, len(staticNodes) + 1):
        if str(node) not in args.skipGeth:
            account_index = random.randint(0, args.accounts - 1)
            os.popen(GETH_UNLOCK_ACCOUNT.format(
                GETH,
                os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node)),
                accounts[account_index]['account'],
                accounts[account_index]['pass']
            ))
            logging.info("Node:{} Account:{} unlocked".format(node, accounts[account_index]['account']))

    logging.info("Quorum infrastructure was successfully started")

if args.container:
    logging.warning("This feature is not supported Yet")

if args.info:
    print("+ Infrastructure:")
    print("{}".format(os.path.abspath(args.workspace)))

    network = os.path.join(os.path.abspath(args.workspace), 'net-info')
    tessera = os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera')
    # Accounts
    print("+ Accounts:")
    with open(os.path.join(args.workspace, 'net-info', 'accounts.json'), 'r') as accountsReader:
        accounts = json.load(accountsReader)
        for o in accounts:
            print("{}:{}".format(o['account'], o['pass']))

    # Quorum
    print("+ Quorum endpoints:")
    with open(os.path.join(args.workspace, 'net-info', 'static-nodes.json'), 'r') as accountsReader:
        staticNodes = json.load(accountsReader)
        for o in staticNodes:
            print('{}'.format(o))

    # Tressera
    private = True if args.private else True if len(
        os.listdir(os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera'))) > 0 else False

    if private:
        print("+ Transaction manager endpoint information:")
        with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'endpoints.json'),
                  'r') as tesseraEndpointReader:
            endpoints = json.load(tesseraEndpointReader)
            for o in endpoints:
                print(o)

        print("+ Transaction manager endpoints:")
        with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'node-1-tx',
                               'tessera-config.json'), 'r') as configReader:
            config = json.load(configReader)
            counter = 0
            for o in config['peer']:
                counter = counter + 1
                with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera',
                                       'node-{}-tx'.format(counter), 'node-tx-key.pub'), 'r') as keyReader:
                    print('{} - {}'.format(o['url'], keyReader.read()))

if args.contract:
    privateForPubKeyList = []
    privateForIndexList = []
    network = os.path.join(os.path.abspath(args.workspace), 'net-info')
    tessera = os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera')

    logging.info("Deploy contract:{}".format(args.contract))
    if not args.account:
        logging.info("Deploy using random account")
        with open(os.path.join(args.workspace, 'net-info', 'accounts.json'), 'r') as accountsReader:
            accounts = json.load(accountsReader)
            args.account = accounts[random.randint(0, len(accounts) - 1)]

    if not args.sender:
        logging.info("Deploy using random node")
        with open(os.path.join(args.workspace, 'net-info', 'static-nodes.json'), 'r') as staticReader:
            staticNodes = json.load(staticReader)
            args.sender = random.randint(0, len(staticNodes) - 1) + 1

    if args.privateFor:
        with open(os.path.join(args.workspace, 'net-info', 'static-nodes.json'), 'r') as staticReader:
            staticNodes = json.load(staticReader)
            args.privateFor = args.privateFor.strip(' ')
            if args.privateFor == '*':
                privateForIndexList = [o for o in range(1, len(staticNodes) + 1)]
            elif ',' in args.privateFor:
                privateForIndexList = [o for o in args.privateFor.split(',') if o != '']
            else:
                privateForIndexList.append(args.privateFor)

            for tx in privateForIndexList:
                with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'node-{}-tx'.format(tx),
                                       'node-tx-key.pub'), 'r') as keyReader:
                    privateForPubKeyList.append(keyReader.read())

    logging.info("Compiling contract")
    os.popen("solcjs --bin --abi {} --output-dir {}".format(
        args.contract,
        os.path.join(os.path.abspath(args.workspace), 'net-info', 'helpers',
                     ))).read()

    # Read compilation result
    contractByteCode = ''
    contractABI = ''
    contractABIPath = ''
    contractByteCodePath = ''
    contractFileName = os.path.abspath(args.contract).split('/')[-1].split('.')[0]
    for o in os.listdir(os.path.join(os.path.abspath(args.workspace), 'net-info', 'helpers')):
        if contractFileName in o and o.endswith('.bin'):
            contractByteCodePath = os.path.join(os.path.abspath(args.workspace), 'net-info', 'helpers', o)
        if contractFileName in o and o.endswith('.abi'):
            contractABIPath = os.path.join(os.path.abspath(args.workspace), 'net-info', 'helpers', o)
    # Read values
    with open(contractByteCodePath, 'r') as bytecodeReader:
        contractByteCode = bytecodeReader.read()

    with open(contractABIPath, 'r') as abiReader:
        contractABI = abiReader.read()

    # clean files
    os.remove(contractABIPath)
    os.remove(contractByteCodePath)

    # Generate template
    contractTemplate = ''

    if privateForPubKeyList:
        logging.info("Deploy contract as private contract from node:node-{} to nodes:{} using account:{}".format(
            args.sender,
            privateForIndexList,
            args.account['account']
        ))

        with open(os.path.join(RES, 'helpers', 'private-contract-build.js'), 'r') as reader:
            contractTemplate = reader.read()

        contractTemplate = contractTemplate.replace('*abi*', contractABI)
        contractTemplate = contractTemplate.replace('*abi*', contractABI)
        contractTemplate = contractTemplate.replace('*bytecode*', contractByteCode)
        contractTemplate = contractTemplate.replace('*account*', args.account['account'])
        contractTemplate = contractTemplate.replace('*password*', args.account['pass'])
        contractTemplate = contractTemplate.replace('*privateFor*', json.dumps(privateForPubKeyList))

    else:
        logging.info("Deploy contract as public contract from node:node-{} using account:{}".format(
            args.sender,
            args.account['account']
        ))

        with open(os.path.join(RES, 'helpers', 'public-contract-build.js'), 'r') as reader:
            contractTemplate = reader.read()

        contractTemplate = contractTemplate.replace('*abi*', contractABI)
        contractTemplate = contractTemplate.replace('*bytecode*', contractByteCode)
        contractTemplate = contractTemplate.replace('*account*', args.account['account'])
        contractTemplate = contractTemplate.replace('*password*', args.account['pass'])

    contractDeployFile = contractABIPath.replace('.abi', '.js')
    with open(contractDeployFile, 'w') as writer:
        writer.write(contractTemplate)

    os.popen(GETH_EXECUTE_RPC.format(
        GETH,
        os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(args.sender)),
        "loadScript('{}')".format(contractDeployFile)
    )).read()

if args.getContracts:
    if not args.sender:
        with open(os.path.join(args.workspace, 'net-info', 'static-nodes.json'), 'r') as staticReader:
            staticNodes = json.load(staticReader)
            args.sender = random.randint(0, len(staticNodes) - 1) + 1

    accounts = []
    with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'accounts.json'), 'r') as reader:
        accounts = json.load(reader)

    for account in accounts:
        result = os.popen(GETH_EXECUTE_RPC.format(
            GETH,
            os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(args.sender)),
            "loadScript('{}');getContract('{}');".format(
                os.path.join(RES, 'helpers', 'helpers.js'),
                account['account']
            )
        )).read().replace('""', '')

        if result and result.replace("\n", "") != '':
            print(result)

if args.contractsOf:
    if not args.sender:
        with open(os.path.join(args.workspace, 'net-info', 'static-nodes.json'), 'r') as staticReader:
            staticNodes = json.load(staticReader)
            args.sender = random.randint(0, len(staticNodes) - 1) + 1

    print(os.popen(GETH_EXECUTE_RPC.format(
        GETH,
        os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(args.sender)),
        "loadScript('{}');getCreatingContractTransactionsByAccount('{}',null,null);".format(
            os.path.join(RES, 'helpers', 'helpers.js'),
            args.contractsOf
        )
    )).read())

if args.transactionsOf:
    if not args.sender:
        with open(os.path.join(args.workspace, 'net-info', 'static-nodes.json'), 'r') as staticReader:
            staticNodes = json.load(staticReader)
            args.sender = random.randint(0, len(staticNodes) - 1) + 1

    print(os.popen(GETH_EXECUTE_RPC.format(
        GETH,
        os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(args.sender)),
        "loadScript('{}');getTransactionsByAccount('{}',null,null);".format(
            os.path.join(RES, 'helpers', 'helpers.js'),
            args.transactionsOf
        )
    )).read())

if args.reset and not args.build:
    logging.info("Reset network chain")
    for node in range(1, args.size + 1):
        logging.info("Reset node-{}".format(node))
        geth = os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node), 'geth')
        shutil.rmtree(geth)

        os.popen("{} --datadir {} init {}/genesis.json".format(
            GETH,
            os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node)),
            os.path.join(os.path.abspath(args.workspace), 'net-info'))
        ).read()

if args.sniff and not args.sniffName:
    args.sniffName = datetime.now().strftime("%d-%m-%Y-%H:%M:%S")

if args.sniffStop:
    logging.info("Stoping Sniffers")
    os.popen("killall -9 tshark 2>&1")
    logging.info("Sniffers has been terminated")

if args.sniff:
    session_folder = os.path.join(os.path.abspath(args.workspace), 'net-info', 'traffic', args.sniffName)
    tessera_folder = os.path.join(session_folder, "tessera")
    get_folder = os.path.join(session_folder, "geth")

    os.mkdir(session_folder)
    os.mkdir(tessera_folder)
    os.mkdir(get_folder)

    tessera_ports = []
    geth_ports = {}
    private = True if args.private else True if len(
        os.listdir(os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera'))) > 0 else False
    with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'node-1-tx', 'tessera-config.json'),
              'r') as reader:
        tessera_config = json.load(reader)
        tessera_ports = [o['url'].split(':')[-1] for o in tessera_config['peer']]

    with open(os.path.join(args.workspace, 'net-info', 'static-nodes.json'), 'r') as accountsReader:
        staticNodes = json.load(accountsReader)
        node_counter = 0
        for node in staticNodes:
            node_counter = node_counter + 1
            node_geth_port = 0
            node_raft_port = 0
            node_rpc_port = 0

            node_geth_port = node.split('@')[1].split('?')[0].split(':')[1]
            params = node.split('@')[1].split('?')[1].split('&')
            for p in params:
                if 'raftport' in p:
                    node_raft_port = p.split('=')[1]
                if 'rpcport' in p:
                    node_rpc_port = p.split('=')[1]
            geth_ports[node_counter] = {'geth': node_geth_port, 'raft': node_raft_port, 'rpc': node_rpc_port}

    sniff_exec_tessera = []
    for port in tessera_ports:
        sniff_exec_tessera.append('tcp dst port {}'.format(port))

    sniff_exec_tessera = ' or '.join(sniff_exec_tessera)
    os.popen(SNIFF.format(
        sniff_exec_tessera,
        os.path.join(tessera_folder, 'tessera.pcap')
    ))
    for geth in geth_ports.keys():
        os.mkdir(os.path.join(get_folder, 'node-{}'.format(geth)))
        # Geth
        sniff_exec_geth = ' or '.join([
            'tcp dst port {}'.format(geth_ports[geth]['geth']),
            'tcp dst port {}'.format(geth_ports[geth]['raft']),
            'tcp dst port {}'.format(geth_ports[geth]['rpc'])])
        exec = SNIFF.format(
            sniff_exec_geth,
            os.path.join(os.path.join(get_folder, 'node-{}'.format(geth)), 'geth.pcap'))
        os.popen(exec)

    logging.info("Sniffer output:")
    logging.info("Tessera:{}".format(os.path.join(tessera_folder, 'tessera.pcap')))
    for geth in geth_ports.keys():
        logging.info("geth:{}".format(os.path.join(os.path.join(get_folder, 'node-{}'.format(geth)), 'geth.pcap')))

if args.build and args.istanbul:
    # 1 - Generate workspace structure
    logging.info('Generating Workspace')
    # Clean workspace if exists
    if os.path.exists(args.workspace):
        shutil.rmtree(args.workspace)

    # Generate workspace folders tree
    os.mkdir(args.workspace)
    os.mkdir(os.path.join(args.workspace, 'net-info'))
    os.mkdir(os.path.join(args.workspace, 'net-info', 'tessera'))
    os.mkdir(os.path.join(args.workspace, 'net-info', 'istanbul'))
    os.mkdir(os.path.join(args.workspace, 'net-info', 'traffic'))
    os.mkdir(os.path.join(args.workspace, 'net-info', 'helpers'))
    os.mkdir(os.path.join(args.workspace, 'net-info', 'accounts'))
    [os.mkdir(os.path.join(args.workspace, 'node-{}'.format(o))) for o in range(1, args.size + 1)]

    # 2 - Generate accounts
    logging.info('Generating Accounts')
    # Generate passwords
    for account in range(1, args.accounts + 1):
        with open(os.path.join(args.workspace, 'net-info', 'accounts', 'account-{}.pass'.format(account)),
                  'w') as passFile:
            passFile.write(''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)]))

    # Generate Accounts
    accounts = []
    for account in range(1, args.accounts + 1):
        accountAddress = str(os.popen("{} --datadir {} account new --password {}".format(GETH,
                                                                                         os.path.join(os.path.abspath(
                                                                                             args.workspace),
                                                                                             'net-info'),
                                                                                         os.path.join(os.path.abspath(
                                                                                             args.workspace),
                                                                                             'net-info',
                                                                                             'accounts',
                                                                                             'account-{}.pass'.format(
                                                                                                 account)))
                                      ).read()).replace("Address: {", "").replace("}", "").replace("\n", "")

        accountAddress = accountAddress.replace("Your new key was generatedPublic address of the key:   ", "").replace(
            "Path of the secret key file", "")
        if ":" in accountAddress:
            accountAddress = accountAddress.split(":")[0]

        if not accountAddress.startswith("0x"):
            accountAddress = "0x{}".format(accountAddress)

        with open(os.path.join(args.workspace, 'net-info', 'accounts', 'account-{}.pass'.format(account)),
                  'r') as passFile:
            accountPassword = passFile.read()
            accounts.append({'account': accountAddress, 'pass': accountPassword})

    with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'accounts.json'), 'w') as accountsFile:
        accountsFile.write(json.dumps(accounts))
        shutil.rmtree(os.path.join(os.path.abspath(args.workspace), 'net-info', 'accounts'))
        os.mkdir(os.path.join(os.path.abspath(args.workspace), 'net-info', 'accounts'))
        for account in accounts:
            with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'accounts',
                                   '{}.pass'.format(account['account'].replace('0x', ''))), 'w') as passWrite:
                passWrite.write(account['pass'])
    # Copy keystore
    for node in range(1, args.size + 1):
        shutil.copytree(os.path.join(os.path.abspath(args.workspace), 'net-info', 'keystore'),
                        os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node), 'keystore'))

    # Generate keys, genesis & static-nodes
    logging.info("Generate genesis.json & static-nodes.json")
    pwd = os.path.join(os.path.abspath(args.workspace), 'net-info', 'istanbul')
    exec_args = ISTANBUL_SETUP_NETWORK.format(args.size)
    subprocess.Popen([ISTANBUL] + exec_args.split(' '), cwd=pwd)

    # Genesis file
    # Populate with generated accounts
    time.sleep(1)
    genesis = {}
    with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'istanbul', 'genesis.json')) as genesisFile:
        genesis = json.load(genesisFile)
        genesis['alloc'] = {}
        for o in accounts:
            genesis['alloc'][o['account'].replace('0x', '')] = {"balance": '{}'.format(args.ether)}

    with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'genesis.json'), 'w') as genWriter:
        json.dump(genesis, genWriter)

    # Process genesis file
    logging.info("Setup genesis file")
    for node in range(1, args.size + 1):
        os.popen("{} --datadir {} init {}/genesis.json".format(
            GETH,
            os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node)),
            os.path.join(os.path.abspath(args.workspace), 'net-info'))
        ).read()

    logging.info("Setup Nodes Key")
    for node in range(1, args.size + 1):
        shutil.move(
            os.path.join(os.path.abspath(args.workspace), 'net-info', 'istanbul', '{}'.format(node - 1), 'nodekey'),
            os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node), 'nodekey')
        )
        shutil.rmtree(os.path.join(os.path.abspath(args.workspace), 'net-info', 'istanbul', '{}'.format(node - 1)))

    logging.info("Setup Static Nodes")
    istanbulStatic = []
    with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'istanbul', 'static-nodes.json'),
              'r') as reader:
        istanbulStatic = json.load(reader)

    # Fix static node port
    istanbulPort = args.istanbulStartPort
    for entry in range(0, len(istanbulStatic)):
        istanbulPort = istanbulPort + 1
        istanbulStatic[entry] = istanbulStatic[entry].replace('0.0.0.0:30303', '127.0.0.1:{}'.format(istanbulPort))

    with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'istanbul', 'static-nodes.json'),
              'w') as writer:
        json.dump(istanbulStatic, writer)

    shutil.copy(os.path.join(os.path.abspath(args.workspace), 'net-info', 'istanbul', 'static-nodes.json'),
                os.path.join(os.path.abspath(args.workspace), 'net-info', 'static-nodes.json'))

    for node in range(1, len(istanbulStatic) + 1):
        nodepath = os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node))
        with open(os.path.join(nodepath, 'enode'), 'w') as writer:
            writer.write(istanbulStatic[node - 1].split('@')[0].replace('enode://', ''))
        shutil.copy(os.path.join(os.path.abspath(args.workspace), 'net-info', 'istanbul', 'static-nodes.json'),
                    os.path.join(nodepath, 'static-nodes.json'))

    if args.permissioned:
        logging.info("Generate permissioned-nodes.json")
        with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'permissioned-nodes.json'),
                  'w') as permissionWriter:

            permissioned = [entry.split("?")[0] for entry in istanbulStatic]
            permissionWriter.write(json.dumps(permissioned))

        for node in range(1, args.size + 1):
            logging.info("Generate permissioned entries for node-{}".format(node))
            shutil.copy(os.path.join(os.path.abspath(args.workspace), 'net-info', 'permissioned-nodes.json'),
                        os.path.join(os.path.abspath(args.workspace), 'node-{}'.format(node),
                                     'permissioned-nodes.json'))

if args.private and args.build:
    if args.private:
        logging.info("Generate Tessera Keys")
        for node in range(1, args.size + 1):
            nodetx = os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'node-{}-tx'.format(node))
            os.mkdir(nodetx)

            with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'node-{}-tx'.format(node),
                                   'node-tx-keys.pass'), 'w') as passFile:
                password = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])
                passFile.write(password)
                logging.info(os.popen(
                    "java -jar {} -keygen -filename {} << '{}'".format(
                        TESSERA,
                        os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'node-{}-tx'.format(node),
                                     'node-tx-key'),
                        password
                    )).read())

        logging.info("Generate Tessera Config")
        tesseraConfigTemplate = {}
        with open(os.path.join(RES, 'other', 'tessera.json')) as genesisFile:
            tesseraConfigTemplate = json.load(genesisFile)

        TesserConfigPeers = []
        txPpStartPort = args.txPpStartPort
        for node in range(1, args.size + 1):
            txPpStartPort = txPpStartPort + 1
            TesserConfigPeers.append({"url": "http://localhost:{}".format(txPpStartPort)})

        txPpStartPort = args.txPpStartPort
        txQtStartPort = args.txQtStartPort
        txTpStartPort = args.txTpStartPort

        tessera_endpoints = []
        for node in range(1, args.size + 1):
            txPpStartPort = txPpStartPort + 1
            txQtStartPort = txQtStartPort + 1
            txTpStartPort = txTpStartPort + 1

            tessera_endpoints.append("http://localhost:{}/application.wadl".format(txTpStartPort))
            nodetx = os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'node-{}-tx'.format(node))
            nodetxServerConfig = [
                {
                    "app": "ThirdParty",
                    "enabled": True,
                    "serverAddress": "http://localhost:{}".format(txTpStartPort),
                    "communicationType": "REST"
                },
                {
                    "app": "Q2T",
                    "enabled": True,
                    "serverAddress": "unix:{}/tm.ipc".format(nodetx),
                    "communicationType": "REST"
                },
                {
                    "app": "P2P",
                    "enabled": True,
                    "serverAddress": "http://localhost:{}".format(txPpStartPort),
                    "sslConfig": {
                        "tls": "OFF"
                    },
                    "communicationType": "REST"
                }
            ]
            nodetxKeysConfig = [{
                "privateKeyPath": "{}/node-tx-key.key".format(nodetx),
                "publicKeyPath": "{}/node-tx-key.pub".format(nodetx)
            }]

            tesseraConfigTemplate["jdbc"][
                "url"] = "jdbc:h2:/{}/tessera-store-{};MODE=Oracle;TRACE_LEVEL_SYSTEM_OUT=0".format(nodetx, node)
            tesseraConfigTemplate["serverConfigs"] = nodetxServerConfig
            tesseraConfigTemplate["peer"] = TesserConfigPeers
            tesseraConfigTemplate["keys"]["keyData"] = nodetxKeysConfig

            with open(os.path.join(nodetx, 'tessera-config.json'.format(node)), 'w') as tesseraConfigWriter:
                json.dump(tesseraConfigTemplate, tesseraConfigWriter)

        with open(os.path.join(os.path.abspath(args.workspace), 'net-info', 'tessera', 'endpoints.json'),
                  'w') as tesseraEndpointWriter:
            json.dump(tessera_endpoints, tesseraEndpointWriter)
