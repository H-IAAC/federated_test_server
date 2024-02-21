function stopServer() {
    postReq('/stop');
}

function startServer() {
    fetch(flower_endpoint + '/status')
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (!data.isRunning) {
                // Save parameters from this execution
                let server_upload_directory = setConfiguration();

                // Call api to start flower execution
                postReq('/run', server_upload_directory);

                getStatus();
            } else {
                displayMessage("Flower server is already running.");
            }
        })
        .catch(error => {
            displayMessage(error.message);
        });
}

function getStatus() {
    fetch(flower_endpoint + '/status')
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            displayMessage((data.isRunning) ? "Server Running" : "Server not Running");

            // Update UI with values from the server
            fraction_fit.value = data.fraction_fit;
            fraction_eval.value = data.fraction_eval;
            min_fit_clients.value = data.min_fit_clients;
            min_eval_clients.value = data.min_eval_clients;
            min_available_clients.value = data.min_available_clients;
            batch_size.value = data.batch_size;
            local_epochs.value = data.local_epochs;
            num_rounds.value = data.num_rounds;

            if (!data.stop_timestamp)
                flower_server_execution_time.innerHTML = "Since: " + convertTimeFormat(data.start_timestamp);
            else
                flower_server_execution_time.innerHTML = "Last run: " + convertTimeFormat(data.start_timestamp) + " ~ " + convertTimeFormat(data.stop_timestamp);
        })
        .catch(error => {
            displayMessage(error.message);
        });
}

/**
 * Post request to Flower Server
 */
function postReq(api_path, server_upload_directory = "") {
    var form = new FormData();
    var req = new XMLHttpRequest();

    req.open("POST", flower_endpoint + '/' + api_path, true);

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
                displayMessage(JSON.parse(req.response).reason);
        } else {
            if (req.response)
                displayMessage(JSON.parse(req.response).reason);
        }
    }
    req.send(form);
}
