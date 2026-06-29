FROM nousresearch/hermes-agent:latest

USER root

COPY bootstrap-profile.sh /opt/aethos/bootstrap-profile.sh
COPY aethos_mcp_server.py /opt/aethos/aethos_mcp_server.py
COPY aethos-atlas-profile /opt/aethos/atlas-profile

RUN chmod +x /opt/aethos/bootstrap-profile.sh

USER hermes

ENTRYPOINT ["/opt/aethos/bootstrap-profile.sh"]
CMD ["gateway", "run"]
