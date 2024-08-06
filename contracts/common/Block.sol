// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;


contract BlockTimestamp {
    event Result(uint256 block_timestamp);
    uint256 a;
    uint256 block_timestamp;

    struct Data {
        string info;
        uint256 value;
    }
    mapping(uint256 => Data) public dataByTimestamp;
    event DataAdded(uint256 timestamp, string info, uint256 value);

    constructor() {
        block_timestamp = block.timestamp;
    }

    function getInitBlockTimestamp() public view returns (uint256) {
        return block_timestamp;
    }

    function getBlockTimestamp() public view returns (uint256) {
        return block.timestamp;
    }

    function callEvent() public {
        emit Result(block.timestamp);
    }

    function callEventsInLoop() public payable {
        for (uint256 i = 0; i < 100; i++) {
            a = a + i;
        }
        emit Result(block.timestamp);
    }

    function addData(string memory _info, uint256 _value) public {
        uint256 currentTimestamp = block.timestamp;
        Data memory newData = Data({
            info: _info,
            value: _value
        });
        
        dataByTimestamp[currentTimestamp] = newData;
        emit DataAdded(currentTimestamp, _info, _value);
    }
    
    function getData(uint256 _timestamp) public view returns (string memory, uint256) {
        Data memory retrievedData = dataByTimestamp[_timestamp];
        return (retrievedData.info, retrievedData.value);
    }

}

contract BlockNumber {
    event Log(address indexed sender, string message);
    event Result(uint256 block_number);
    uint256 a;

    uint256 public block_number;

    struct Data {
        string info;
        uint256 value;
    }
    mapping(uint256 => Data) public dataByNumber;
    event DataAdded(uint256 number, string info, uint256 value);

    constructor() payable {
        block_number = block.number;
    }

    function getInitBlockNumber() public view returns (uint256) {
        return block_number;
    }

    function getBlockNumber() public view returns (uint256) {
        return block.number;
    }
    
    function callEvent() public {
        emit Result(block.number);
    }

    function callEventsInLoop() public payable {
        for (uint256 i = 0; i < 100; i++) {
            a = a + i;
        }
        emit Result(block.number);
    }

    function addData(string memory _info, uint256 _value) public {
        uint256 currentNumber = block.number;
        Data memory newData = Data({
            info: _info,
            value: _value
        });
        
        dataByNumber[currentNumber] = newData;
        emit DataAdded(currentNumber, _info, _value);
    }

    function getData(uint256 _number) public view returns (string memory, uint256) {
        Data memory retrievedData = dataByNumber[_number];
        return (retrievedData.info, retrievedData.value);
    }
}
