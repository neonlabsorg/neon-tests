// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

//Tree of execution:

    //Func1.execute()
    //├── Func2.execute()
    //└── Func3.execute()
    //    ├── Func4.execute()
    //    ├── Func5.execute()
    //    │   └── Func7.execute()
    //    └── Func6.execute()

contract ChainExecution {
    Func2 private func2;
    Func3 private func3;

    constructor(address _func2, address _func3, address _middleCall) {
        func2 = Func2(_func2);
        func3 = Func3(_func3);
    }

    function start_execution() external view returns (uint256) {
        uint256 result1 = func2.execute();
        uint256 result2 = func3.execute();
        uint256 sum = result1 + result2;
        return sum;
    }
}

contract Func2 {

    function execute() external pure returns (uint256) {
        return 2;
    }
}

contract Func3 {
    Func4 private func4;
    Func5 private func5;
    Func6 private func6;

    constructor(address _func4, address _func5, address _func6) {
        func4 = Func4(_func4);
        func5 = Func5(_func5);
        func6 = Func6(_func6);
    }

    function execute() external view returns (uint256) {
        uint256 result1 = func4.execute();
        uint256 result2 = func5.execute();
        uint256 result3 = func6.execute();
        uint256 sum = result1 + result2 + result3;
        return sum;
    }
}

contract Func4 {

    function execute() external pure returns (uint256) {
        return 4;
    }
}

contract Func5 {
    Func7 private func7;

    constructor(address _func7) {
        func7 = Func7(_func7);
    }

    function execute() external view returns (uint256) {
        uint256 result1 = func7.execute();
        return result1 + 5;
    }
}

contract Func6 {

    function execute() external pure returns (uint256) {
        return 6;
    }
}

contract Func7 {

    function execute() external pure returns (uint256) {
        return 7;
    }
}


contract ChainWithRevert {
    MiddleCall public middleCall;

    constructor(address _middleCall) {
        middleCall = MiddleCall(_middleCall);
    }

    function execute_trivial_revert(address _contractCallee) public returns (bool){
        return middleCall.callContactTrivialRevert(_contractCallee);
    }

    function execute_revert_in_middle_call(address _contractCommon, address _contractCallee) public{
        middleCall.callGetTextAndDoRevert(_contractCommon, _contractCallee);
    }
}

contract ChainWithReturnData {
    MiddleCall public middleCall;

    constructor(address _middleCall) {
        middleCall = MiddleCall(_middleCall);
    }

    function start_chain_with_return_data(address _commonContract) public view returns (string memory) {
        return middleCall.callGetText(_commonContract);
    }
}

contract MiddleCall {
    function callContactTrivialRevert(address _contractCallee) public returns (bool) {
        bytes memory payload = abi.encodeWithSignature("emitEventRevert()");
        (bool success, ) = _contractCallee.call(payload);
        return success;
    }

    function callGetText(address _commonContract) public view returns (string memory) {
        bytes memory payload = abi.encodeWithSignature("getText()");
        (bool success, bytes memory returnData) = _commonContract.staticcall(payload);
        require(success, "Call to getText() failed");

        return abi.decode(returnData, (string));
    }

    function callGetTextAndDoRevert(address _commonContract, address _contractCallee) public returns (bool) {
        bytes memory payload_1 = abi.encodeWithSignature("getText()");
        (bool success_1, bytes memory returnData) = _commonContract.staticcall(payload_1);
        require(success_1, "Call to getText() failed");

        bytes memory payload_2 = abi.encodeWithSignature("emitEventRevert()");
        (bool success_2, ) = _contractCallee.call(payload_2);
        return success_2;
}
}


