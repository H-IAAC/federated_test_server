function pad2(n) {
    return n < 10 ? '0' + n : n
}

function getTimestamp() {
    let date = new Date();
    return date.getFullYear().toString() +
                    pad2(date.getMonth() + 1) +
                    pad2(date.getDate()) +
                    pad2(date.getHours()) +
                    pad2(date.getMinutes()) +
                    pad2(date.getSeconds());
}

function displayMessage(message) {
    flower_status.innerHTML = message;
}

function convertTimeFormat(date) {
    var m = moment(date, 'ddd, DD MMM YYYY HH:mm:ss');
    return m.format('DD/MM/YYYY HH:mm:ss');
}