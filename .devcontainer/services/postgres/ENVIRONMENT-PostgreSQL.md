# PostgreSQL Environment Variables

This document outlines the environment variables used by `libpq`, the C application programmer's interface to PostgreSQL, as specified in the PostgreSQL 17 documentation. These variables are used to set default connection parameter values for functions like `PQconnectdb`, `PQsetdbLogin`, and `PQsetdb` when no values are directly specified in the calling code. They are particularly useful for avoiding hard-coded database connection information in client applications. Additionally, some variables control the internal behavior of `libpq` by overriding compiled-in defaults.[](https://www.postgresql.org/docs/current/libpq-envars.html)

> **NOTE**: The environment variables described in this document are not intended to be used for security-sensitive information. For example, `PGPASSWORD` is not recommended for use in production environments due to potential security risks, such as exposing passwords through process environment variables. Instead, consider using the `~/.pgpass` file for secure password storage.[](https://www.postgresql.org/docs/current/libpq-envars.html) [](https://www.postgresql.org/docs/8.2/libpq-envars.html) 
> 


## Connection Parameter Variables

These environment variables specify default connection parameter values used by `libpq` when establishing a connection to a PostgreSQL server.

- **PGHOST**
  - **Description**: Specifies the database server host name. If it begins with a slash, it indicates Unix-domain communication, with the value being the directory where the socket file is stored (default is `/tmp`). Without either `PGHOST` or `PGHOSTADDR`, `libpq` connects via a local Unix-domain socket or, on Windows, to `localhost`.[](https://www.postgresql.org/docs/current/libpq-envars.html)[](https://www.postgresql.org/docs/8.2/libpq-envars.html)

- **PGHOSTADDR**
  - **Description**: Specifies the IP address of the database server. Can be used instead of or in addition to `PGHOST` to avoid DNS lookup overhead.[](https://www.postgresql.org/docs/current/libpq-envars.html)[](https://www.postgresql.org/docs/13/libpq-envars.html)

- **PGPORT**
  - **Description**: Sets the TCP port number or Unix-domain socket file extension for communication with the PostgreSQL server. Can specify a comma-separated list of ports if multiple hosts are provided in `host` or `hostaddr`. An empty string or empty item in the list uses the default port number established during PostgreSQL compilation.[](https://www.postgresql.org/docs/current/libpq-connect.html)[](https://www.postgresql.org/docs/13/libpq-envars.html)

- **PGDATABASE**
  - **Description**: Specifies the name of the database to connect to. Defaults to the same as the user name if not set. In certain contexts, extended formats are checked (see Section 32.1.1 for details).[](https://www.postgresql.org/docs/current/libpq-connect.html)[](https://www.postgresql.org/docs/13/libpq-envars.html)

- **PGUSER**
  - **Description**: Specifies the PostgreSQL user name for the connection. Defaults to the operating system user name of the client if not set.[](https://www.postgresql.org/docs/16/libpq-envars.html)

- **PGPASSWORD**
  - **Description**: Sets the password used if the server requires password authentication. Not recommended for security reasons, as some operating systems allow non-root users to view process environment variables via `ps`. Instead, consider using the `~/.pgpass` file.[](https://www.postgresql.org/docs/8.2/libpq-envars.html)

- **PGPASSFILE**
  - **Description**: Specifies the name of the password file used for authentication lookups. Defaults to `~/.pgpass` or `%APPDATA%\postgresql\.pgpass` on Microsoft Windows.[](https://www.postgresql.org/docs/16/libpq-envars.html)[](https://www.postgresql.org/docs/8.2/libpq-envars.html)

- **PGSERVICE**
  - **Description**: Sets the service name to be looked up in the `pg_service.conf` file, which contains predefined connection parameters.[](https://www.postgresql.org/docs/8.2/libpq-envars.html)

- **PGSERVICEFILE**
  - **Description**: Specifies the name of the per-user connection service file. Defaults to `~/.pg_service.conf` or `%APPDATA%\postgresql\.pg_service.conf` on Microsoft Windows.[](https://www.postgresql.org/docs/16/libpq-envars.html)[](https://www.postgresql.org/docs/18/libpq-envars.html)

- **PGOPTIONS**
  - **Description**: Sets additional run-time options for the PostgreSQL server, equivalent to the `options` connection parameter.[](https://www.postgresql.org/docs/16/libpq-envars.html)[](https://www.postgresql.org/docs/8.2/libpq-envars.html)

- **PGAPPNAME**
  - **Description**: Specifies the application name for the connection, equivalent to the `application_name` connection parameter.[](https://www.postgresql.org/docs/16/libpq-envars.html)[](https://www.postgresql.org/docs/18/libpq-envars.html)

- **PGSSLMODE**
  - **Description**: Determines whether and with what priority an SSL connection is negotiated with the server. Options include:
    - `disable`: Only attempts an unencrypted connection.
    - `allow`: Tries a non-SSL connection first, then SSL if that fails.
    - `prefer` (default): Tries an SSL connection first, then non-SSL if that fails.
    - `require`: Only tries an SSL connection.
    If PostgreSQL is compiled without SSL support, `require` causes an error, while `allow` and `prefer` are accepted but no SSL connection is attempted.[](https://www.postgresql.org/docs/8.2/libpq-envars.html)

- **PGREQUIRESSL**
  - **Description**: Deprecated in favor of `PGSSLMODE`. If set to `1`, `libpq` refuses to connect unless the server accepts an SSL connection (equivalent to `sslmode=prefer`). Only available if PostgreSQL is compiled with SSL support. Setting both `PGREQUIRESSL` and `PGSSLMODE` suppresses this variable's effect.[](https://www.postgresql.org/docs/16/libpq-envars.html)[](https://www.postgresql.org/docs/8.2/libpq-envars.html)

- **PGSSLCOMPRESSION**
  - **Description**: Specifies whether SSL compression is used, equivalent to the `sslcompression` connection parameter.[](https://www.postgresql.org/docs/16/libpq-envars.html)

- **PGSSLCERT**
  - **Description**: Specifies the file containing the SSL client certificate, equivalent to the `sslcert` connection parameter.[](https://www.postgresql.org/docs/16/libpq-envars.html)[](https://www.postgresql.org/docs/9.1/libpq-envars.html)

- **PGSSLKEY**
  - **Description**: Specifies the file containing the SSL client private key, equivalent to the `sslkey` connection parameter.[](https://www.postgresql.org/docs/16/libpq-envars.html)[](https://www.postgresql.org/docs/9.1/libpq-envars.html)

- **PGSSLROOTCERT**
  - **Description**: Specifies the file containing the SSL root certificate, equivalent to the `sslrootcert` connection parameter.[](https://www.postgresql.org/docs/16/libpq-envars.html)[](https://www.postgresql.org/docs/9.1/libpq-envars.html)

- **PGSSLCRL**
  - **Description**: Specifies the file containing the SSL certificate revocation list, equivalent to the `sslcrl` connection parameter.[](https://www.postgresql.org/docs/9.1/libpq-envars.html)

- **PGSSLCRLDIR**
  - **Description**: Specifies the directory containing SSL certificate revocation lists. Must be prepared with the OpenSSL `rehash` or `c_rehash` command. Can be used alongside `PGSSLCRL`.[](https://www.postgresql.org/docs/current/libpq-connect.html)

- **PGSSLCERTMODE**
  - **Description**: Determines whether a client certificate is sent to the server and whether the server requires one. Options include modes that control certificate behavior (see Section 32.1.2 for details).[](https://www.postgresql.org/docs/current/libpq-connect.html)[](https://www.postgresql.org/docs/16/libpq-envars.html)

- **PGSSLNEGOTIATION**
  - **Description**: Controls the SSL/TLS negotiation behavior, equivalent to the `sslnegotiation` connection parameter.[](https://www.postgresql.org/docs/18/libpq-envars.html)

- **PGREQUIREPEER**
  - **Description**: Specifies the operating-system user name of the server (e.g., `requirepeer=postgres`). For Unix-domain socket connections, `libpq` checks if the server process runs under this user name at the start of the connection; if not, the connection is aborted.[](https://www.postgresql.org/docs/current/libpq-connect.html)

- **PGKRBSRVNAME**
  - **Description**: Sets the Kerberos service name for authentication, equivalent to the `krbsrvname` connection parameter.[](https://www.postgresql.org/docs/8.2/libpq-envars.html)

- **PGGSSLIB**
  - **Description**: Specifies the GSS library to use for authentication, equivalent to the `gsslib` connection parameter.[](https://www.postgresql.org/docs/8.4/libpq-envars.html)

- **PGCONNECT_TIMEOUT**
  - **Description**: Sets the maximum number of seconds `libpq` waits when attempting to connect to the PostgreSQL server. If unset or set to `0`, `libpq` waits indefinitely. A timeout less than 2 seconds is not recommended.[](https://www.postgresql.org/docs/8.2/libpq-envars.html)

- **PGREALM**
  - **Description**: Sets the Kerberos realm for PostgreSQL authentication if different from the local realm. Used only if Kerberos authentication is selected by the server, allowing `libpq` to use separate ticket files to avoid conflicts.[](https://www.postgresql.org/docs/9.1/libpq-envars.html)[](https://www.postgresql.org/docs/8.2/libpq-envars.html)

## Internal Behavior Variables

These environment variables control the internal behavior of `libpq` and override compiled-in defaults.

- **PGSYSCONFDIR**
  - **Description**: Sets the directory containing the `pg_service.conf` file and, in future versions, possibly other system-wide configuration files.[](https://www.postgresql.org/docs/current/libpq-envars.html)[](https://www.postgresql.org/docs/13/libpq-envars.html)

- **PGLOCALEDIR**
  - **Description**: Sets the directory containing the locale files for message localization.[](https://www.postgresql.org/docs/current/libpq-envars.html)[](https://www.postgresql.org/docs/13/libpq-envars.html)

## Notes
- These environment variables are particularly useful for simplifying client application configuration by avoiding hard-coded connection details.
- For security-sensitive variables like `PGPASSWORD`, consider using alternatives like `~/.pgpass` to reduce exposure risks.
- For detailed information on connection parameters and their behavior, refer to the PostgreSQL documentation sections 32.1.1 (Connection Strings) and 32.1.2 (Parameter Key Words).[](https://www.postgresql.org/docs/current/libpq-connect.html)

If you find any inaccuracies or need further clarification, please report them using the PostgreSQL documentation feedback form.[](https://www.postgresql.org/docs/current/libpq-envars.html)