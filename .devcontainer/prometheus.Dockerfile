FROM prom/prometheus:v2.51.0
COPY ./.devcontainer/cfg/prometheus.yml /etc/prometheus/prometheus.yml
EXPOSE 9090
CMD ["--config.file=/etc/prometheus/prometheus.yml", "--web.listen-address=:9090", "--storage.tsdb.path=/prometheus"]
