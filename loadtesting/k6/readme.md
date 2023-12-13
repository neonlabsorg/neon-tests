# How to build a k6 bin

install k6
```bash
go install go.k6.io/xk6/cmd/xk6
```
 build  a k6 binary file with following command
 ```bash
 xk6 build --with github.com/szkiba/xk6-prometheus --with github.com/romanova-natasha/xk6-ethereum@edbfda2
```
 where: 

- github.com/szkiba/xk6-prometheus is a plugin for working with metrics

- romanova-natasha/xk6-ethereum@edbfda2 is a plugin for working with ethereum



## Run infrastructure
go to the monitoring folder and run
```bash
docker-compose -f compose.yml up -d --build
```
It is needed to include telegraf tool in the infrastructure. Install it if do not have one (```brew install telegraf``` or similar for your system)

run telegraf with config
```bash
telegraf --config telegraf.conf
```
## Run load test
To run tests go to the repo k6
```bash
./k6 run send_neon.test.js --tag testrun='devnet test' --tag system='Proxy' -o 'prometheus=namespace=k6'
```
## Monitoring
To monitor your test run go to the default grafana host/port ```localhost:3000```. Open dashboard: ``` Neonlabs performance test```.