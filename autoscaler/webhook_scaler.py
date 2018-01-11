import requests
import time
import os
import logging
import json
import uuid
from copy import deepcopy

import autoscaler.utils as utils
from autoscaler.agent_pool import AgentPool
from autoscaler.scaler import Scaler, ClusterNodeState

logger = logging.getLogger(__name__)

class WebHookScaler(Scaler):

    def __init__(self, scale_out_webhook, scale_in_webhook, drain, pool_name_regex, nodes,
              over_provision, spare_count, idle_threshold, 
              ignore_pools, notifier):
        Scaler.__init__(self, nodes, over_provision,
            spare_count, idle_threshold, notifier)
        
        self.scale_out_webhook = scale_out_webhook
        self.scale_in_webhook = scale_in_webhook
        self.pool_name_regex = pool_name_regex
        self.drain = drain

        for pool_name in ignore_pools.split(','):
            self.ignored_pool_names[pool_name] = True
        self.agent_pools, self.scalable_pools = self.get_agent_pools(nodes)

    def get_agent_pools(self, nodes):
        # TODO: add param for regex for pool name
        pools = {}
        for node in nodes:
            # Will need to be modified to pass the regex
            pool_name = utils.get_pool_name(node, self.pool_name_regex)
            pool = pools.setdefault(pool_name, {'size': "", 'nodes': []})
            pool['nodes'].append(node)
            pool['size'] = node.selectors["beta.kubernetes.io/instance-type"]

        agent_pools = []
        scalable_pools = []
        for pool_name in pools:
            pool_info = pools[pool_name]
            # TODO: Create the pool after, and infer size from node count
            pool = AgentPool(pool_name, pool_info['size'], pool_info['nodes'])
            agent_pools.append(pool)
            if not pool_name in self.ignored_pool_names:
                scalable_pools.append(pool)

        return agent_pools, scalable_pools

    def scale_in(self, desired_pool_configurations):
        print("scale in with req: {}".format(desired_pool_configurations))
        resp = requests.post(self.scale_in_webhook, json=desired_pool_configurations)

    def scale_out(self, new_pool_sizes):
        req = []
        for pool in self.scalable_pools:
            req.append({
                "name": pool.name,
                "current_agent_count": pool.actual_capacity,
                "desired_agent_count": new_pool_sizes[pool.name]
            })
        print("scale out with req: {}".format(req))
        resp = requests.post(self.scale_out_webhook, json=req)


    def maintain(self, pods_to_schedule, running_or_pending_assigned_pods):
        """
        maintains running instances:
        - determines if idle nodes should be drained and terminated
        """
        logger.info("++++ Maintaining Nodes ++++++")

        delete_queue = []
        pods_by_node = {}
        for p in running_or_pending_assigned_pods:
            pods_by_node.setdefault(p.node_name, []).append(p)

        desired_pool_configurations = []
        should_scale_in = False
        for pool in self.scalable_pools:
            conf = {
                "name": pool.name,
                "current_agent_count": pool.actual_capacity,
                "desired_agent_count": pool.actual_capacity,
                "target_nodes": []
            }
            desired_pool_configurations.append(conf)

            # maximum nomber of nodes we can drain without hiting our spare
            # capacity
            max_nodes_to_drain = pool.actual_capacity - self.spare_count
            for node in pool.nodes:
                state = self.get_node_state(
                    node, pods_by_node.get(node.name, []), pods_to_schedule)

                if state == ClusterNodeState.UNDER_UTILIZED_DRAINABLE:
                    if max_nodes_to_drain == 0:
                        state = ClusterNodeState.SPARE_AGENT

                logger.info("node: %-*s state: %s" % (75, node, state))

                # state machine & why doesnt python have case?
                if state in (ClusterNodeState.POD_PENDING, ClusterNodeState.BUSY,
                             ClusterNodeState.SPARE_AGENT, ClusterNodeState.GRACE_PERIOD):
                    # do nothing
                    pass
                elif state == ClusterNodeState.UNDER_UTILIZED_DRAINABLE:
                    if self.drain:
                        node.cordon()
                        notifier = self.notifier or None
                        node.drain(pods_by_node.get(node.name, []),
                                    notifier)
                        max_nodes_to_drain -= 1
                    else:
                        conf["desired_agent_count"] -= 1
                        conf["target_nodes"].append(node.name)
                        should_scale_in = True
                elif state == ClusterNodeState.IDLE_SCHEDULABLE:
                    if self.drain:
                        node.cordon()
                    else:
                        conf["desired_agent_count"] -= 1
                        conf["target_nodes"].append(node.name)
                        should_scale_in = True
                elif state == ClusterNodeState.BUSY_UNSCHEDULABLE:
                    if self.drain:
                        node.uncordon()
                elif state == ClusterNodeState.IDLE_UNSCHEDULABLE:
                    conf["desired_agent_count"] -= 1
                    conf["target_nodes"].append(node.name)
                    should_scale_in = True
                elif state == ClusterNodeState.UNDER_UTILIZED_UNDRAINABLE:
                    pass
                else:
                    raise Exception("Unhandled state: {}".format(state))
        if should_scale_in:
            self.scale_in(desired_pool_configurations)
