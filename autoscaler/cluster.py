import collections
import datetime
import logging
import math
import time
import sys
import pykube
import os

from autoscaler.webhook_scaler import WebHookScaler
import autoscaler.capacity as capacity
from autoscaler.kube import KubePod, KubeNode, KubeResource, KubePodStatus
import autoscaler.utils as utils

# we are interested in all pods, incl. system ones
pykube.Pod.objects.namespace = None

# HACK: https://github.com/kelproject/pykube/issues/29#issuecomment-230026930
import backports.ssl_match_hostname
# Monkey-patch match_hostname with backports's match_hostname, allowing for IP addresses
# XXX: the exception that this might raise is
# backports.ssl_match_hostname.CertificateError
pykube.http.requests.packages.urllib3.connection.match_hostname = backports.ssl_match_hostname.match_hostname

logger = logging.getLogger(__name__)

class Cluster(object):
    def __init__(self, kubeconfig, kubecontext, idle_threshold, drain,
                 scale_out_webhook, scale_in_webhook, pool_name_regex,
                 spare_agents, notifier, ignore_pools,
                 scale_up=True, maintainance=True,
                 over_provision=5):

        # config
        self.kubeconfig = kubeconfig
        self.kubecontext = kubecontext
        self.scale_out_webhook = scale_out_webhook
        self.scale_in_webhook = scale_in_webhook
        self.pool_name_regex = pool_name_regex
        self._drained = {}
        self.agent_pools = {}
        self.pools_instance_type = {}
        self.spare_agents = spare_agents
        self.drain = drain
        self.idle_threshold = idle_threshold
        self.over_provision = over_provision
        self.scale_up = scale_up
        self.maintainance = maintainance
        self.notifier = notifier
        self.ignore_pools = ignore_pools

    def login(self):

        #firstConsecutiveStaticIP parameter is used as the private IP for the master
        #os.environ["PYKUBE_KUBERNETES_SERVICE_HOST"] = self.arm_parameters['firstConsecutiveStaticIP']['value']

        if self.kubeconfig:
            # for using locally
            logger.debug('Using kubeconfig %s', self.kubeconfig)
            config = pykube.KubeConfig.from_file(self.kubeconfig)
            # config.set_current_context(self.kubecontext)
            self.api = pykube.HTTPClient(config)
        else:
            # for using on kube
            logger.debug('Using kube service account')
            self.api = pykube.HTTPClient(
                pykube.KubeConfig.from_service_account())
    
    def loop(self, debug):
        """
        runs one loop of scaling to current needs.
        returns True if successfully scaled.
        """
        logger.info("++++ Running Scaling Loop ++++++")

        if debug:
            # In debug mode, we don't want to catch error. Let the app crash
            # explicitly
            return self.loop_logic()
        else:
            try:
                return self.loop_logic()
            except:
                logger.warn("Unexpected error: {}".format(sys.exc_info()[0]))
                return False
    
    def create_kube_node(self, node):
        kube_node = KubeNode(node)
        kube_node.capacity = capacity.get_capacity_for_instance_type(kube_node.instance_type)
        return kube_node

    def loop_logic(self):
        pykube_nodes = pykube.Node.objects(self.api)
        if not pykube_nodes:
            logger.warn(
                'Failed to list nodes. Please check kube configuration. Terminating scale loop.')
            return False

        all_nodes = list(filter(lambda x: utils.is_agent(x, self.pool_name_regex), map(self.create_kube_node, pykube_nodes)))

        scaler = WebHookScaler(
            scale_out_webhook=scale_out_webhook,
            scale_in_webhook=scale_in_webhook,
            pool_name_regex=pool_name_regex,
            nodes=all_nodes,
            ignore_pools=self.ignore_pools,
            over_provision=self.over_provision,
            spare_count=self.spare_agents,
            drain=drain,
            idle_threshold=self.idle_threshold,
            notifier=self.notifier)

        pods = list(map(KubePod, pykube.Pod.objects(self.api)))

        running_or_pending_assigned_pods = [
            p for p in pods if (p.status == KubePodStatus.RUNNING or p.status == KubePodStatus.CONTAINER_CREATING) or (
                p.status == KubePodStatus.PENDING and p.node_name
            )
        ]

        for node in all_nodes:
            for pod in running_or_pending_assigned_pods:
                if pod.node_name == node.name:
                    node.count_pod(pod)
        pods_to_schedule = self.get_pods_to_schedule(pods, scaler.agent_pools)
        logger.info("Pods to schedule: {}".format(len(pods_to_schedule)))

        if self.scale_up:
            logger.info("++++ Scaling Up Begins ++++++")
            self.scale(pods_to_schedule, all_nodes, scaler)
            logger.info("++++ Scaling Up Ends ++++++")
        if self.maintainance:
            logger.info("++++ Maintenance Begins ++++++")
            self.maintain(pods_to_schedule,
                          running_or_pending_assigned_pods, scaler)
            logger.info("++++ Maintenance Ends ++++++")

        return True

    def get_pending_pods(self, pods, nodes):
        pending_pods = []
        # for each pending & unassigned job, try to fit them on current machines or count requested
        #   resources towards future machines
        for pod in pods:
            fitting = None
            for node in nodes:
                if node.can_fit(pod.resources):
                    fitting = node
                    break
            if fitting is None:
                pending_pods.append(pod)
            else:
                fitting.count_pod(pod)
                logger.info("{pod} fits on {node}".format(pod=pod,
                                                          node=fitting))
        logger.info("Pending pods: {}".format(len(pending_pods)))
        for pod in pending_pods:
            logger.debug(pod.name)

        return pending_pods

    def scale(self, pods_to_schedule, nodes, scaler):
        """
        scale up logic
        """
        logger.info("Nodes: {}".format(len(nodes)))
        logger.info("To schedule: {}".format(len(pods_to_schedule)))

        pending_pods = self.get_pending_pods(pods_to_schedule, nodes)
        if len(pending_pods) > 0:
            scaler.fulfill_pending(pending_pods)

    def get_pods_to_schedule(self, pods, agent_pools):
        """
        given a list of KubePod objects,
        return a map of (selectors hash -> pods) to be scheduled
        """
        pending_unassigned_pods = [
            p for p in pods
            if p.status == KubePodStatus.PENDING and (not p.node_name)
        ]

        # we only consider a pod to be schedulable if it's pending and
        # unassigned and feasible
        pods_to_schedule = []
        for pod in pending_unassigned_pods:
            if capacity.is_possible(pod, agent_pools):
                pods_to_schedule.append(pod)
            else:
                logger.warn(
                    "Pending pod %s cannot fit. "
                    "Please check that requested resource amount is "
                    "consistent with node size."
                    "Scheduling skipped." % (pod.name))

        return pods_to_schedule

    def maintain(self, pods_to_schedule, running_or_pending_assigned_pods, scaler):
        scaler.maintain(pods_to_schedule, running_or_pending_assigned_pods)