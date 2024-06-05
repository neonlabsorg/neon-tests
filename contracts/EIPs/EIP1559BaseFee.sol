pragma solidity ^0.8.7;

contract BaseFeeOpcode {

    function baseFee() public returns (uint256){
        return block.basefee;
    }

}