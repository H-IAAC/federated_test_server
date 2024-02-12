
# H-IAAC - Federated Test

## Web
**Requirements:**\
`node v19.8.1`\
`npm v9.5.1`

**How To:**\
Start: ./run.sh start <port>\
Stop: ./run.sh stop

## Flower:

**Requirements:**\
`flower-0.18`\
`python=3.9`\
`poetry=1.3.2`

**Set environment:**\
` conda create -n flower-3.10.12 python=3.10.12`\
` poetry run pip install`\
` poetry run python3 server.py`

**How To:**\
Start: ./run.sh start <web_server_port> <flower_server_port>\
Stop: ./run.sh stop


## Architecture

![image](https://github.com/H-IAAC/federated_test_server/assets/117912051/792effab-f8cd-44b6-8da6-6a0899634ae6)


