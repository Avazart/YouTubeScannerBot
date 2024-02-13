#!/bin/bash

if ! tmux has-session -t scanner; then
    tmux new -s scanner -d
    tmux send-keys -t scanner:0.0 "./run_app_prod.sh" Enter
    tmux split-window -t scanner:0.0 -v
    tmux send-keys -t scanner:0.1 "cd /home/ubuntu/Projects/AdminHelper/AdminHelper" Enter
    tmux send-keys -t scanner:0.1 "./run_bot.sh" Enter
fi
    tmux attach -t scanner