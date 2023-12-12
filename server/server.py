import os
import flwr as fl
import tensorflow
import grpc
import google.protobuf
import flatbuffers
import json
import argparse
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from multiprocessing import Process
import logging
import multiprocessing

from Utils import log, check_log_size, read_log
from DEEV_Strategy import DEEV_Strategy

log(f"flwr: {fl.__version__}")
log(f"tensorflow: {tensorflow.__version__}")
log(f"protobuf: {google.protobuf.__version__}")
log(f"grpcio: {grpc.__version__}")
log(f"flatbuffers: {flatbuffers.__version__}")

config = {
    'ORIGINS': [
        'http://localhost:8080',
        'http://127.0.0.1:8080',
        'http://localhost:8070',
        'http://127.0.0.1:8070',
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
          'local_epochs': 10,
          'algorithm_name': 'FedAvg',
          'algorithm_params': {}}

######
# Display the log file when accessing the '/' path.
#
#####
@app.route("/")
@cross_origin()
def get():
    if not os.path.exists("./log.txt"):
        return "No log content to display."
    else:
        check_log_size()

    return read_log()


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
    global status
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
            _algorithm_name = request.form['algorithm_name']
            _algorithm_params = request.form['algorithm_params']

            _eval_fn = None
            # _initial_parameters = request.form['initial_parameters']

            status = {'isRunning': True,
                      'fraction_fit': _fraction_fit, 'fraction_eval': _fraction_eval,
                      'min_fit_clients': _min_fit_clients, 'min_eval_clients': _min_eval_clients,
                      'min_available_clients': _min_available_clients,
                      'batch_size': _batch_size,
                      'local_epochs': _local_epochs,
                      'num_rounds': _num_rounds,
                      'algorithm_name': _algorithm_name,
                      'algorithm_params': _algorithm_params}


            # Strategy - FedAvg
            if _algorithm_name == 'FedAvg':
                log("  Using FedAvg strategy")
                # Create FedAvg strategy
                strategy = fl.server.strategy.FedAvgAndroid(
                    fraction_fit=_fraction_fit,
                    fraction_eval=_fraction_eval,
                    min_fit_clients=_min_fit_clients,
                    min_eval_clients=_min_eval_clients,
                    min_available_clients=_min_available_clients,
                    eval_fn=None,
                    initial_parameters=None,
                    on_fit_config_fn=lambda server_round : { "batch_size": _batch_size, "local_epochs": _local_epochs })

            # Strategy - DEEV
            elif _algorithm_name == 'DEEV':
                log("  Using DEEV strategy")

                parameters = json.loads(_algorithm_params)
                decay = (parameters["decay"])
                perc_of_clients = (parameters["perc_of_clients"])

                log(f"DEEV decay: {decay} perc_of_clients {perc_of_clients}")

                # Create DEEV strategy
                strategy =  DEEV_Strategy(_algorithm_name, 
                                          fraction_fit=_fraction_fit,
                                          fraction_eval=_fraction_eval,
                                          min_fit_clients=int(_min_fit_clients),
                                          min_eval_clients=int(_min_eval_clients),
                                          min_available_clients=int(_min_available_clients),
                                          eval_fn=None,
                                          decay=float(decay),
                                          perc_of_clients=float(perc_of_clients)
                                          #dataset            = os.environ['DATASET'],
                                          #model_name         = os.environ['MODEL'])
                                        )

            # Strategy - RAWCS
            elif _algorithm_name == 'rawcs':
                log("  RAWCS strategy not implemented")
                return jsonify(status="fail", reason=f"RAWCS strategy not implemented")

            else:
                log(f"Invalid aggregation_method received: {_algorithm_name}")
                return jsonify(status="fail", reason=f"Invalid aggregation_method received: {_algorithm_name}")

            # Start Flower server execution
            start(strategy, _num_rounds)

        except Exception as e:
            log(f"Flower start failed!! Exception: {e}")
            return jsonify(status="fail", reason=f"Flower start failed!! Exception: {e}.")

        finally:
            status['isRunning'] = False

    return jsonify(status="success", reason=f"{_algorithm_name} execution finished.")

######
# Start server.
#
#####
def start(strategy, _num_rounds):
    global flower_process
    log(f"===## Starting Flower Server\n                      with parameters: {status}")

    # create a new process
    flower_process = Process(target=flower_server, args=(strategy, _num_rounds))

    # start the process
    flower_process.start()

    # wait for the process to finish
    flower_process.join()

    log("===## FLOWER SERVER is now disabled ##===")

######
# function used to run flower server process.
#
#####
def flower_server(strategy, _num_rounds):
    # Start Flower server for 10 rounds of federated learning
    log(f"Flower server started on port: {flower_server_port}")
    fl.server.start_server(
        server_address=f"0.0.0.0:{flower_server_port}",
        config={"num_rounds": _num_rounds},
        #config=fl.server.ServerConfig(num_rounds=int(_num_rounds)),
        strategy=strategy,
    )

######
# Main.
#
#####
if __name__ == "__main__":
    server_port = 8082
    flower_server_port = 8083

    parser = argparse.ArgumentParser(
        description="Flower server"
    )

    parser.add_argument("--port", help="server port (default: 8082)")
    parser.add_argument("--flower_port", help="flower server port (default: 8083)")
    args = parser.parse_args()

    if args.port is not None:
        server_port = args.port

    if args.flower_port is not None:
        flower_server_port = args.flower_port

    log("==============================================")
    log(f"======== Service started on port: {server_port} =======")

    app.run(host='0.0.0.0', port=server_port)
