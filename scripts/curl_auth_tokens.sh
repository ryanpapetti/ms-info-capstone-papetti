#!/bin/bash
CLIENTID='7ec4038de1184e2fb0a1caf13352e295'
CLIENTSECRET='18fa59e0d4614c139f4c6102f5bc965a'
echo -n $CLIENTID:$CLIENTSECRET | base64 > '../credentials/auth_hash.txt'
