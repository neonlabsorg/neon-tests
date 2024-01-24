pragma solidity >=0.7.0 <0.9.0;
pragma abicoder v2;

import "../external/call_solana.sol";


contract CallSolanaCaller {

    CallSolana constant _callSolana = CallSolana(0xFF00000000000000000000000000000000000006);
    struct ExecuteArgs {
        uint64 lamports;
        bytes instruction;
    }

    event LogBytes(bytes32 value);
    event LogStr(string value);

    function getNeonAddress(address addr) public returns (bytes32){
        bytes32 solanaAddr = _callSolana.getNeonAddress(addr);
        return solanaAddr;
    }

    function execute(uint64 lamports, bytes calldata instruction) public {
        _callSolana.execute(lamports, instruction);
    }

    function batchExecute(ExecuteArgs[] memory _args) public {
        for(uint i = 0; i < _args.length; i++) {
            _callSolana.execute(_args[i].lamports, _args[i].instruction);
        }
    }

    function getPayer() public returns (bytes32){
        bytes32 payer = _callSolana.getPayer();
        return payer;
    }


}