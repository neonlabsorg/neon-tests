pragma solidity >=0.4.0;

/**
 * @title Storage
 * @dev Store & retrieve value in a variable
 */
contract Storage {
    uint256 number;
    uint256 numberTwo;
    uint256 time;
    uint256[] public values;

    /**
     * @dev Stores value in variable
     * @param num value to store
     */
    function store(uint256 num) public {
        number = num;
        values = [number];
    }

    /**
     * @dev Returns value
     * @return value of 'number'
     */
    function retrieve() public view returns (uint256) {
        return number;
    }

    function retrieveSenderBalance() public view returns (uint256) {
        return msg.sender.balance;
    }

    function storeSumOfNumbers(uint256 num1, uint256 num2) public returns (uint256) {
        number = num1;
        numberTwo = num2;
        return number + numberTwo;
    }
    /**
     * @dev Returns code for given address
     * @return value of '_addr.code'
     */
    function at(address _addr) public view returns (bytes memory) {
        return _addr.code;
    }

    function storeBlock() public {
        number = block.number;
        values = [number];
    }

    function storeBlockTimestamp() public returns (uint256) {
        number = block.timestamp;
        values = [number];
        return block.timestamp;
    }

    function storeBlockInfo() public {
        number = block.number;
        time = block.timestamp;
        values = [number, time];
    }
}

contract StorageMultipleVars {
    string public data = "test";
    uint256 public constant number = 1;
    uint256 public notSet;

    function setData(string memory _data) public {
        data = _data;
    }
}
