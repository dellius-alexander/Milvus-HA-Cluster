#!/bin/bash
etcdctl --endpoints=http://localhost:2379 member list
etcdctl --endpoints=http://localhost:2379 endpoint health