#!/usr/bin/env bash
set -e

cd /root/models/cosima_omnetpp_project

NETWORK="${OMNET_NETWORK:-SimpleNetworkTCP}"
MODE="${OMNET_MODE:-gui}"

# pega o NED path exatamente do config do COSIMA
INET_NED_PATH="$(python3 -c "import cosima_core.util.general_config as cfg; print(cfg.INET_INSTALLATION_PATH)")"

CMD="./cosima_omnetpp_project -n ${INET_NED_PATH} -f cosima.ini -c ${NETWORK}"

if [ "${MODE}" = "cmd" ]; then
  CMD="${CMD} -u Cmdenv"
else
  CMD="${CMD} -u Qtenv"
fi

echo "[omnet] Running: ${CMD}"
exec ${CMD}
