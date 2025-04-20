FROM nginx:latest

# Metadata for image
LABEL maintainer="Dellius Alexander <admin@hyfisolutions.com>"
LABEL description="Custom MinIO image for Milvus high-availability setup"


COPY cluster/cfg/nginx.conf /etc/nginx/
# Remove the default NGINX configuration
RUN rm /etc/nginx/conf.d/default.conf

# For nginx health check
EXPOSE 8001
# For etcd client connections
EXPOSE 2379
# For MinIO client connections
EXPOSE 9000
# For Milvus client connections
EXPOSE 19530
# For Milvus REST API connections
EXPOSE 9091
# Start NGINX
CMD ["nginx", "-g", "daemon off;"]
