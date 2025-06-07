#!/bin/bash

if ! tmux has-session -t scanner; then
    tmux new -s scanner -d
    tmux send-keys -t scanner:0.0 "./run_app_prod.sh" Enter
    tmux split-window -t scanner:0.0 -v
fi
    tmux attach -t scanner