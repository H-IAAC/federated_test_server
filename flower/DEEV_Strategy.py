# Reference code from flower and original deev:
# https://github.com/adap/flower/blob/main/src/py/flwr/server/strategy/fedavg_android.py
# https://github.com/GabrielTalasso/DEEV/blob/main/Server/server.py

import flwr as fl
import numpy as np
import os
import csv
import math

from Utils import log, check_log_size, read_log

from server_utils import sample

from logging import WARNING
from typing import Callable, Dict, List, Optional, Tuple, Union, cast

from logging import WARNING

from flwr.server.client_manager import ClientManager
from flwr.server.client_proxy import ClientProxy
from flwr.server.strategy.aggregate import aggregate, weighted_loss_avg

from flwr.common.logger import log
from flwr.common import (
    EvaluateIns,
    EvaluateRes,
    FitIns,
    FitRes,
    NDArray,
    NDArrays,
    Parameters,
    Scalar,
)

class DEEV_Strategy(fl.server.strategy.FedAvgAndroid):
    def __init__(self, aggregation_method, fraction_fit, fraction_eval, min_fit_clients, min_eval_clients, min_available_clients, eval_fn, initial_parameters, decay, perc_of_clients, local_epochs, batch_size):
        print(f"DEEV_Strategy init")

        self.__name__ = 'DEEV'

        self.aggregation_method = aggregation_method
        self.num_clients        = min_available_clients
        self.list_of_clients    = []
        self.list_of_accuracies = []
        self.selected_clients   = []
        #self.clients_last_round = []

        self.average_accuracy   = 0
        self.last_accuracy      = 0
        self.current_accuracy   = 0

        #pareto
        self.clients_info = {}

        #logs
        #self.dataset    = dataset
        #self.model_name = model_name

        self.local_epochs = local_epochs
        self.batch_size   = batch_size

        #POC
        self.perc_of_clients  = perc_of_clients

        #FedLTA
        self.decay_factor = decay

        super().__init__()

        self.fraction_fit=fraction_fit,
        self.fraction_fit=float(sum(self.fraction_fit))

        self.fraction_eval=fraction_eval,
        self.fraction_eval=float(sum(self.fraction_eval))

        self.min_fit_clients=min_fit_clients,
        self.min_fit_clients=int(sum(self.min_fit_clients))

        self.min_eval_clients=min_eval_clients,
        self.min_eval_clients=int(sum(self.min_eval_clients))

        self.min_available_clients=min_available_clients,
        self.min_available_clients=int(sum(self.min_available_clients))

        self.eval_fn=eval_fn

        self.initial_parameters = initial_parameters

        # Dictionary of type cid:accuracy
        self.clients = {}

        # define csv path
        self.csv_path = f'{os.sep}tmp{os.sep}selected_clientes.csv'
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

        with open(self.csv_path, 'w', encoding='UTF8') as f:
            csv.writer(f, quoting=csv.QUOTE_ALL).writerow(['round','clients'])

    def configure_fit(self, server_round, parameters, client_manager):
        """Configure the next round of training."""

        print(f"configure_fit")

        self.selected_clients = self.select_clients_bellow_average(self.average_accuracy)

        if self.decay_factor > 0:
            the_chosen_ones  = len(self.selected_clients) * (1 - self.decay_factor)**int(server_round)
            self.selected_clients = self.selected_clients[ : math.ceil(the_chosen_ones)]

        print(f"Round {server_round}\tNumber of selected clients = {len(self.selected_clients)}")

        with open(self.csv_path, 'a', encoding='UTF8') as f:
            data = [server_round] + self.selected_clients
            csv.writer(f, quoting=csv.QUOTE_ALL).writerow(data)

        self.clients_last_round = self.selected_clients
        
        config = {
            "selected_clients" : ' '.join(self.selected_clients),
            "round"            : server_round,
            "batch_size"       : self.batch_size, 
            "local_epochs"     : self.local_epochs
            }

        fit_ins = FitIns(parameters, config)

        # Sample clients
        sample_size, min_num_clients = self.num_fit_clients(
            client_manager.num_available()
        )
        clients = client_manager.sample(
            num_clients=sample_size, min_num_clients=min_num_clients
        )

        # Return client/config pairs
        return [(client, fit_ins) for client in clients]

    def configure_evaluate(self, server_round, parameters, client_manager):
        """Configure the next round of evaluation."""

        print(f"configure_evaluate")

        # Do not configure federated evaluation if fraction eval is 0.
        if self.fraction_eval == 0.0:
            return []
        
        # Parameters and config
        config = {
            'round' : server_round
        }
        if self.on_evaluate_config_fn is not None:
            # Custom evaluation config function provided
            config = self.on_evaluate_config_fn(server_round)
        evaluate_ins = fl.common.EvaluateIns(parameters, config)

        # Sample clients
        sample_size, min_num_clients = self.num_evaluation_clients(
            client_manager.num_available()
        )
        clients = client_manager.sample(
            num_clients=sample_size, min_num_clients=min_num_clients
        )

        # Return client/config pairs
        return [(client, evaluate_ins) for client in clients]

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[Union[Tuple[ClientProxy, FitRes], BaseException]],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:

        if not results:
            return None, {}
        # Do not aggregate if there are failures and failures are not accepted
        if not self.accept_failures and failures:
            return None, {}

        weights_results = [
            (self.parameters_to_ndarrays(fit_res.parameters), fit_res.num_examples)
            for client, fit_res in results
        ]

        #parameters_aggregated = weights_to_parameters(aggregate(weights_results))
        parameters_aggregated = fl.common.ndarrays_to_parameters(aggregate(weights_results))

        # Aggregate custom metrics if aggregation fn was provided
        metrics_aggregated = {}

        return parameters_aggregated, metrics_aggregated

    def aggregate_evaluate(
        self,
        server_round,
        results,
        failures,
    ):
        if not results:
            print(f"aggregate_evaluate no 'results', returning...")
            return None, {}
        # Do not aggregate if there are failures and failures are not accepted
        if not self.accept_failures and failures:
            print(f"aggregate_evaluate there are failures, returning...")            
            return None, {}

        print(f"aggregate_evaluate")

        accs = []
        self.acc = []
        clients = {}

        for response in results:
            client_id       = response[0].cid
            client_accuracy = float(response[1].metrics['Accuracy'])
            #client_trans    = float(response[1].metrics['transmittion_prob'])
            #client_cputime  = float(response[1].metrics['cpu_cost'])
            #client_battery  = float(response[1].metrics['battery'])
            #filename = f"logs/{self.solution_name}/pareto.csv"
            #os.makedirs(os.path.dirname(filename), exist_ok=True)
    
            #with open(filename, 'a') as pareto_file:
                #pareto_file.write(f"{server_round}, {client_id}, {client_accuracy}, {client_trans}, {client_cputime}, {client_battery}\n")
    
            accs.append(client_accuracy)
    
            clients[client_id] = client_accuracy
    
        self.clients = dict(sorted(clients.items(), key=lambda item: item[1]))

        self.acc = accs.copy()

        accs.sort()
        self.average_accuracy = np.mean(accs)

        # Weigh accuracy of each client by number of examples used
        accuracies = [float(r.metrics["Accuracy"]) * r.num_examples for _, r in results]
        examples   = [r.num_examples for _, r in results]

        # Aggregate and print custom metric
        accuracy_aggregated = sum(accuracies) / sum(examples)
        current_accuracy    = accuracy_aggregated

        print(f"Round {server_round} accuracy aggregated from client results: {accuracy_aggregated}")

        # Aggregate loss
        loss_aggregated = weighted_loss_avg(
            [
                (
                    evaluate_res.num_examples,
                    evaluate_res.loss,
                    evaluate_res.accuracy,
                )
                for _, evaluate_res in results
            ]
        )

        # Aggregate custom metrics if aggregation fn was provided
        top5 = np.mean(accs[-5:])
        top1 = accs[-1]

        #filename = f"logs/{self.dataset}/{self.solution_name}/{self.model_name}/server.csv"
        #os.makedirs(os.path.dirname(filename), exist_ok=True)

        #with open(filename, 'a') as server_log_file:
        #    server_log_file.write(f"{time.time()}, {server_round}, {accuracy_aggregated}, {top5}, {top1}\n")

        metrics_aggregated = { 
            "accuracy"  : accuracy_aggregated,
            "top-5"     : top5,
            "top-1"     : top1
        }
    
        return loss_aggregated, metrics_aggregated

    def select_clients_bellow_average(self, average_accuracy):
        selected_clients = []

        for item in self.clients.items():
            if item[1] < average_accuracy:
                selected_clients.append(item[0])

        return selected_clients

    def get_result_file(self) -> str:
        #temp_file = open("/tmp/temporary.txt", "w")
        #temp_file.write('temporary to test flower DEEV execution.')
        #temp_file.close()

        # Return the path to the result file
        return self.csv_path