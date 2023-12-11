import flwr as fl
import numpy as np
import math
import os
import time
import os
import flwr as fl
import tensorflow
import grpc
import google.protobuf
import flatbuffers
import json
import argparse
import multiprocessing

from Utils import log, check_log_size, read_log



from logging import WARNING
from typing import Callable, Dict, List, Optional, Tuple

from flwr.server.client_manager import ClientManager
from flwr.server.client_proxy import ClientProxy
from flwr.common import (
    EvaluateIns,
    EvaluateRes,
    FitIns,
    FitRes,
    Parameters,
    Scalar,
    Weights,
    parameters_to_weights,
    weights_to_parameters,
)
from flwr.server.strategy.aggregate import aggregate, weighted_loss_avg
from flwr.common.logger import log

class DEEV_Strategy(fl.server.strategy.FedAvg):
    def __init__(self, aggregation_method, fraction_fit, num_clients, decay=0, perc_of_clients=0):
        print(f"DEEV_Strategy init")

        self.aggregation_method = aggregation_method
        self.num_clients        = num_clients
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

        #POC
        self.perc_of_clients  = perc_of_clients

        #FedLTA
        self.decay_factor = decay

        # Parameters changed from min_eval_clients to min_evaluate_clients in flower newer versions.
        # https://github.com/adap/flower/blob/09bb063643cbbc03ac2b16e528ec2b07a4a4217f/src/py/flwr/strategy/fedavg.py
        super().__init__(fraction_fit=fraction_fit, min_available_clients=num_clients, min_fit_clients=num_clients, min_eval_clients=num_clients)


    def configure_fit(
        self, rnd: int, parameters: Parameters, client_manager: ClientManager
    ) -> List[Tuple[ClientProxy, FitIns]]:
