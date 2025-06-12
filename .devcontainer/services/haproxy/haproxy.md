# HAProxy Configuration and Management Guide

This README provides a comprehensive guide to configuring and managing HAProxy 3.0, based on the official documentation from [HAProxy 3.0 Introduction](https://docs.haproxy.org/3.0/intro.html), [Configuration](https://docs.haproxy.org/3.0/configuration.html), and [Management](https://docs.haproxy.org/3.0/management.html). It includes detailed explanations of configuration options, best practices, and example `haproxy.cfg` files for common use cases. The guide also covers management commands, conflicting configurations, and when to use specific directives.

## Table of Contents
1. [Overview of HAProxy](#overview-of-haproxy)
2. [Configuration Structure](#configuration-structure)
3. [Global Section](#global-section)
4. [Defaults Section](#defaults-section)
5. [Frontend Section](#frontend-section)
6. [Backend Section](#backend-section)
7. [Management and Runtime API](#management-and-runtime-api)
8. [Best Practices](#best-practices)
9. [Example Configurations](#example-configurations)
10. [Conflicting Configurations](#conflicting-configurations)
11. [Common Options and Flags](#common-options-and-flags)

## Overview of HAProxy
HAProxy is a high-performance TCP and HTTP load balancer that provides reliability, flexibility, and observability for modern applications. It operates at Layer 4 (TCP) or Layer 7 (HTTP), distributing traffic across multiple backend servers. Key features include:
- **High Availability**: Ensures no single point of failure by load balancing across servers.
- **Performance**: Handles thousands of connections with low latency.
- **Flexibility**: Supports complex routing, health checks, and session persistence.
- **Observability**: Provides detailed logging, statistics, and runtime API for monitoring.

HAProxy is commonly used for:
- Load balancing web applications (HTTP/HTTPS).
- Proxying TCP-based services (e.g., databases, gRPC).
- Providing a single entry point for microservices.
- Securing traffic with SSL termination.

## Configuration Structure
The `haproxy.cfg` file is divided into sections that define how HAProxy processes traffic:
- **Global**: Sets process-wide parameters (e.g., max connections, logging).
- **Defaults**: Specifies default settings for all frontends and backends unless overridden.
- **Frontend**: Defines entry points for incoming traffic (ports, protocols).
- **Backend**: Specifies the servers to which traffic is forwarded and how they are balanced.
- **Listen**: Combines frontend and backend in a single section (less common).
- **Userlist**: Defines authentication for stats or other services.

Each section contains directives (e.g., `maxconn`, `bind`) and options (e.g., `option httplog`) that control behavior.

## Global Section
The `global` section configures process-wide settings that affect the entire HAProxy instance.

### Key Directives
- **`maxconn <number>`**:
  - **Purpose**: Limits the total number of concurrent connections HAProxy can handle.
  - **When to Use**: Set based on system resources (CPU, memory) and expected traffic. High values require sufficient file descriptors (`ulimit -n`).
  - **Example**: `maxconn 4096` supports 4096 simultaneous connections.
  - **Best Practice**: Start with 1000–5000 and adjust based on load testing. Monitor `conn_rate` in stats.

- **`log <target> <facility> [<level>]`**:
  - **Purpose**: Configures logging to a syslog server, stdout, or file.
  - **When to Use**: Always enable logging for debugging and monitoring. Use `stdout` in containers for centralized logging.
  - **Example**: `log stdout format raw local0 info` logs to stdout with info level.
  - **Best Practice**: Use `local0`–`local7` facilities to avoid conflicts with other services. Set level to `info` for general use, `debug` for troubleshooting.

- **`stats socket <path> [options]`**:
  - **Purpose**: Enables the runtime API for dynamic configuration and monitoring.
  - **When to Use**: Essential for production to adjust settings without restarting (e.g., enable/disable servers).
  - **Example**: `stats socket /var/run/api.sock user haproxy group haproxy mode 660 level admin expose-fd listeners`.
  - **Options**:
    - `user <user>`, `group <group>`, `mode <mode>`: Set permissions for security.
    - `level admin`: Allows full control (use cautiously).
    - `expose-fd listeners`: Supports seamless reloads.
  - **Best Practice**: Restrict access to `admin` level and secure the socket file.

- **`daemon`**:
  - **Purpose**: Runs HAProxy in the background.
  - **When to Use**: Use in non-containerized environments. Omit in containers where HAProxy runs in the foreground.
  - **Best Practice**: Avoid in Docker/Kubernetes; use `log stdout` instead.

### Example Global Section

```plaintext
global
  maxconn 5000
  log stdout format raw local0 info
  stats socket /var/run/api.sock user haproxy group haproxy mode 660 level admin expose-fd listeners
  daemon
```

## Defaults Section
The `defaults` section sets default parameters for all frontends and backends, reducing repetition.

### Key Directives
- **`mode {http|tcp}`**:
  - **Purpose**: Sets the protocol layer (Layer 7 for HTTP, Layer 4 for TCP).
  - **When to Use**: Use `http` for web traffic, `tcp` for non-HTTP protocols (e.g., gRPC, databases).
  - **Example**: `mode tcp` for etcd traffic.
  - **Best Practice**: Match the mode to the application protocol to enable appropriate features (e.g., HTTP routing).

- **`timeout <type> <value>`**:
  - **Purpose**: Configures timeouts for various operations.
  - **Types**:
    - `client`: Time a client can remain inactive (default: 10s).
    - `connect`: Time to establish a connection to a backend (default: 5s).
    - `server`: Time a server can take to respond (default: 10s).
    - `queue`: Time a request can wait in the queue (default: 5s).
  - **When to Use**: Adjust based on application latency and network conditions.
  - **Example**: `timeout client 30s` for long-lived HTTP connections.
  - **Best Practice**: Set `client` and `server` timeouts higher than `connect` to avoid premature disconnections.

- **`balance <algorithm>`**:
  - **Purpose**: Defines the load balancing algorithm.
  - **Algorithms**:
    - `roundrobin`: Distributes requests sequentially (default).
    - `leastconn`: Sends requests to the server with the fewest connections.
    - `source`: Routes based on client IP hash.
  - **When to Use**: Use `roundrobin` for general purposes, `leastconn` for uneven workloads.
  - **Example**: `balance roundrobin`.
  - **Best Practice**: Test algorithms under load to ensure even distribution.

- **`option tcplog`**:
  - **Purpose**: Enables detailed TCP connection logging.
  - **When to Use**: Use with `mode tcp` to log connection details.
  - **Best Practice**: Combine with `log global` for consistent logging.

- **`option httplog`**:
  - **Purpose**: Enables detailed HTTP request/response logging.
  - **When to Use**: Use with `mode http` for web applications.
  - **Best Practice**: Enable for debugging and monitoring HTTP traffic.

### Example Defaults Section

```plaintext
defaults
  mode http
  timeout client 30s
  timeout connect 5s
  timeout server 30s
  timeout queue 10s
  balance roundrobin
  maxconn 2000
  log global
  option httplog
  option dontlognull
  retries 3
```

## Frontend Section
The `frontend` section defines how HAProxy accepts incoming connections.

### Key Directives
- **`bind <address>:<port> [options]`**:
  - **Purpose**: Specifies the listening address and port.
  - **Options**:
    - `ssl`: Enables SSL termination.
    - `accept-proxy`: Accepts PROXY protocol headers.
  - **When to Use**: Use for each service entry point (e.g., HTTP on 80, TCP on 2379).
  - **Example**: `bind *:80` for HTTP traffic.
  - **Best Practice**: Use `*:<port>` for all interfaces unless restricting to a specific IP.

- **`mode {http|tcp}`**:
  - **Purpose**: Sets the protocol for the frontend.
  - **When to Use**: Match the backend mode for consistency.
  - **Example**: `mode tcp` for etcd.

- **`default_backend <name>`**:
  - **Purpose**: Routes traffic to a specific backend.
  - **When to Use**: Always specify to avoid undefined behavior.
  - **Example**: `default_backend backend_etcd`.

- **`stats enable`**:
  - **Purpose**: Enables the stats page for monitoring.
  - **When to Use**: Use in a dedicated frontend for observability.
  - **Example**:

    ```plaintext
    frontend stats
      mode http
      bind *:8404
      stats enable
      stats uri /
      stats refresh 5s
    ```
  - **Best Practice**: Secure with authentication (`stats auth`) in production.

### Example Frontend Section

```plaintext
frontend http_frontend
  mode http
  bind *:80
  default_backend backend_web
  option httplog

frontend stats
  mode http
  bind *:8404
  stats enable
  stats uri /
  stats refresh 5s
  stats auth admin:password
```

## Backend Section
The `backend` section defines the servers that receive traffic and how they are managed.

### Key Directives
- **`server <name> <address>:<port> [options]`**:
  - **Purpose**: Defines a backend server.
  - **Options**:
    - `check`: Enables health checks.
    - `cookie <value>`: Sets a cookie for session persistence.
    - `weight <number>`: Adjusts load balancing priority (1–256).
  - **When to Use**: List all servers for a service.
  - **Example**: `server web1 192.168.1.10:80 check`.

- **`option httpchk [method] <uri>`**:
  - **Purpose**: Configures HTTP health checks.
  - **When to Use**: Use with `mode http` for application-level checks.
  - **Example**: `option httpchk GET /health`.

- **`http-check expect status <codes>`**:
  - **Purpose**: Defines expected HTTP status codes for health checks.
  - **When to Use**: Use to validate server health.
  - **Example**: `http-check expect status 200,204`.

- **`cookie <name> insert indirect nocache`**:
  - **Purpose**: Enables session persistence via cookies.
  - **When to Use**: Use for stateful applications requiring sticky sessions.
  - **Example**: `cookie SERVERUSED insert indirect nocache`.

- **`default-server [options]`**:
  - **Purpose**: Sets default parameters for all servers in the backend.
  - **Options**:
    - `check inter <interval>`: Health check interval.
    - `fall <count>`: Failures before marking down.
    - `rise <count>`: Successes before marking up.
    - `error-limit <count>`: Errors before marking down.
    - `on-error mark-down`: Action on error.
  - **Example**: `default-server check inter 3s fall 2 rise 3`.

### Example Backend Section

```plaintext
backend backend_web
  mode http
  balance roundrobin
  option httpchk GET /health
  http-check expect status 200
  cookie SERVERUSED insert indirect nocache
  default-server check inter 3s fall 2 rise 3 error-limit 10 on-error mark-down
  server web1 192.168.1.10:80 check cookie web1
  server web2 192.168.1.11:80 check cookie web2
```

## Management and Runtime API
HAProxy provides a runtime API via the stats socket for dynamic management. Key commands include:
- **Enable/Disable Servers**: `set server <backend>/<server> state {ready|drain|down}`.
  - **Example**: `echo "set server backend_web/web1 state down" | socat /var/run/api.sock -`.
- **Adjust Weights**: `set weight <backend>/<server> <value>`.
- **View Stats**: `show stat` for detailed metrics.
- **Reload Configuration**: Use `expose-fd listeners` for seamless reloads with `haproxy -sf`.

### When to Use
- **Dynamic Scaling**: Enable/disable servers during deployments.
- **Troubleshooting**: Adjust weights or check stats without restarting.
- **Monitoring**: Integrate with tools like Prometheus via stats page.

### Best Practice
- Secure the stats socket with restricted permissions.
- Use `level admin` only for trusted users.
- Monitor runtime API usage to prevent abuse.

## Best Practices
1. **Logging**: Always enable logging (`log global`, `option httplog` or `tcplog`).
2. **Health Checks**: Use application-specific health checks (e.g., `/health` endpoint).
3. **Timeouts**: Set realistic timeouts based on application and network latency.
4. **Stats Page**: Enable with authentication for monitoring.
5. **Session Persistence**: Use cookies for stateful applications.
6. **Resource Limits**: Tune `maxconn` and file descriptors for high traffic.
7. **Security**: Restrict stats socket and stats page access.
8. **Testing**: Validate configurations with `haproxy -c -f haproxy.cfg` before deploying.

## Example Configurations
Below are example `haproxy.cfg` files for common scenarios, incorporating best practices.

### HTTP Load Balancer for Web Servers
This configuration load balances HTTP traffic across two web servers with session persistence and health checks.

```plaintext
global
  maxconn 5000
  log stdout format raw local0 info
  stats socket /var/run/api.sock user haproxy group haproxy mode 660 level admin expose-fd listeners

defaults
  mode http
  timeout client 30s
  timeout connect 5s
  timeout server 30s
  timeout queue 10s
  balance roundrobin
  maxconn 2000
  log global
  option httplog
  retries 3

frontend http_frontend
  bind *:80
  mode http
  default_backend backend_web
  option httplog

frontend stats
  mode http
  bind *:8404
  stats enable
  stats uri /
  stats refresh 5s
  stats auth admin:password

backend backend_web
  mode http
  balance roundrobin
  option httpchk GET /health
  http-check expect status 200
  cookie SERVERUSED insert indirect nocache
  default-server check inter 3s fall 2 rise 3 error-limit 10 on-error mark-down
  server web1 192.168.1.10:80 check cookie web1
  server web2 192.168.1.11:80 check cookie web2
```

### TCP Load Balancer for Etcd
This configuration proxies TCP traffic for an etcd cluster with health checks.

```plaintext
global
  maxconn 4096
  log stdout format raw local0 info
  stats socket /var/run/api.sock user haproxy group haproxy mode 660 level admin expose-fd listeners

defaults
  mode tcp
  timeout client 10s
  timeout connect 5s
  timeout server 10s
  timeout queue 5s
  balance roundrobin
  maxconn 2000
  log global
  option tcplog
  retries 3

frontend frontend_etcd
  mode tcp
  bind *:2379
  default_backend backend_etcd
  option tcplog

backend backend_etcd
  mode tcp
  option httpchk GET /health
  http-check send meth GET uri /health
  http-check expect status 200,204,307
  default-server check inter 3s downinter 5s fall 2 rise 3 error-limit 10 on-error mark-down
  server etcd1 etcd1:2379 check
  server etcd2 etcd2:2379 check
```

### MinIO Cluster Load Balancer
This configuration load balances MinIO API and console traffic with session persistence.

```plaintext
global
  maxconn 5000
  log stdout format raw local0 info
  stats socket /var/run/api.sock user haproxy group haproxy mode 660 level admin expose-fd listeners

defaults
  mode http
  timeout client 30s
  timeout connect 5s
  timeout server 30s
  timeout queue 10s
  balance roundrobin
  maxconn 2000
  log global
  option httplog
  retries 3

frontend minio_console
  mode http
  bind *:9001
  default_backend backend_minio_console
  option httplog

frontend minio_api
  mode http
  bind *:9000
  default_backend backend_minio_api
  option httplog

frontend stats
  mode http
  bind *:8404
  stats enable
  stats uri /
  stats refresh 5s
  stats auth admin:password

backend backend_minio_console
  mode http
  option httpchk HEAD /minio/health/live
  http-check expect status 200
  cookie SERVERUSED insert indirect nocache
  default-server check inter 3s fall 2 rise 3 observe layer7 error-limit 10 on-error mark-down
  server minio1 minio1:9001 check cookie minio1
  server minio2 minio2:9001 check cookie minio2

backend backend_minio_api
  mode http
  option httpchk HEAD /minio/health/live
  http-check expect status 200
  cookie SERVERUSED insert indirect nocache
  default-server check inter 3s fall 2 rise 3 observe layer7 error-limit 10 on-error mark-down
  server minio1 minio1:9000 check cookie minio1
  server minio2 minio2:9000 check cookie minio2
```

## Conflicting Configurations
Potential conflicts to avoid:
- **Mode Mismatch**: Ensure `mode` is consistent between frontend and backend (e.g., both `http` or both `tcp`).
- **Duplicate Backend Names**: Backend names must be unique.
- **Overlapping Stats Ports**: Ensure the stats port (e.g., 8404) is not used by other services.

## Common Options and Flags
Below is a list of commonly used options and flags, their purposes, and when to use them:

- **`option dontlognull`**:
  - **Purpose**: Suppresses logging of null connections (e.g., health checks).
  - **When to Use**: Enable to reduce log noise in high-traffic environments.
  - **Example**: `option dontlognull`.

- **`retries <number>`**:
  - **Purpose**: Number of retry attempts for failed requests.
  - **When to Use**: Set to 2–3 for resilience without overwhelming servers.
  - **Example**: `retries 3`.

- **`option redispatch`**:
  - **Purpose**: Allows retrying failed requests on a different server.
  - **When to Use**: Use with `retries` for high availability.
  - **Example**: `option redispatch`.

- **`observe layer7`**:
  - **Purpose**: Monitors Layer 7 (HTTP) metrics for health checks.
  - **When to Use**: Use with `mode http` for detailed application monitoring.
  - **Example**: `default-server observe layer7`.

- **`error-limit <count>`**:
  - **Purpose**: Maximum errors before marking a server down.
  - **When to Use**: Use to prevent flapping due to transient errors.
  - **Example**: `error-limit 10`.

- **`on-error mark-down`**:
  - **Purpose**: Action to take when `error-limit` is reached.
  - **When to Use**: Use to quickly isolate failing servers.
  - **Example**: `on-error mark-down`.

### How to Use
- Combine options to tailor behavior (e.g., `option httpchk` with `http-check expect`).
- Test configurations with `haproxy -c` to catch errors.
- Monitor stats and logs to validate option effectiveness.

## Conclusion
This guide provides a foundation for configuring and managing HAProxy 3.0 for various use cases. By following the best practices and example configurations, you can achieve high availability, performance, and observability. Always validate configurations and monitor runtime metrics to ensure optimal operation.

For further details, refer to:
- [HAProxy 3.0 Introduction](https://docs.haproxy.org/3.0/intro.html)
- [HAProxy 3.0 Configuration](https://docs.haproxy.org/3.0/configuration.html)
- [HAProxy 3.0 Management](https://docs.haproxy.org/3.0/management.html)
</xaiArtifact>