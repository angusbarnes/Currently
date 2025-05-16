#!/bin/bash

COMMAND="./your_program arg1 arg2"
/usr/bin/time -f "\nRuntime: %e seconds\nPeak Memory Usage: %M KB\nExit Status: %x" bash -c "$COMMAND"
