#!/bin/bash
set -e
groupadd -r minio-user
useradd -M -r -g minio-user minio-user
chown minio-user:minio-user /mnt/disk1 /mnt/disk2 /mnt/disk3 /mnt/disk4
#chown minio-user:minio-user /mnt/disk1/.minio.sys
#chown minio-user:minio-user /mnt/disk2/.minio.sys
#chown minio-user:minio-user /mnt/disk3/.minio.sys
#chown minio-user:minio-user /mnt/disk4/.minio.sys
