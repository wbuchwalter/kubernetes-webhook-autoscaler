import logging
import sys
import time

import click

from autoscaler.cluster import Cluster
from autoscaler.notification import Notifier

logger = logging.getLogger('autoscaler')

DEBUG_LOGGING_MAP = {
    0: logging.CRITICAL,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG
}

@click.command()
@click.option("--sleep", default=60, help='time in seconds between successive checks')
@click.option("--kubeconfig", default=None,
              help='Full path to kubeconfig file. If not provided, '
                   'we assume that we\'re running on kubernetes.')
@click.option("--kubecontext", default="default", help="context to use from the kubeconfig file, default to 'default'.")
@click.option("--scale-out-webhook", help="URI to be called when a scaling out need is detected by the autoscaler")
@click.option("--scale-in-webhook", help="URI to be called when a scaling in need is detected by the autoscaler")
@click.option("--pool-name-regex", help="Regex used to identify agents in the pool(s), default to `agent`. The regex should not match masters.", default="agent")
#How many agents should we keep even if the cluster is not utilized? The autoscaler will currenty break if --spare-agents == 0
@click.option("--spare-agents", default=1, help='number of agent per pool that should always stay up') 
@click.option("--idle-threshold", default=1800, help='time in seconds an agent can stay idle')
@click.option("--drain", default=False, help='wether nodes targeted for deletion should be drained before calling the webhook. Default to False.')
@click.option("--no-scale", is_flag=True, help="never scale out")
@click.option("--over-provision", default=0)
@click.option("--no-maintenance", is_flag=True, help="never scale in")
@click.option("--ignore-pools", default='', help='list of pools that should be ignored by the autoscaler, delimited by a comma')
@click.option("--slack-hook", default=None, envvar='SLACK_HOOK',
              help='Slack webhook URL. If provided, post scaling messages '
                   'to Slack.')
@click.option('--verbose', '-v',
              help="Sets the debug noise level, specify multiple times "
                   "for more verbosity.",
              type=click.IntRange(0, 3, clamp=True),
              count=True, default=2)
#Debug mode will explicitly surface erros
@click.option("--debug", is_flag=True) 
def main(sleep, kubeconfig, kubecontext, scale_out_webhook, scale_in_webhook, spare_agents, pool_name_regex, idle_threshold,
         drain, no_scale, over_provision, no_maintenance, ignore_pools, slack_hook,
         verbose, debug):
    logger_handler = logging.StreamHandler(sys.stderr)
    logger_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(logger_handler)
    logger.setLevel(DEBUG_LOGGING_MAP.get(verbose, logging.CRITICAL))

    notifier = None
    if slack_hook:
        notifier = Notifier(slack_hook)

    cluster = Cluster(kubeconfig=kubeconfig,
                      kubecontext=kubecontext,
                      scale_out_webhook=scale_out_webhook,
                      scale_in_webhook=scale_in_webhook,
                      pool_name_regex=pool_name_regex,
                      spare_agents=spare_agents,
                      idle_threshold=idle_threshold,
                      drain=drain,
                      scale_up=not no_scale,
                      ignore_pools=ignore_pools,
                      maintainance=not no_maintenance,
                      over_provision=over_provision,
                      notifier=notifier)
    cluster.login()
    backoff = sleep
    while True:
        scaled = cluster.loop(debug)
        if scaled:
            time.sleep(sleep)
            backoff = sleep
        else:
            logger.warn("backoff: %s" % backoff)
            backoff *= 2
            time.sleep(backoff)


if __name__ == "__main__":
    main()
