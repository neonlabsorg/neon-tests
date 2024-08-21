# dApps testing

This project includes GHA Workflow for regular testing DApps like Uniswap V2, AAVE, and more.
This workflow is triggered by cron every Sunday at 01:00 UTC and runs DApp tests, gets a cost report from these tests, and shows this report.

1. Uniswap V2
2. Uniswap V3
3. Uniswap V4
4. Saddle finance
5. AAVE
6. Curve and Curve-factory
7. Yearn finance
8. Compound
9. Robonomics


## dApp report

Each DApp generates a report in json format and saves it in GHA artifacts. The report has structure:

```json
{
    "name": "Saddle finance",
    "actions": [
       {
          "name": "Remove liquidity",
          "usedGas": "123456",
          "gasPrice": "100000000",
          "tx": "0xadasdasdas"
       }
    ]
}
```

In the "report" state workflow, run clickfile.py command, which will print the report.
