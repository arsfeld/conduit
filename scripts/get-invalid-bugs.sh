#!/bin/bash
wget -q -O - "http://www.conduit-project.org/query?format=csv&status=closed&resolution=invalid&order=priority" | sed 1d | awk -F, '{print $1}'
