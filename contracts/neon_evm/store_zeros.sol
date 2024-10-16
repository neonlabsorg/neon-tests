pragma solidity 0.8.12;

contract saveZeros {

    bytes32[64] public b;  // prefills the contract storage
    bytes32 public number;
    mapping(uint256 => uint256) public intMapping;

    function saveZeroToVar() public returns (bytes32) {  // should not create a new account
        number = bytes32(0);
        return number;
    }

    function saveZeroToMapping() public {  // should not create a new account
        intMapping[0] = 0;
    }

    function saveZeroToMappingCycle() public {  // should not create a new account
        for (uint i = 0; i < 10; i++) {
            intMapping[i] = 0;
        }
    }

}
