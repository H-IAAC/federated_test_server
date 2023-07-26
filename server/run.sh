#!/bin/bash

TOOL_NAME='Federated_web'
SCRIPTPATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

status () {
    echo 'Status:'
    if [[ $(ps -aux | grep $SCRIPTPATH | grep python3 | awk -F ' ' '{print $2}') -ne 0 ]]
    then
         echo "  Process: $(ps -aux | grep $SCRIPTPATH | grep python3 | awk -F ' ' '{print $2}')"
         echo "    $(ps -aux | grep $SCRIPTPATH | grep python3 | awk '{ s = ""; for (i =11; i <= NF; i++) s = s $i " "; print s }')"
    else
        echo "  Not running"
        exit 1
    fi
}

start () {
    echo 'Starting'
    cd $SCRIPTPATH
    nohup ~/.local/bin/./poetry run python3 $SCRIPTPATH/server.py --port 8082 >> $SCRIPTPATH/log.txt 2>&1  &
}

stop () {
   echo 'Stop:'
   echo "  Process: $(ps -aux | grep $SCRIPTPATH | grep python3 | awk -F ' ' '{print $2}')"
   kill -9 $(ps -aux | grep $SCRIPTPATH | grep python3 | awk -F ' ' '{print $2}')
}

help () {
   echo 'Usage: '
   echo '  run.sh status'
   echo '  run.sh start'
   echo '  run.sh stop'
}

case $1 in
    status) status ;;
    start) start ;;
    stop) stop ;;
    *) help ;;
esac
