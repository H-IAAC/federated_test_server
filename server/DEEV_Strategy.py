import flwr as fl
import numpy as np
import os
import time

from Utils import log, check_log_size, read_log

from server_utils import sample

from logging import WARNING
from typing import Callable, Dict, List, Optional, Tuple

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

from flwr.server.strategy.aggregate import aggregate, weighted_loss_avg
from flwr.common.logger import log

class DEEV_Strategy(fl.server.strategy.FedAvgAndroid):
    def __init__(self, 
                 aggregation_method, 
                 fraction_fit, 
                 fraction_eval, 
                 min_fit_clients, 
                 min_eval_clients, 
                 min_available_clients, 
                 eval_fn, 
                 initial_parameters, 
                 on_fit_config_fn, 
                 decay, 
                 perc_of_clients):
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

        #POC
        self.perc_of_clients  = perc_of_clients

        #FedLTA
        self.decay_factor = decay

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
        self.on_fit_config_fn = on_fit_config_fn

        #params
        if self.aggregation_method == 'POC':
            self.solution_name = f"{aggregation_method}-{self.perc_of_clients}"

        elif self.aggregation_method == 'DEEV': 
            self.solution_name = f"{aggregation_method}-{self.decay_factor}"

        else:
            self.solution_name = f"{aggregation_method}"

        # https://flower.dev/docs/framework/ref-api/flwr.server.strategy.FedAvgAndroid.html#fedavgandroid
        super().__init__(fraction_fit          = self.fraction_fit, 
                         fraction_eval         = self.fraction_eval, 
                         min_fit_clients       = self.min_fit_clients, 
                         min_eval_clients      = self.min_eval_clients, 
                         min_available_clients = self.min_available_clients,
                         eval_fn               = self.eval_fn,
                         on_fit_config_fn      = self.on_fit_config_fn,
                         initial_parameters    = self.initial_parameters)

    def configure_fit(self, server_round, parameters, client_manager):
        """Configure the next round of training."""
        if self.aggregation_method == 'POC':
            clients2select        = int(float(self.num_clients) * float(self.perc_of_clients))
            self.selected_clients = self.list_of_clients[:clients2select]

        elif self.aggregation_method == 'DEEV':
            self.selected_clients = self.select_clients_bellow_average()


        self.clients_last_round = self.selected_clients

        config = {
			"selected_clients" : ' '.join(self.selected_clients),
			"round"            : server_round
			}

        fit_ins = FitIns(parameters, config)


        # Sample clients
        sample_size, min_num_clients = self.num_fit_clients(
            client_manager.num_available()
        )

        if self.aggregation_method == 'Rawcs':

            self.Rawcs_Manager, clients = sample(clients = client_manager.clients,
					num_clients=sample_size,
					selection = self.aggregation_method,
					POC_perc_of_clients = self.perc_of_clients,
					decay_factor = self.decay_factor,
					acc = self.acc,
					server_round = server_round,
					#rawcs_params=self.rawcs_params, 
					Rawcs_Manager = self.Rawcs_Manager)

        else:
            clients = sample(clients = client_manager.clients,
				   num_clients=sample_size,
				   selection = self.aggregation_method,
				   POC_perc_of_clients = self.perc_of_clients,
				   decay_factor = self.decay_factor,
				   acc = self.acc,
				   server_round = server_round)
				   #rawcs_params=self.rawcs_params)

		# clients = client_manager.sample(
		#     num_clients=sample_size, min_num_clients=min_num_clients,
		# 	selection = self.aggregation_method,
		# 	POC_perc_of_clients = self.perc_of_clients,
		# 	decay_factor = self.decay_factor,
		# 	acc = self.acc,
		# 	server_round = server_round,
		# )

        print('pause')
        # Return client/config pairs
        return [(client, fit_ins) for client in clients]


    def aggregate_fit(self, server_round, results, failures):		
        print(f"aggregate_fit")

        if not results:
            return None, {}
        # Do not aggregate if there are failures and failures are not accepted
        if not self.accept_failures and failures:
            return None, {}
        
        weights_results = []

        for _, fit_res in results:
            '''
            client_id         = str(fit_res.metrics['cid'])
            transmittion_prob = float(fit_res.metrics['transmittion_prob'])
            cpu_cost          = float(fit_res.metrics['cpu_cost'])

            self.clients_info[client_id] = {}
            self.clients_info[client_id] = {'transmittion_prob': transmittion_prob,
                                            'cpu_cost': cpu_cost}
            '''
            
            weights_results.append((fl.common.parameters_to_ndarrays(fit_res.parameters), fit_res.num_examples))
            #if self.aggregation_method not in ['POC', 'DEEV'] or int(server_round) <= 1:
            #    weights_results.append((fl.common.parameters_to_ndarrays(fit_res.parameters), fit_res.num_examples))
#
            #else:
            #    if client_id in self.selected_clients:
            #        weights_results.append((fl.common.parameters_to_ndarrays(fit_res.parameters), fit_res.num_examples))

        #print(f'LEN AGGREGATED PARAMETERS: {len(weights_results)}')
        parameters_aggregated = fl.common.ndarrays_to_parameters(aggregate(weights_results))

        # Aggregate custom metrics if aggregation fn was provided
        metrics_aggregated = {}

        return parameters_aggregated, metrics_aggregated

    def configure_evaluate(self, server_round, parameters, client_manager):
        """Configure the next round of evaluation."""
		# Do not configure federated evaluation if fraction eval is 0.
        if self.fraction_evaluate == 0.0:
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
        print('pause')
		# Return client/config pairs
        return [(client, evaluate_ins) for client in clients]



    def aggregate_evaluate(
        self,
        server_round,
        results,
        failures,
    ):

        local_list_clients      = []
        self.list_of_clients    = []
        self.list_of_accuracies = []
        accs                    = []
        self.acc = []

		
        for response in results:
            #client_id       = response[1].metrics['cid']
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
        accuracies = [r.metrics["Accuracy"] * r.num_examples for _, r in results]
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

        filename = f"logs/{self.dataset}/{self.solution_name}/{self.model_name}/server.csv"
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, 'a') as server_log_file:
            server_log_file.write(f"{time.time()}, {server_round}, {accuracy_aggregated}, {top5}, {top1}\n")

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