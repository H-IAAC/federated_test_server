// Post on Flower Server
function postOnFlowerServer(api_path, server_upload_directory = "") {
  var form = new FormData();
  var req = new XMLHttpRequest();

  req.open("POST", 'http://' + flower_url.value + ":" + flower_api_port.value + api_path, true);

  form.append("fraction_fit", fraction_fit.value);
  form.append("fraction_eval", fraction_eval.value);
  form.append("min_fit_clients", min_fit_clients.value);
  form.append("min_eval_clients", min_eval_clients.value);
  form.append("min_available_clients", min_available_clients.value);
  form.append("batch_size", batch_size.value);
  form.append("local_epochs", local_epochs.value);
  form.append("num_rounds", num_rounds.value);
  form.append("algorithm_name", algorithms_select.options[algorithms_select.selectedIndex].text);
  form.append("algorithm_params", algorithms_select.value);
  form.append("server_upload_directory", server_upload_directory);

  req.onreadystatechange = function() {
      if (this.readyState === XMLHttpRequest.DONE && this.status === 200) {
          if (req.response)
              flower_status.innerHTML = JSON.parse(req.response).reason;
      } else {
          if (req.response)
              flower_status.innerHTML = JSON.parse(req.response).reason;
      }
  }
  req.send(form);
}

// Post a request
function post(path, params, method = 'post') {

  const form = document.createElement('form');
  form.method = method;
  form.action = path;

  for (const key in params) {
      if (params.hasOwnProperty(key)) {
          const hiddenField = document.createElement('input');
          hiddenField.type = 'hidden';
          hiddenField.name = key;
          hiddenField.value = params[key];

          form.appendChild(hiddenField);
      }
  }

  document.body.appendChild(form);
  form.submit();

  return false;
}

function getFlowerStatus() {
  fetch('http://' + flower_url.value + ":" + flower_api_port.value + '/status')
      .then(function(response) {
          return response.json();
      })
      .then(function(data) {
          flower_status.innerHTML = (data.isRunning) ? "Server Running" : "Server not Running";

          // Update UI with values from the server
          fraction_fit.value = data.fraction_fit;
          fraction_eval.value = data.fraction_eval;
          min_fit_clients.value = data.min_fit_clients;
          min_eval_clients.value = data.min_eval_clients;
          min_available_clients.value = data.min_available_clients;
          batch_size.value = data.batch_size;
          local_epochs.value = data.local_epochs;
          num_rounds.value = data.num_rounds;
      })
      .catch(error => {
          flower_status.innerHTML = error.message;
      });
}

// Refresh the "Remote Devices" list every 3 secs.
var interval = 3000;
function doAjax() {
    $.ajax({
        type: 'GET',
        url: '/getDevices',
        data: $(this).serialize(),
        dataType: 'json',
        success: function (data) {
            var table = document.getElementById("table");

            for (var i = table.rows.length; i > 1; i = table.rows.length) {
                table.deleteRow(i - 1);
            }

            for (var i = 0; i < data.devices.length; i++) {
                var row = table.insertRow(table.rows.length);
                row.insertCell(0).innerHTML = data.devices[i][0];
                row.insertCell(1).innerHTML = data.devices[i][1];
                row.insertCell(2).innerHTML = data.devices[i][2];
                row.insertCell(3).innerHTML = data.devices[i][3];
            }

            if (table.rows.length > 1)
                $("#newtestBtn").show();
            else
                $("#newtestBtn").hide();
        },
        complete: function (data) {
            // Schedule the next
            setTimeout(doAjax, interval);
        }
    });
}
setTimeout(doAjax, interval);