#    def configure_fit(self, server_round, parameters, client_manager):
        print(f"DEEV_Strategy configure_fit")
        self.selected_clients = self.select_clients_bellow_average()

        if self.decay_factor > 0:
            the_chosen_ones  = len(self.selected_clients) * (1 - self.decay_factor)**int(rnd)
            self.selected_clients = self.selected_clients[ : math.ceil(the_chosen_ones)]


        self.clients_last_round = self.selected_clients
        
        config = {
            "selected_clients" : ' '.join(self.selected_clients),
            "round"            : rnd
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










    




    def aggregate_fit(
        self,
        rnd: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[BaseException],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
    #def aggregate_fit(self, server_round, results, failures):	

        print(f"DEEV_Strategy aggregate_fit")
        weights_results = []

        for _, fit_res in results:

            print (fit_res.metrics)

            client_id         = str(fit_res.metrics['cid'])
            transmittion_prob = float(fit_res.metrics['transmittion_prob'])
            cpu_cost          = float(fit_res.metrics['cpu_cost'])
            print(f"DEEV_Strategy aggregate_fit 0")
            self.clients_info[client_id] = {}
            self.clients_info[client_id] = {'transmittion_prob' : transmittion_prob , 
                                            'cpu_cost': cpu_cost}
            print(f"DEEV_Strategy aggregate_fit 1")
            if self.aggregation_method not in ['POC', 'DEEV'] or int(server_round) <= 1:
                weights_results.append((fl.common.parameters_to_ndarrays(fit_res.parameters), fit_res.num_examples))

            else:
                if client_id in self.selected_clients:
                    weights_results.append((fl.common.parameters_to_ndarrays(fit_res.parameters), fit_res.num_examples))

        print(f"DEEV_Strategy aggregate_fit 2")

        #print(f'LEN AGGREGATED PARAMETERS: {len(weights_results)}')
        parameters_aggregated = fl.common.ndarrays_to_parameters(aggregate(weights_results))
        print(f"DEEV_Strategy aggregate_fit 3")
        # Aggregate custom metrics if aggregation fn was provided
        metrics_aggregated = {}
        print(f"DEEV_Strategy aggregate_fit 4")
        return parameters_aggregated, metrics_aggregated
        #return weights_to_parameters(aggregate(weights_results)), {}












    def configure_evaluate(
        self, rnd: int, parameters: Parameters, client_manager: ClientManager
    ) -> List[Tuple[ClientProxy, EvaluateIns]]:
    #def configure_evaluate(self, server_round, parameters, client_manager):
        print(f"DEEV_Strategy configure_evaluate")
        """Configure the next round of evaluation."""
        # Do not configure federated evaluation if fraction eval is 0.
        if self.fraction_evaluate == 0.0:
            return []

        # Parameters and config
        config = {
            'round' : rnd
        }
        if self.on_evaluate_config_fn is not None:
            # Custom evaluation config function provided
            config = self.on_evaluate_config_fn(rnd)

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












    def aggregate_evaluate(
        self,
        server_round,
        results,
        failures,
    ):
        print(f"DEEV_Strategy aggregate_evaluate")
        local_list_clients      = []
        self.list_of_clients    = []
        self.list_of_accuracies = []
        accs                    = []

        
        for response in results:
            client_id       = response[1].metrics['cid']
            client_accuracy = float(response[1].metrics['accuracy'])
            client_trans    = float(response[1].metrics['transmittion_prob'])
            client_cputime  = float(response[1].metrics['cpu_cost'])
            client_battery  = float(response[1].metrics['battery'])

            #filename = f"logs/{self.dataset}/{self.solution_name}/{self.model_name}/pareto.csv"
            #os.makedirs(os.path.dirname(filename), exist_ok=True)

            #with open(filename, 'a') as pareto_file:
            #	pareto_file.write(f"{server_round}, {client_id}, {client_accuracy}, {client_trans}, {client_cputime}, {client_battery}\n")

            #accs.append(client_accuracy)

            local_list_clients.append((client_id, client_accuracy))

        local_list_clients.sort(key=lambda x: x[1])

        self.list_of_clients    = [str(client[0]) for client in local_list_clients]
        self.list_of_accuracies = [float(client[1]) for client in local_list_clients]

        accs.sort()
        self.average_accuracy   = np.mean(accs)

        # Weigh accuracy of each client by number of examples used
        accuracies = [r.metrics["accuracy"] * r.num_examples for _, r in results]
        examples   = [r.num_examples for _, r in results]

        # Aggregate and print custom metric
        accuracy_aggregated = sum(accuracies) / sum(examples)
        current_accuracy    = accuracy_aggregated

        print(f"Round {server_round} accuracy aggregated from client results: {accuracy_aggregated}")

        # Aggregate loss
        loss_aggregated = weighted_loss_avg(
            [
                (evaluate_res.num_examples, evaluate_res.loss)
                for _, evaluate_res in results
            ]
        )

        # Aggregate custom metrics if aggregation fn was provided
        top5 = np.mean(accs[-5:])
        top1 = accs[-1]

        #filename = f"logs/{self.dataset}/{self.solution_name}/{self.model_name}/server.csv"
        #os.makedirs(os.path.dirname(filename), exist_ok=True)

        #with open(filename, 'a') as server_log_file:
        #	server_log_file.write(f"{time.time()}, {server_round}, {accuracy_aggregated}, {top5}, {top1}\n")

        metrics_aggregated = { 
            "accuracy"  : accuracy_aggregated,
            "top-5"     : top5,
            "top-1"     : top1
        }

    
        return loss_aggregated, metrics_aggregated



    def select_clients_bellow_average(self):
        print(f"DEEV_Strategy select_clients_bellow_average")
        selected_clients = []

        for idx_accuracy in range(len(self.list_of_accuracies)):

            if self.list_of_accuracies[idx_accuracy] < self.average_accuracy:
                selected_clients.append(self.list_of_clients[idx_accuracy])

        return selected_clients