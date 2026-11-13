FROM scratch
COPY --chmod=0755 weed /usr/local/bin/weed
COPY LICENSE /usr/share/licenses/seaweedfs/LICENSE
COPY --chown=10001:10001 data/ /data/
USER 10001:10001
WORKDIR /data
ENTRYPOINT ["/usr/local/bin/weed", "-logtostderr=true"]
