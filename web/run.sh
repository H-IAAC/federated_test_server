#!/bin/bash

TOOL_NAME='Federated_web'
SCRIPTPATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

status () {
    echo 'Status:'
    if [[ $(ps -aux | grep $SCRIPTPATH | grep node | awk -F ' ' '{print $2}') -ne 0 ]]
    then
         echo "  Process: $(ps -aux | grep $SCRIPTPATH | grep node | awk -F ' ' '{print $2}')"
         echo "    $(ps -aux | grep $SCRIPTPATH | grep node | awk '{ s = ""; for (i =11; i <= NF; i++) s = s $i " "; print s }')"
    else
        echo "  Not running"
        exit 1
    fi
}

start () {
    echo 'Starting, on port '$1
    cd $SCRIPTPATH
    nohup node $SCRIPTPATH/index.js -p $1 >> $SCRIPTPATH/log.out 2>&1 &
}

stop () {
   echo 'Stop:'
   echo "  Process: $(ps -aux | grep $SCRIPTPATH | grep node | awk -F ' ' '{print $2}')"
   kill -9 $(ps -aux | grep $SCRIPTPATH | grep node | awk -F ' ' '{print $2}')
}

help () {
   echo 'Usage: '
   echo '  run.sh status'
   echo '  run.sh start'
   echo '  run.sh stop'
}

case $1 in
    status) status ;;
    start) start $2 ;;
    stop) stop ;;
    *) help ;;
esac
