/**
 * Send configuration parameters to the server
 */
function setConfiguration() {
    // Get values from algorithm options
    let current_algorithm_config = get(JSON.parse(algorithms_select.value));

    let server_upload_directory = algorithms_select.options[algorithms_select.selectedIndex].text + '__' + getTimestamp();

    post('/setConfig/', { fold: fold.value,
                          server_directory: server_upload_directory,
                          flower_url: flower_url.value,
                          flower_port: flower_port.value,
                          flower_api_port: flower_api_port.value,
                          algorithm_name: algorithms_select.options[algorithms_select.selectedIndex].text,
                          algorithm_params: JSON.stringify(current_algorithm_config) });

    return server_upload_directory;
}

/**
 * Post a request to the backend
 */
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

