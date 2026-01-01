#!/bin/bash

# ===== 配置区 =====
WORKDIR="/home/wushenhui/workspace/project/other/gym_booking"
VENV="$WORKDIR/.venv"
SCRIPT="$WORKDIR/main_once.py"
LOGDIR="$WORKDIR/logs"
LOGFILE="$LOGDIR/main_once.log"
PIDFILE="$WORKDIR/main_once.pid"

# ===== 准备环境 =====
mkdir -p "$LOGDIR"
cd "$WORKDIR" || exit 1

# 激活虚拟环境
source "$VENV/bin/activate"

# ===== 启动程序 =====
nohup python -u "$SCRIPT" > "$LOGFILE" 2>&1 &

# 保存 PID
echo $! > "$PIDFILE"

# ===== 提示 =====
echo "Gym booking started."
echo "PID: $!"
echo "Log: $LOGFILE"
