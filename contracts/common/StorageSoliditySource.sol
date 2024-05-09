pragma solidity >=0.4.0;

/**
 * @title Storage
 * @dev Store & retrieve value in a variable
 */
contract Storage {
    uint256 number;
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
}

contract StorageMultipleVars {
    string public data = "test";
    uint256 public constant number = 1;
    uint256 public notSet;

    function setData(string memory _data) public {
        data = _data;
    }
}
