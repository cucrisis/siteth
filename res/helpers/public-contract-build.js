personal.unlockAccount('*account*','*password*');var abi = *abi*;var bytecode = '0x*bytecode*';var simpleContract = web3.eth.contract(abi);var simple = simpleContract.new(42, {from:'*account*', data: bytecode, gas: 0x47b760}, function(e, contract) {if (e) {console.log('Error creating contract', e);} else {if (!contract.address) {console.log('Contract transaction creation sent.');console.log('Transaction hash: ' + contract.transactionHash + ' waiting ...');} else {console.log('Contract was successfully created');console.log('Contract: ' + contract.address);}}});