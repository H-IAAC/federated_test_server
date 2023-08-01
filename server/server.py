import os
import flwr as fl
import grpc
import google.protobuf as protobuf
import json
import argparse
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from multiprocessing import Process
import logging

print(f"flwr: {fl.__version__}")
print(f"grpcio: {grpc.__version__}")
print(f"protobuf: {protobuf.__version__}")

config = {
    'ORIGINS': [
        'http://localhost:8080',
        'http://127.0.0.1:8080',
    ],
}

app = Flask(__name__)
cors = CORS(app, resources={r'/*': {'origins': config['ORIGINS']}}, supports_credentials=True)
app.config['CORS_HEADERS'] = 'Content-Type'
app.logger.disabled = True

logging.getLogger('werkzeug').disabled = True

flower_process: Process
status = {'isRunning': False,
          'fraction_fit': 1.0, 'fraction_eval': 1.0,
          'min_fit_clients': 1, 'min_eval_clients': 1,
          'min_available_clients': 1,
          'eval_fn': None,
          'initial_parameters': None,
          'num_rounds': 5,
          'batch_size': 32,
          'local_epochs': 10}

######
# Display the log file when accessing the '/' path.
#
#####
@app.route("/")
@cross_origin()
def get():
    content = "No log content to display."

    if not os.path.exists("./log.txt"):
        return content
    else:
        with open("./log.txt", 'r+') as file:
            # read an store all lines into list
            lines = file.readlines()

            #print(f"-> {len(lines)}")

            # Remove initial file lines, when it has more than 5000 log lines
            if len(lines) > 5000:
                print(f"-> removing log lines")
                # move file pointer to the beginning of a file
                file.seek(0)
                # truncate the file
                file.truncate()
                # start writing lines except the first line
                # lines[2500:] from line 2501 to last line
                file.writelines(lines[2500:])

            # loop to read iterate
            # last 1000 lines and print it
            file.seek(0)
            content = '<head><style>'
            content += 'body { font-family: "Courier New", monospace; }'
            content += '</style></head>'
            content += '<script> function scrollToBottom() { window.scrollTo(0, document.body.scrollHeight); } '
            content += 'history.scrollRestoration = "manual"; '            
            content += 'window.onload = scrollToBottom; </script>'

            for line in (file.readlines()[-1000:]):
                content += line + "</br>"

    return content


######
# API to returns the current server configuration.
#
#####
@app.route("/status")
@cross_origin()
def get_status():
    global status
    log(f"configuration: {status}")
    return jsonify(status)


######
# API to handle stop flower server execution.
#
#####
@app.route('/stop', methods=['POST'])
@cross_origin()
def stop_flower():
    global flower_process, status
    log("POST to stop flower server received")

    if not status['isRunning']:
        log("FLOWER SERVER not running")
        return jsonify(status="fail", reason=f"Flower server is not running.")

    try:
        flower_process.kill()
        log("FLOWER SERVER forced to stop")
    except Exception as e:
        log(f"FLOWER SERVER failed to stop: {e}")
        return jsonify(status="fail", reason=f"Flower server failed to stop: {e}.")

    return jsonify(status="success", reason=f"Flower server has stop.")


######
# API to handle start/run flower server.
#
#####
@app.route('/run', methods=['POST'])
@cross_origin()
def run_flower():
    global status, flower_process
    log("POST to start FLOWER SERVER received")

    if status['isRunning']:
        log("FLOWER SERVER is already running")
        return jsonify(status="fail", reason="Flower server already running.")
    else:
        try:
            _num_rounds: int = int(request.form['num_rounds'])
            _fraction_fit: float = float(request.form['fraction_fit'])
            _fraction_eval: float = float(request.form['fraction_eval'])
            _min_fit_clients: int = int(request.form['min_fit_clients'])
            _min_eval_clients: int = int(request.form['min_eval_clients'])
            _min_available_clients: int = int(request.form['min_available_clients'])
            _batch_size: int = int(request.form['batch_size'])
            _local_epochs: int = int(request.form['local_epochs'])

            # _eval_fn = request.form['eval_fn']
            # _initial_parameters = request.form['initial_parameters']

            status = {'isRunning': True,
                      'fraction_fit': _fraction_fit, 'fraction_eval': _fraction_eval,
                      'min_fit_clients': _min_fit_clients, 'min_eval_clients': _min_eval_clients,
                      'min_available_clients': _min_available_clients,
                      'batch_size': _batch_size,
                      'local_epochs': _local_epochs,
                      'num_rounds': _num_rounds}

            log(f"===## Starting FLOWER SERVER ##===")
            log(f"Starting parameters: {status}")

            # Create strategy
            strategy = fl.server.strategy.FedAvgAndroid(
                fraction_fit=_fraction_fit,
                fraction_eval=_fraction_eval,
                min_fit_clients=_min_fit_clients,
                min_eval_clients=_min_eval_clients,
                min_available_clients=_min_available_clients,
                eval_fn=None,
                initial_parameters=None,
                on_fit_config_fn=lambda server_round : { "batch_size": _batch_size, "local_epochs": _local_epochs })

            # create a new process
            flower_process = Process(target=start_flower_server, args=(strategy, _num_rounds))

            # start the process
            flower_process.start()

            # wait for the process to finish
            flower_process.join()

            log("===## FLOWER SERVER is now disabled ##===")

        except Exception as e:
            log(f"Invalid request, exception: {e}")
            return jsonify(status="fail", reason=f"Invalid request, exception: {e}.")

        finally:
            status['isRunning'] = False

    return jsonify(status="success", reason=f"Flower execution finished.")

######
# Starts/Run flower server.
#
#####
def start_flower_server(strategy, _num_rounds):
    # Start Flower server for 10 rounds of federated learning
    fl.server.start_server(
        server_address="0.0.0.0:8083",
        config={"num_rounds": _num_rounds},
        strategy=strategy,
    )

######
# Log message to default output.
#
#####
def log(msg):
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    print(f"{now} {msg}")

    with open("./log.txt", "a") as file:
        file.write(f"{now} {msg}\n")


######
# Main.
#
#####
if __name__ == "__main__":
    server_port = 8082

    parser = argparse.ArgumentParser(
        description="Flower server"
    )

    parser.add_argument("--port", help="server port (default: 8082)")
    args = parser.parse_args()

    if args.port is not None:
        server_port = args.port

    log("==============================================")
    log(f"======== Service started on port: {server_port} =======")

    app.run(host='0.0.0.0', port=server_port)
