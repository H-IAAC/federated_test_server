import flwr as fl
import numpy as np
import os
import time
import math

from Utils import log, check_log_size, read_log

from server_utils import sample

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
    Weights
)

from flwr.server.strategy.aggregate import aggregate, weighted_loss_avg
from flwr.common.logger import log

class DEEV_Strategy(fl.server.strategy.FedAvgAndroid):
    def __init__(self, aggregation_method, fraction_fit, fraction_eval, min_fit_clients, min_eval_clients, min_available_clients, eval_fn, initial_parameters, decay, perc_of_clients, local_epochs, batch_size):
        print(f"DEEV_Strategy init")

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

        # Parameters changed from min_eval_clients to min_evaluate_clients in flower newer versions.
        # https://github.com/adap/flower/blob/09bb063643cbbc03ac2b16e528ec2b07a4a4217f/src/py/flwr/strategy/fedavg.py
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

    ###### Referent to original code from version 0.18.0
    #def configure_fit(
    #    self, rnd: int, parameters: Parameters, client_manager: ClientManager
    #) -> List[Tuple[ClientProxy, FitIns]]:
    #    """Configure the next round of training."""
    #    config = {}
    #    if self.on_fit_config_fn is not None:
            # Custom fit config function provided
    #        config = self.on_fit_config_fn(rnd)
    #    fit_ins = FitIns(parameters, config)

        # Sample clients
    #    sample_size, min_num_clients = self.num_fit_clients(
    #        client_manager.num_available()
    #    )
    #    clients = client_manager.sample(
    #        num_clients=sample_size, min_num_clients=min_num_clients
    #    )

        # Return client/config pairs
    #    return [(client, fit_ins) for client in clients]

    def configure_fit(self, rnd, parameters, client_manager):
        """Configure the next round of training."""
        if self.aggregation_method == 'POC':
            clients2select        = int(float(self.num_clients) * float(self.perc_of_clients))
            self.selected_clients = self.list_of_clients[:clients2select]

        elif self.aggregation_method == 'DEEV':
            self.selected_clients = self.select_clients_bellow_average()

            if self.decay_factor > 0:
                the_chosen_ones  = len(self.selected_clients) * (1 - self.decay_factor)**int(rnd)
                self.selected_clients = self.selected_clients[ : math.ceil(the_chosen_ones)]

        self.clients_last_round = self.selected_clients
        
        config = {
            "selected_clients" : ' '.join(self.selected_clients),
            "round"            : rnd,
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


    ###### Referent to original code from version 0.18.0
    #def configure_evaluate(
    #    self, rnd: int, parameters: Parameters, client_manager: ClientManager
    #) -> List[Tuple[ClientProxy, EvaluateIns]]:
    #    """Configure the next round of evaluation."""
        # Do not configure federated evaluation if a centralized evaluation
        # function is provided
    #    if self.eval_fn is not None:
    #        return []

        # Parameters and config
    #    config = {}
    #    if self.on_evaluate_config_fn is not None:
            # Custom evaluation config function provided
    #        config = self.on_evaluate_config_fn(rnd)
    #    evaluate_ins = EvaluateIns(parameters, config)

        # Sample clients
    #    if rnd >= 0:
    #        sample_size, min_num_clients = self.num_evaluation_clients(
    #            client_manager.num_available()
    #        )
    #        clients = client_manager.sample(
    #            num_clients=sample_size, min_num_clients=min_num_clients
    #        )
    #    else:
    #        clients = list(client_manager.all().values())

        # Return client/config pairs
    #    return [(client, evaluate_ins) for client in clients]


    def configure_evaluate(self, rnd, parameters, client_manager):
        """Configure the next round of evaluation."""
        # Do not configure federated evaluation if fraction eval is 0.
        if self.fraction_eval == 0.0:
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

    ###### Referent to original code from version 0.18.0
    #def aggregate_fit(self, rnd: int, results: List[Tuple[ClientProxy, FitRes]], failures: List[BaseException],
    #) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
    #    """Aggregate fit results using weighted average."""
    #    if not results:
    #        return None, {}
        # Do not aggregate if there are failures and failures are not accepted
    #    if not self.accept_failures and failures:
    #        return None, {}
        # Convert results
    #    weights_results = [
    #        (self.parameters_to_weights(fit_res.parameters), fit_res.num_examples)
    #        for client, fit_res in results
    #    ]
    #    return self.weights_to_parameters(aggregate(weights_results)), {}

    def aggregate_fit(self, rnd: int, results: List[Tuple[ClientProxy, FitRes]], failures: List[BaseException],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:

        if not results:
            return None, {}
        # Do not aggregate if there are failures and failures are not accepted
        if not self.accept_failures and failures:
            return None, {}


        weights_results = [
            (self.parameters_to_weights(fit_res.parameters), fit_res.num_examples)
            for client, fit_res in results
        ]

        print(f'LEN AGGREGATED PARAMETERS: {len(weights_results)}')
        #parameters_aggregated = weights_to_parameters(aggregate(weights_results))

        # Aggregate custom metrics if aggregation fn was provided
        metrics_aggregated = {}

        #return parameters_aggregated, metrics_aggregated
        return self.weights_to_parameters(aggregate(weights_results)), metrics_aggregated

    ###### Referent to original code from version 0.18.0
    #def aggregate_evaluate(
    #    self,
    #    rnd: int,
    #    results: List[Tuple[ClientProxy, EvaluateRes]],
    #    failures: List[BaseException],
    #) -> Tuple[Optional[float], Dict[str, Scalar]]:

    #    if not results:
    #        return None, {}
        # Do not aggregate if there are failures and failures are not accepted
    #    if not self.accept_failures and failures:
    #        return None, {}
    #    loss_aggregated = weighted_loss_avg(
    #        [
    #            (
    #                evaluate_res.num_examples,
    #                evaluate_res.loss,
    #                evaluate_res.accuracy,
    #            )
    #            for _, evaluate_res in results
    #        ]
    #    )
    #    return loss_aggregated, {} """

    def aggregate_evaluate(
        self,
        rnd: int,
        results: List[Tuple[ClientProxy, EvaluateRes]],
        failures: List[BaseException],
    ) -> Tuple[Optional[float], Dict[str, Scalar]]:

        if not results:
            print(f"aggregate_evaluate no 'results', returning...")
            return None, {}
        # Do not aggregate if there are failures and failures are not accepted
        if not self.accept_failures and failures:
            print(f"aggregate_evaluate there are failures, returning...")            
            return None, {}

        local_list_clients      = []
        self.list_of_clients    = []
        self.list_of_accuracies = []
        accs                    = []
        self.acc = []
        
        for response in results:
            #print(f"client: {response[0].cid}")
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
    
            local_list_clients.append((client_id, client_accuracy))
    
        local_list_clients.sort(key=lambda x: x[1])

        self.list_of_clients    = [str(client[0]) for client in local_list_clients]
        self.list_of_accuracies = [float(client[1]) for client in local_list_clients]

        self.acc = accs.copy()

        accs.sort()
        self.average_accuracy   = np.mean(accs)

        # Weigh accuracy of each client by number of examples used
        accuracies = [float(r.metrics["Accuracy"]) * r.num_examples for _, r in results]
        examples   = [r.num_examples for _, r in results]

        # Aggregate and print custom metric
        accuracy_aggregated = sum(accuracies) / sum(examples)
        current_accuracy    = accuracy_aggregated

        print(f"Round {rnd} accuracy aggregated from client results: {accuracy_aggregated}")

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

    def select_clients_bellow_average(self):
        selected_clients = []

        for idx_accuracy in range(len(self.list_of_accuracies)):

            if self.list_of_accuracies[idx_accuracy] < self.average_accuracy:
                selected_clients.append(self.list_of_clients[idx_accuracy])

        return selected_clients

    def weights_to_parameters(self, weights: Weights) -> Parameters:
        """Convert NumPy weights to parameters object."""
        tensors = [self.ndarray_to_bytes(ndarray) for ndarray in weights]
        return Parameters(tensors=tensors, tensor_type="numpy.nda")

    def parameters_to_weights(self, parameters: Parameters) -> Weights:
        """Convert parameters object to NumPy weights."""
        return [self.bytes_to_ndarray(tensor) for tensor in parameters.tensors]
