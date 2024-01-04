import numpy as np
import random
import threading
import numpy as np
import math
from abc import ABC, abstractmethod
from logging import INFO
from typing import Dict, List, Optional

from flwr.common.logger import log


from flwr.server.client_proxy import ClientProxy
from flwr.server.criterion import Criterion

import json
import os
import pickle
import random
from typing import Optional, List, Tuple, Union, Dict

import flwr as fl
import numpy as np
from flwr.common import Parameters, FitIns, FitRes, Scalar, EvaluateIns, EvaluateRes
from flwr.server.client_proxy import ClientProxy
from flwr.server.strategy.aggregate import aggregate, weighted_loss_avg

def sample(
        clients,
        num_clients: int,
        criterion: Optional[Criterion] = None,
        selection = None,
        acc = None,
        decay_factor = None,
        server_round = None,
        POC_perc_of_clients = 0.5,
        rawcs_params = {}, 
        Rawcs_Manager = None
    ) -> List[ClientProxy]:
        
        # Sample clients which meet the criterion
        available_cids = list(clients)
        if criterion is not None:
            available_cids = [
                cid for cid in available_cids if criterion.select(clients[cid])
            ]

        if num_clients > len(available_cids):
            log(
                INFO,
                "Sampling failed: number of available clients"
                " (%s) is less than number of requested clients (%s).",
                len(available_cids),
                num_clients,
            )
            return []
        
        sampled_cids = available_cids.copy()
        
        if selection == 'DEEV' and server_round>1:
            selected_clients = []

            for idx_accuracy in range(len(acc)):
                if acc[idx_accuracy] < np.mean(np.array(acc)):
                    selected_clients.append(available_cids[idx_accuracy])
            
            sampled_cids = selected_clients.copy()

            if decay_factor > 0:
                the_chosen_ones  = len(selected_clients) * (1 - decay_factor)**int(server_round)
                selected_clients = selected_clients[ : math.ceil(the_chosen_ones)]
                sampled_cids = selected_clients.copy()


        if selection == 'POC' and server_round>1:
            selected_clients = []
            clients2select        = max(int(float(len(acc)) * float(POC_perc_of_clients)), 1)
            sorted_acc = [str(x) for _,x in sorted(zip(acc,available_cids))]
            for c in sorted_acc[:clients2select]:
                selected_clients.append(c)
                sampled_cids = selected_clients.copy()

        '''
        if selection == 'Rawcs':
            if server_round == 1:
                Rawcs_Manager = ManageRawcs(**rawcs_params)
            selected_cids = Rawcs_Manager.sample_fit(server_round)
            selected_cids = Rawcs_Manager.filter_clients_to_train_by_predicted_behavior(selected_cids, server_round)
            for j in range(len(selected_cids)):
                selected_cids[j] = str(selected_cids[j])
            sampled_cids = selected_cids.copy()

            return Rawcs_Manager, [clients[cid] for cid in sampled_cids]
        '''

        if selection == 'All':
            sampled_cids = random.sample(available_cids, num_clients)  


        return [clients[cid] for cid in sampled_cids]   