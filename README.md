# Siteth

![Alt Text](ref/build.gif)

An tool to bootstrap and debug Quorum network. The main goal is to introduce fast/portable way of spinning and interrogating a network of *N* size node
and **X** accounts locally for debugging and security research. 

**Siteth**: generate a clean folder structure that represent the network information. User can zip / send this folder to anther siteth user and be able to 
run the network with minimum to no change.

**Siteth**: works as wrapper around other tools such as tshark for package sniffing, gdlv for golang binary debugging, and quorum ecosystem (geth, tessera, istanbul-tools).

**Siteth**: provide easy way to interface with RPC console through helpers script located in res/helpers.js from command line.

**Siteth**: is not intended  to be used for production network deployment.

**Siteth**: is very fast writen script a lot of refactoring needed.

**Siteth**: res folder only support OSX for now.

### Automation
**res/helpers/helpers.js**: javascript to interact with RPC

**res/helpers/instrument.star**: [automate golang debugger](https://github.com/aarzilli/gdlv/blob/master/doc/starlark.md) useful to instrument geth binary at run time. 

**res/helpers/private|public -contract-build.js**: contract deployment template.

### Usage
```
siteth.py --build --private --permissioned
siteth.py --info
siteth.py --run
```

### Examples

```
Build network:
 siteth.py --build --raft --workspace network --permissioned --private --info --size 8
 siteth.py --build --istanbul --workspace network --permissioned --private --info --size 8
```

```
Print information about network:
 siteth.py --info --workspace network

Run previously created network:
 siteth.py --run --workspace network

Reset network chain information:
 siteth.py --reset --workspace network

Stop running network:
 siteth.py --stop
 
Restart Tessera Network
 ./siteth.py --restartPrivacy --workspace <...>
```

```
Sniff network traffic & save to pcap:
 siteth.py --run --sniff '*'  --workspace network
```

```
Debug tessera & geth 
 siteth.py --run --debug '*' --workspace network

Print geth parameters for debugging instead of running it
 ./siteth.py --run --skipGeth 1 --workspace <...>

```

```
Deploy public contract using random account from random node
 siteth.py --contract contract.sol

Deploy public contract using specific account from specific node
 siteth.py --contract contract.sol --sender 1 --account 0x000000

Deploy private contract using random account form random node to specific nodes
 siteth.py --contract contract.sol --privateFor 1,2,3
```

```
Display all contracts information created by specific ethereum address
 siteth.py --contractsOf 0x000000000


Display all transactions created by specific ethereum address
 siteth.py --transactionsOf 0x000000000
```
 

### Workspace folder structure
```
├── net-info
│   ├── accounts    # Ethereum account information
│   ├── helpers     # Put your network specific files for example contracts, notes ...etc
│   ├── keystore    # Contains accounts key store. Note: all geth nodes will have same copy of keystore, so accounts any account can be unlocked in anynode.
│   ├── tessera     # Tessera network configuration. 
│   │   ├── node-(1:X)-tx
│   │    
│   └── traffic     # Output of traffic analysis.
├── node-(1:X)
│   ├── geth
│   │   ├── chaindata
│   │   ├── lightchaindata
│   │   └── nodes
│   ├── keystore
│   ├── quorum-raft-state
│   ├── raft-snap
│   └── raft-wal

```

### Parameters
```
  --stop                Stop Existing Network
  --raft                Bootstrap raft network
  --istanbul            Bootstrap istanbul network
  --run                 Run Existing Network
  --buildRaft           Build raft network
  --restartPrivacy      Restart Tessera Network
  --skipGeth SKIPGETH   skip running geth instead print formed command. Use
                        comma separation for multiple nodes(ex, 1,2,3,4) or
                        '*' for all nodes
  --debug DEBUG         Rung golang binary Debug for specified nodes. Use
                        comma separation for multiple nodes(ex, 1,2,3,4) or
                        '*' for all nodes
  --sniff               Sniff network traffic
  --sniffClear          Clearn sniffing data
  --sniffName SNIFFNAME Sniff session name. Time format if not set
  --sniffStop           Stop traffic sniffing
  --reset               Reset chain information
  --getContracts        Get Information about all the contracts in the network
  --container           Build Docker container based infrastructure. NOT IMPLEMENTED YET
  --containerServer CONTAINERSERVER Docker server location
  --contract CONTRACT   Path to contract to deploy. This is contract.sol file
  --account ACCOUNT     An existing ethereum account address to use to deploy
                        contract from. if not set a random one will be picked
  --password PASSWORD   An existing ethereum account password
  --sender SENDER       The node index to use as sender of the transaction. if
                        not set a random one will be picked
  --contractsOf CONTRACTSOF Show all contract creation transaction of account
  --transactionsOf TRANSACTIONSOF Show Accounts Transactions
  --privateFor PRIVATEFOR Nodes index to use (ex. 1,2,3,4). will set privateFor
                        to its the geth tx manager addresses for each node
  --info                Print information information
  --build               Build Network
  --private             Build With Privacy feature enabled
  --permissioned        Build With Permission feature nabled
  --size SIZE           Network size
  --accounts ACCOUNTS   Total number of Accounts
  --workspace WORKSPACE Network workspace folder
  --ether ETHER         Initial Account Funding Value
  --raftStartPort RAFTSTARTPORT Raft Start Port
  --gethStartPort GETHSTARTPORT Geth peering Start Port
  --rpcStartPort RPCSTARTPORT RPC Start Port
  --txTpStartPort TXTPSTARTPORT Tessera Third Party Start Port
  --tesserDebugPortStart TESSERDEBUGPORTSTART Tessera Debug port start
  --txQtStartPort TXQTSTARTPORT Tessera Quorum Transaction Start Port
  --txPpStartPort TXPPSTARTPORT Tessera Peer Network Start Port
  --istanbulStartPort ISTANBULSTARTPORT istanbul start port
  --gethParams GETHPARAMS Additional geth parameters


```

### Optional Env Variables
```
export GO_DEBUGGER=... path to gdlv debugger
export GETH_DEBUG =... path to debuggable compiled version of geth
export RES_PATH=... path to resource folder.
export TESSERA=... path to tessera binary if not provided RES_PATH/bin/tessera will be used
export GETH_PATH=... path to geth binary if not provided RES_PATH/bin/geth will be used
export BOOT_PATH=... path to bootnode binary if not provided RES_PATH/bin/bootnode will be used
export ISTANBUL_PATH=... path to istanbul binary if not provided RES_PATH/bin/istanbul will be used
```

### Requirements
 ```
Must be installed
- solcjs - npm install -g solc
- tshark - brew install wireshark

Included:
- geth
- gdlv
- tessera
- bootnode
```

### Future Features:
- [ ]  Refactor, restructure & clean 
- [ ]  Support docker build & remote docker deployment
- [ ]  Integrate tshark as module instead of external dependency with pyshark
- [ ]  Support correlation between helpers/helpers.js functions and command line parameters automatically
- [ ]  Support constraining accounts to nodes instead of deploying all accounts to all nodes
- [ ]  Support contracts security scanning on the fly during deployment
- [ ]  Support multi-platform for res/bin 
- [ ]  Check for ecosystem version compatibility
