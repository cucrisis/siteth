function getTransactionsByAccount(account, startBlockNumber, endBlockNumber) {
  if (startBlockNumber == null) {
    startBlockNumber = 0;
  }

  if (endBlockNumber == null) {
    endBlockNumber = eth.blockNumber;
  }

  console.log("+ Find transaction of: " + account);
  console.log("+ Scanning from Block: " + startBlockNumber + " to " +endBlockNumber);
  console.log("+ Transactions");

transactions = 0;
for (var i = startBlockNumber; i <= endBlockNumber; i++) {
    var block = eth.getBlock(i, true);
    if (block != null && block.transactions != null) {
      block.transactions.forEach( function(e) {
        if (account == "*" || account == e.from || account == e.to) {
          transactions++
          console.log()
          console.log(
              "Tx hash: " + e.hash + "\n"
            + "Tx Information" + "\n"
            + "\tnonce           : " + e.nonce + "\n"
            + "\tblockHash       : " + e.blockHash + "\n"
            + "\tblockNumber     : " + e.blockNumber + "\n"
            + "\ttransactionIndex: " + e.transactionIndex + "\n"
            + "\tfrom            : " + e.from + "\n"
            + "\tto              : " + e.to + "\n"
            + "\tvalue           : " + e.value + "\n"
            + "\ttime            : " + block.timestamp + " " + new Date(block.timestamp * 1000).toGMTString() + "\n"
            + "\tgasPrice        : " + e.gasPrice + "\n"
            + "\tgas             : " + e.gas + "\n"
            + "\tinput           : " + e.input);
        }
      })
    }
  }
  console.log()
  return 'Total Transactions:' + transactions
}

function getContract(account) {
  startBlockNumber = 0;
  endBlockNumber = eth.blockNumber;


wasPrinted = false;
for (var i = startBlockNumber; i <= endBlockNumber; i++) {
    var block = eth.getBlock(i, true);
    if (block != null && block.transactions != null) {
      block.transactions.forEach( function(e) {
        if (account == "*" || account == e.from || account == e.to) {
          if (e.to == null){
            if (wasPrinted == false) {
                console.log("+ Account : " + account);
                wasPrinted = true;
            }

            var receipt =web3.eth.getTransactionReceipt(e.hash)
            console.log("Contract:" +receipt.contractAddress);
            console.log(
                "Transaction information:" + "\n"
                + "Hash:" + e.hash + "\n"
                + "Time:" + block.timestamp + " " + new Date(block.timestamp * 1000).toGMTString() + "\n"
                + "Input:" + e.input);

            }

            console.log('Bytes:'+eth.getCode(receipt.contractAddress))
        }
      })
    }
  }

  return ''
}

function getCreatingContractTransactionsByAccount(account, startBlockNumber, endBlockNumber) {
  if (startBlockNumber == null) {
    startBlockNumber = 0;
  }

  if (endBlockNumber == null) {
    endBlockNumber = eth.blockNumber;
  }

  console.log("+ Get All Contracts Creation Transaction Of : " + account);
  console.log("+ Scanning from Block: " + startBlockNumber + " to " +endBlockNumber);
  console.log("+ Transactions");

transactions = 0;
for (var i = startBlockNumber; i <= endBlockNumber; i++) {
    var block = eth.getBlock(i, true);
    if (block != null && block.transactions != null) {
      block.transactions.forEach( function(e) {
        if (account == "*" || account == e.from || account == e.to) {
          if (e.to == null){
              transactions++
            console.log()

            var receipt =web3.eth.getTransactionReceipt(e.hash)
            console.log("Contract:" +receipt.contractAddress);
            console.log(
                "Transaction information:" + "\n"
                + "Hash:" + e.hash + "\n"
                + "Time:" + block.timestamp + " " + new Date(block.timestamp * 1000).toGMTString() + "\n"
                + "Input:" + e.input);

            }

            console.log('Bytes:'+eth.getCode(receipt.contractAddress))
        }
      })
    }
  }
  console.log()
  return 'Total Transactions:' + transactions
}
