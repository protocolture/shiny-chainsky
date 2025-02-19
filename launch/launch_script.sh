#!/bin/bash
echo "Pulling the latest code from the GitHub repository..."
git -C /opt/chainsky pull
CONFIG_FILE="/etc/chainsky/chainsky.conf"

#!/bin/bash

# Load configuration from /etc/chainsky/chainsky.conf

if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    echo "Configuration loaded from $CONFIG_FILE"
else
    echo "Configuration file $CONFIG_FILE not found. Exiting."
    exit 1
fi

# Map environment variables to specific scripts
echo $FREESKY_MODE
case $FREESKY_MODE in
    DRelay)
        script_to_run="/opt/chainsky/chainskyrelay/free-sky-relay-loop.py"
        ;;
    DReader)
        script_to_run="/opt/chainsky//chainskycontact/main.py"
        ;;
    DPrinter)
        script_to_run="/opt/chainsky//chainskycompute/admin.py"
        ;;
    DAudio)
        script_to_run="/opt/chainsky//chainskybrain/brain.py"
        ;;
    *)
        echo "Unsupported mode, Exiting"
        exit 1
        ;;
esac

# Check if the script exists and run it
if [ -f "$script_to_run" ]; then
    python3 "$script_to_run"
else
    echo "Script $script_to_run not found. Exiting."
    exit 1
fi
